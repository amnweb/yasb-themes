import copy
import difflib
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from importlib import import_module

import yaml

RAW_THEMES_URL = "https://raw.githubusercontent.com/amnweb/yasb-themes/main/themes"
THEME_ID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
WIDGET_TYPE_RE = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+")
ASSET_KEYS = ("config", "style", "readme", "image")
BAR_COLUMNS = ("left", "center", "right")
GROUPER_TYPE = "yasb.grouper.GrouperWidget"
NOT_A_MAPPING = "A widget must be a mapping with a `type` and `options`."
KIND_LABELS = {"deprecated": "⚠️ Deprecated", "invalid": "❌ Error", "structure": "❌ Error"}
WIDGET_NAME_OVERRIDES = {
    "active_layout": "Komorebi Layout",
    "cpu": "CPU",
    "dnd": "Do Not Disturb",
    "github": "GitHub",
    "glazewm": "GlazeWM",
    "gpu": "GPU",
    "libre_monitor": "Libre HW Monitor",
    "obs": "OBS",
    "open_meteo": "Open Meteo",
    "vscode": "VS Code",
    "whkd": "WHKD",
    "wifi": "WiFi",
}


class CheckError(Exception):
    pass


@dataclass
class Problem:
    kind: str
    message: str
    file: str = "config.yaml"
    path: str = ""
    line: int | None = None


@dataclass
class ThemeResult:
    id: str
    name: str = ""
    author: str = ""
    problems: list[Problem] = field(default_factory=list)
    warnings: list[Problem] = field(default_factory=list)
    suggested_diff: str = ""

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> dict:
        return {**asdict(self), "ok": self.ok}


def format_path(loc) -> str:
    text = ""
    for part in loc:
        if isinstance(part, int):
            text += f"[{part}]"
        else:
            text += f".{part}" if text else str(part)
    return text


def parse_path(path: str) -> tuple:
    return tuple(int(part[1:-1]) if part.startswith("[") else part for part in re.findall(r"\[\d+\]|[^.\[\]]+", path))


def _key_line(root, loc) -> int | None:
    node, line = root, None
    for part in loc:
        if isinstance(node, yaml.MappingNode):
            pair = next(
                (p for p in node.value if isinstance(p[0], yaml.ScalarNode) and p[0].value == str(part)),
                None,
            )
            if pair is None:
                break
            line = pair[0].start_mark.line + 1
            node = pair[1]
        elif isinstance(node, yaml.SequenceNode) and isinstance(part, int) and 0 <= part < len(node.value):
            node = node.value[part]
            line = node.start_mark.line + 1
        else:
            break
    return line


def _pydantic_message(error: dict) -> str:
    if error["type"] == "extra_forbidden":
        return "Unknown option. This YASB version does not support it (it was removed, renamed or is misspelled)."
    if error["type"] == "missing":
        return "Required option is missing."
    message = error["msg"]
    value = error.get("input")
    if isinstance(value, (str, int, float)):
        shown = repr(value)
        message += f" (got {shown if len(shown) <= 60 else shown[:57] + '...'})"
    return message


def _widget_references(config: dict, widgets: dict) -> list[tuple[tuple, str]]:
    references = []
    expanded = set()

    def visit(loc, name):
        references.append((loc, name))
        definition = widgets.get(name)
        if name in expanded or not isinstance(definition, dict) or definition.get("type") != GROUPER_TYPE:
            return
        expanded.add(name)
        options = definition.get("options")
        children = options.get("widgets") if isinstance(options, dict) else None
        for index, child in enumerate(children if isinstance(children, list) else ()):
            if isinstance(child, str):
                visit(("widgets", name, "options", "widgets", index), child)

    bars = config.get("bars")
    for bar_name, bar in bars.items() if isinstance(bars, dict) else ():
        columns = bar.get("widgets") if isinstance(bar, dict) and bar.get("enabled") is not False else None
        for column in BAR_COLUMNS if isinstance(columns, dict) else ():
            names = columns.get(column)
            for index, name in enumerate(names if isinstance(names, list) else ()):
                if isinstance(name, str):
                    visit(("bars", bar_name, "widgets", column, index), name)
    return references


def widget_display_name(widget_type: str) -> str:
    source, module = widget_type.split(".")[:2]
    words = [WIDGET_NAME_OVERRIDES.get(part, part.replace("_", " ").title()) for part in (source, module)]
    return words[1] if source == "yasb" else " ".join(words)


def widget_names(config) -> list[str]:
    widgets = config.get("widgets") if isinstance(config, dict) else None
    if not isinstance(widgets, dict):
        return []
    names = []
    for _, reference in _widget_references(config, widgets):
        definition = widgets.get(reference)
        widget_type = definition.get("type") if isinstance(definition, dict) else None
        if not isinstance(widget_type, str) or not WIDGET_TYPE_RE.fullmatch(widget_type) or widget_type == GROUPER_TYPE:
            continue
        name = widget_display_name(widget_type)
        if name not in names:
            names.append(name)
    return names


def _dedupe(problems: list[Problem]) -> list[Problem]:
    seen = set()
    unique = []
    for problem in problems:
        key = (problem.kind, problem.file, problem.path, problem.message)
        if key not in seen:
            seen.add(key)
            unique.append(problem)
    return unique


def _unified_diff(before: str, after: str) -> str:
    def lines(text):
        return [line if line.endswith("\n") else line + "\n" for line in text.splitlines(keepends=True)]

    return "".join(difflib.unified_diff(lines(before), lines(after), "config.yaml", "config.yaml (updated)", n=1))


class Yasb:
    def __init__(self, src: str, ref: str = ""):
        src = os.path.abspath(src)
        if not os.path.isfile(os.path.join(src, "core", "validation", "config.py")):
            raise CheckError(f"YASB sources were not found in {src}.")
        sys.path.insert(0, src)
        logging.getLogger("deprecation").disabled = True
        try:
            from core.validation.config import YasbConfig
            from core.validation.deprecation import migrate_config
            from pydantic import BaseModel, ValidationError
        except Exception as e:
            raise CheckError(f"Could not import the YASB validation modules: {e}") from e
        self._config_model = YasbConfig
        self._migrate = migrate_config
        self._base_model = BaseModel
        self._validation_error = ValidationError
        self._schemas = {}
        self.ref = ref
        self.version = self._read_version(src)
        self.commit = self._read_commit(src)

    @staticmethod
    def _read_version(src: str) -> str:
        try:
            with open(os.path.join(src, "settings.py"), encoding="utf-8") as f:
                match = re.search(r'^BUILD_VERSION\s*=\s*"([^"]+)"', f.read(), re.MULTILINE)
        except OSError:
            return ""
        return match.group(1) if match else ""

    @staticmethod
    def _read_commit(src: str) -> str:
        try:
            result = subprocess.run(["git", "-C", src, "rev-parse", "HEAD"], capture_output=True, text=True)
        except OSError:
            return ""
        return result.stdout.strip() if result.returncode == 0 else ""

    def describe(self) -> dict:
        name = f"YASB {self.version}" if self.version else "YASB"
        if self.version and self.ref.removeprefix("v") == self.version:
            description = f"[{name}](https://github.com/amnweb/yasb/releases/tag/{self.ref})"
        else:
            source = f"`{self.ref}`" if self.ref else ""
            if self.commit:
                link = f"[`{self.commit[:7]}`](https://github.com/amnweb/yasb/commit/{self.commit})"
                source = f"{source} @ {link}" if source else link
            description = f"{name} ({source})" if source else name
        return {"ref": self.ref, "version": self.version, "commit": self.commit, "description": description}

    def widget_schema(self, widget_type: str):
        if widget_type in self._schemas:
            return self._schemas[widget_type]
        module_name, _, class_name = widget_type.rpartition(".")
        target = f"core.widgets.{module_name}"
        schema = None
        try:
            module = import_module(target)
        except ModuleNotFoundError as e:
            missing = e.name or ""
            if not (missing.startswith("core.widgets.") and (target == missing or target.startswith(missing + "."))):
                raise CheckError(f"Importing {target} failed: {e}") from e
        except Exception as e:
            raise CheckError(f"Importing {target} failed: {e}") from e
        else:
            candidate = getattr(getattr(module, class_name, None), "validation_schema", None)
            if isinstance(candidate, type) and issubclass(candidate, self._base_model):
                schema = candidate
        self._schemas[widget_type] = schema
        return schema

    def check_config(self, text: str) -> tuple[list[Problem], list[Problem], str]:
        problems = []
        warnings = []
        try:
            config = yaml.safe_load(text)
            root = yaml.compose(text, Loader=yaml.SafeLoader)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            problems.append(
                Problem("invalid", f"The file is not valid YAML: {e}", line=mark.line + 1 if mark else None)
            )
            return problems, warnings, ""
        if not isinstance(config, dict):
            problems.append(Problem("invalid", "The config must be a YAML mapping of options."))
            return problems, warnings, ""

        def add(target, kind, message, loc):
            target.append(Problem(kind, message, path=format_path(loc), line=_key_line(root, loc)))

        try:
            migrated, deprecations = self._migrate(text)
        except Exception:
            migrated, deprecations = text, []
        for issue in deprecations:
            if issue["action"] == "rename":
                message = f"Rename it to `{issue['new_name']}`. {issue['message']}"
            else:
                message = f"Remove it. {issue['message']}"
            add(problems, "deprecated", message, parse_path(issue["path"]))

        try:
            self._config_model.model_validate(copy.deepcopy(config))
        except self._validation_error as e:
            for error in e.errors(include_url=False):
                loc = tuple(error["loc"])
                if loc[:1] == ("widgets",) and len(loc) > 1:
                    add(problems, "invalid", NOT_A_MAPPING, loc[:2])
                else:
                    add(problems, "invalid", _pydantic_message(error), loc)

        widgets = config.get("widgets")
        widgets = widgets if isinstance(widgets, dict) else {}
        references = _widget_references(config, widgets)
        used = {name for _, name in references}
        for loc, name in references:
            if not widgets.get(name):
                add(problems, "invalid", f"Widget `{name}` is used but not defined under `widgets`.", loc)

        for name, definition in widgets.items():
            loc = ("widgets", name)
            if not isinstance(definition, dict):
                if isinstance(definition, str):
                    add(problems if name in used else warnings, "invalid", NOT_A_MAPPING, loc)
                continue
            widget_type = definition.get("type")
            if not widget_type:
                if name in used:
                    add(problems, "invalid", "Widget has no `type`.", loc)
                else:
                    add(warnings, "invalid", "Entry has no `type`, so YASB ignores it. Check its indentation.", loc)
                continue
            schema = None
            if isinstance(widget_type, str) and WIDGET_TYPE_RE.fullmatch(widget_type):
                schema = self.widget_schema(widget_type)
            if schema is None:
                add(problems, "invalid", f"Unknown widget type `{widget_type}`.", loc + ("type",))
                continue
            try:
                schema.model_validate(copy.deepcopy(definition.get("options", {})))
            except self._validation_error as e:
                for error in e.errors(include_url=False):
                    add(problems, "invalid", _pydantic_message(error), loc + ("options", *error["loc"]))

        suggested_diff = _unified_diff(text, migrated) if deprecations else ""
        return _dedupe(problems), _dedupe(warnings), suggested_diff

    def check_theme(self, folder: str) -> ThemeResult:
        folder = os.path.normpath(folder)
        theme_id = os.path.basename(folder)
        result = ThemeResult(theme_id, name=theme_id)
        files = set(os.listdir(folder))

        def structure(message, file=""):
            result.problems.append(Problem("structure", message, file=file))

        if not THEME_ID_RE.fullmatch(theme_id):
            structure("The theme folder must be named after the theme id.")

        meta = None
        if "theme.json" not in files:
            structure("`theme.json` is missing.", "theme.json")
        else:
            try:
                with open(os.path.join(folder, "theme.json"), encoding="utf-8") as f:
                    meta = json.load(f)
            except (OSError, ValueError) as e:
                structure(f"`theme.json` could not be read: {e}", "theme.json")
            if meta is not None and not isinstance(meta, dict):
                structure("`theme.json` must be a JSON object.", "theme.json")
                meta = None

        assets = {}
        if meta is not None:
            result.name = str(meta.get("name") or theme_id)
            result.author = str(meta.get("author") or "")
            if meta.get("id") != theme_id:
                structure("`id` in `theme.json` must match the theme folder name.", "theme.json")
            prefix = f"{RAW_THEMES_URL}/{theme_id}/"
            for key in ASSET_KEYS:
                url = meta.get(key)
                name = url[len(prefix) :] if isinstance(url, str) and url.startswith(prefix) else ""
                if not name or "/" in name:
                    structure(
                        f"`{key}` in `theme.json` must link to a file in this theme folder ({prefix}...).", "theme.json"
                    )
                elif name not in files:
                    structure(f"`{name}` is linked from `theme.json` but is missing.", name)
                else:
                    assets[key] = name
        elif "config.yaml" in files:
            assets["config"] = "config.yaml"

        style = assets.get("style")
        if style and os.path.getsize(os.path.join(folder, style)) == 0:
            structure(f"`{style}` is empty. YASB does not start with an empty stylesheet.", style)

        config_file = assets.get("config")
        if config_file:
            try:
                with open(os.path.join(folder, config_file), encoding="utf-8") as f:
                    text = f.read()
            except (OSError, UnicodeDecodeError) as e:
                structure(f"`{config_file}` could not be read: {e}", config_file)
            else:
                problems, warnings, result.suggested_diff = self.check_config(text)
                for problem in problems + warnings:
                    problem.file = config_file
                result.problems += problems
                result.warnings += warnings
        elif meta is None:
            structure("`config.yaml` is missing.", "config.yaml")
        return result


def _cell(text: str) -> str:
    return text.replace("\r", " ").replace("\n", " ").replace("|", "\\|").replace("<", "&lt;")


def _where(theme_id: str, problem: Problem, blob_url: str) -> str:
    label = f"`{problem.path}`" if problem.path else (f"`{problem.file}`" if problem.file else "")
    if not (label and blob_url and problem.file):
        return label
    anchor = f"#L{problem.line}" if problem.line else ""
    return f"[{label}]({blob_url}/themes/{theme_id}/{problem.file}{anchor})"


def render_details(result: ThemeResult, blob_url: str = "") -> str:
    lines = []
    if result.problems:
        lines += ["| Type | Where | Problem |", "| --- | --- | --- |"]
        for problem in result.problems:
            where = _where(result.id, problem, blob_url)
            lines.append(f"| {KIND_LABELS[problem.kind]} | {where} | {_cell(problem.message)} |")
    if result.warnings:
        lines += (
            ["", "Notes, these do not fail the check:", ""] if lines else ["Notes, these do not fail the check:", ""]
        )
        for problem in result.warnings:
            lines.append(f"- {_where(result.id, problem, blob_url)}: {_cell(problem.message)}")
    if result.suggested_diff:
        fence = "```"
        while fence in result.suggested_diff:
            fence += "`"
        lines += [
            "",
            "<details><summary>Suggested <code>config.yaml</code> changes for the deprecated options</summary>",
            "",
            f"{fence}diff",
            result.suggested_diff.rstrip("\n"),
            fence,
            "",
            "</details>",
        ]
    return "\n".join(lines)
