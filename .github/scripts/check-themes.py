import argparse
import json
import os
import subprocess
import sys

from theme_check import CheckError, Yasb, render_details

PR_MARKER = "<!-- theme-pr-check -->"


def parse_args():
    parser = argparse.ArgumentParser(description="Validate themes against a YASB checkout.")
    parser.add_argument("themes", nargs="*", help="Theme ids to check. Defaults to every theme.")
    parser.add_argument("--changed-since", metavar="REV", help="Check the themes changed between REV and HEAD.")
    parser.add_argument("--themes-dir", default="themes")
    parser.add_argument("--yasb-src", default="yasb-repo/src")
    parser.add_argument("--yasb-ref", default="")
    parser.add_argument(
        "--blob-url", default="", help="Base URL for file links, e.g. https://github.com/OWNER/REPO/blob/SHA"
    )
    parser.add_argument("--pr-author", default="")
    parser.add_argument("--report", help="Write the results as JSON to this file.")
    parser.add_argument("--markdown", help="Append a Markdown summary to this file.")
    parser.add_argument("--annotate", action="store_true", help="Print GitHub Actions annotations.")
    parser.add_argument("--fail-on-problems", action="store_true")
    return parser.parse_args()


def changed_files(rev):
    output = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", rev, "HEAD"], check=True, capture_output=True
    ).stdout
    return [path for path in output.decode("utf-8", "replace").split("\0") if path]


def is_theme_file(path):
    return path.startswith("themes/") and path.count("/") >= 2


def count_problems(theme):
    counts = {}
    for problem in theme["problems"]:
        kind = "deprecated" if problem["kind"] == "deprecated" else "errors"
        counts[kind] = counts.get(kind, 0) + 1
    return ", ".join(f"{count} {kind}" for kind, count in sorted(counts.items(), reverse=True))


def render_pull_request(report, pr_author):
    lines = [PR_MARKER]
    if report["error"]:
        lines += ["## ⚠️ Theme check could not run", "", "```text", report["error"], "```"]
        return "\n".join(lines)

    failed = any(not theme["ok"] for theme in report["themes"])
    lines += [f"## {'❌ Theme check failed' if failed else '✅ Theme check passed'}", ""]
    lines += [f"Checked against {report['yasb']['description']}.", ""]
    for theme in report["themes"]:
        lines += [f"### {'✅' if theme['ok'] else '❌'} {theme['name']}", ""]
        lines += [f"`{theme['id']}` by `{theme['author'] or 'unknown'}`", ""]
        if pr_author and theme["author"] and theme["author"].lower() != pr_author.lower():
            lines += [f"> [!WARNING]\n> This theme was published by `{theme['author']}`, not by `{pr_author}`.", ""]
        if theme["ok"] and not theme["warnings"]:
            lines += ["No problems found.", ""]
        else:
            lines += [theme["details"], ""]
    if report["removed"]:
        lines += ["### Removed themes", ""] + [f"- `{theme_id}`" for theme_id in report["removed"]] + [""]
    if not report["themes"] and not report["removed"]:
        lines += ["No theme folders were changed.", ""]
    if report["other_files"]:
        files = ", ".join(f"`{path}`" for path in report["other_files"][:20])
        more = f" and {len(report['other_files']) - 20} more" if len(report["other_files"]) > 20 else ""
        lines += [f"> [!NOTE]\n> This pull request also changes files outside the theme folders: {files}{more}.", ""]
    if failed:
        lines += [
            "Please fix the problems above and push the changes to this pull request. The check runs again automatically."
        ]
    return "\n".join(lines).rstrip() + "\n"


def render_overview(report, blob_url):
    if report["error"]:
        return "\n".join(["## ⚠️ Theme check could not run", "", "```text", report["error"], "```", ""])
    failing = [theme for theme in report["themes"] if not theme["ok"]]
    lines = [f"## Theme compatibility: {len(failing)} of {len(report['themes'])} themes fail", ""]
    lines += [f"Checked against {report['yasb']['description']}.", ""]
    if failing:
        lines += ["| Theme | Author | Problems |", "| --- | --- | --- |"]
        for theme in failing:
            name = f"[{theme['name']}]({blob_url}/themes/{theme['id']})" if blob_url else theme["name"]
            lines.append(f"| {name} | `{theme['author'] or 'unknown'}` | {count_problems(theme)} |")
    return "\n".join(lines) + "\n"


def escape_data(text):
    return str(text).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_property(text):
    return escape_data(text).replace(":", "%3A").replace(",", "%2C")


def annotate(report, themes_dir):
    for theme in report["themes"]:
        for level, problems in (("error", theme["problems"]), ("warning", theme["warnings"])):
            for problem in problems:
                target = f"{themes_dir}/{theme['id']}" + (f"/{problem['file']}" if problem["file"] else "")
                properties = f"file={escape_property(target)}"
                if problem["line"]:
                    properties += f",line={problem['line']}"
                properties += f",title={escape_property(theme['name'])}"
                message = f"{problem['path']}: {problem['message']}" if problem["path"] else problem["message"]
                print(f"::{level} {properties}::{escape_data(message)}")
    if report["error"]:
        print(f"::error title=Theme check could not run::{escape_data(report['error'])}")


def main():
    # Windows runners default to cp1252 for redirected output, which cannot encode many config values.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    args = parse_args()

    other_files = []
    if args.changed_since:
        paths = changed_files(args.changed_since)
        theme_ids = sorted({path.split("/")[1] for path in paths if is_theme_file(path)})
        other_files = [path for path in paths if not is_theme_file(path)]
    else:
        theme_ids = args.themes or sorted(
            entry for entry in os.listdir(args.themes_dir) if os.path.isdir(os.path.join(args.themes_dir, entry))
        )

    report = {
        "yasb": {"ref": args.yasb_ref, "description": "YASB"},
        "themes": [],
        "removed": [],
        "other_files": other_files,
        "error": "",
    }
    try:
        yasb = Yasb(args.yasb_src, args.yasb_ref)
        report["yasb"] = yasb.describe()
        for theme_id in theme_ids:
            folder = os.path.join(args.themes_dir, theme_id)
            if not os.path.isdir(folder):
                report["removed"].append(theme_id)
                continue
            result = yasb.check_theme(folder)
            report["themes"].append({**result.to_dict(), "details": render_details(result, args.blob_url)})
    except CheckError as e:
        report["error"] = str(e)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    if args.markdown:
        with open(args.markdown, "a", encoding="utf-8") as f:
            if args.changed_since:
                f.write(render_pull_request(report, args.pr_author))
            else:
                f.write(render_overview(report, args.blob_url))
    if args.annotate:
        annotate(report, args.themes_dir)

    if report["error"]:
        print(f"Theme check could not run: {report['error']}", file=sys.stderr)
        return 2
    failing = [theme for theme in report["themes"] if not theme["ok"]]
    for theme in failing:
        print(f"FAIL {theme['name']} ({theme['id']})")
        for problem in theme["problems"]:
            print(f"  {problem['file']}:{problem['line'] or '-'} {problem['path']} {problem['message']}")
    print(f"Checked {len(report['themes'])} theme(s): {len(failing)} failing.")
    return 1 if failing and args.fail_on_problems else 0


if __name__ == "__main__":
    sys.exit(main())
