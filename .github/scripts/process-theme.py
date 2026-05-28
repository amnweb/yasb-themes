import os
import json
import re
import uuid
import sys
import requests
import urllib.parse
import datetime
import yaml

sys.path.insert(0, os.path.abspath("./yasb-repo/src"))
try:
    from core.validation.deprecation import migrate_config
    from core.validation.config import YasbConfig
except ImportError as e:
    print(f"ERROR: Could not import YASB core validation modules: {e}", file=sys.stderr)
    exit(1)

STYLES_FILE = "styles.css"
README_FILE = "readme.md"
IMAGE_FILE = "image.png"
CONFIG_FILE = "config.yaml"


def create_theme_id():
    return str(uuid.uuid4())


def get_static_asset(theme_id, asset):
    return f"https://raw.githubusercontent.com/amnweb/yasb-themes/main/themes/{theme_id}/{asset}"


def validate_url(url, allow_empty=False):
    if not url:
        url = ""
    if allow_empty and len(url) == 0:
        return
    try:
        result = urllib.parse.urlparse(url)
        if result.scheme != "https":
            print("URL must be HTTPS.", file=sys.stderr)
            exit(1)
    except Exception as e:
        print("URL is invalid.", file=sys.stderr)
        print(e, file=sys.stderr)
        exit(1)


def validate_name(name):
    if not name or len(name) == 0:
        print("Name is required.", file=sys.stderr)
        exit(1)
    if len(name) > 50:
        print("Name must be less than 50 characters.", file=sys.stderr)
        exit(1)
    for char in name:
        if not char.isalnum() and char != " ":
            print(
                "Name must only contain letters, numbers, and spaces.", file=sys.stderr
            )
            exit(1)


def validate_description(description):
    if not description or len(description) == 0:
        print("Description is required.", file=sys.stderr)
        exit(1)
    if len(description) > 200:
        print("Description must be less than 200 characters.", file=sys.stderr)
        exit(1)


def download_image(image_url, image_path):
    response = requests.get(image_url, headers={"User-Agent": "Epicture"})
    if response.status_code != 200:
        print("Image URL is invalid.", file=sys.stderr)
        exit(1)
    if response.headers.get("Content-Type", "") != "image/png":
        print("Image must be a PNG.", file=sys.stderr)
        exit(1)
    with open(image_path, "wb") as f:
        f.write(response.content)


def sanitize_description(description):
    return re.sub(r"[^a-zA-Z0-9 .,!?'\-()]", "", description)


def write_github_env(key, value):
    env_file = os.environ.get("GITHUB_ENV")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as f:
            if "\n" in str(value):
                f.write(f"{key}<<EOF\n{value}\nEOF\n")
            else:
                f.write(f"{key}={value}\n")


def strip_markdown_block(content, lang):
    if not content:
        return ""
    content = content.strip()
    prefix = f"```{lang}"
    if content.startswith(prefix):
        content = content[len(prefix) :]
    if content.endswith("```"):
        content = content[: -len("```")]
    return content.strip()


def parse_issue_body(body: str) -> dict:
    data = {}
    import re

    parts = re.split(r"^###\s+", body, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n", 1)
        key = lines[0].strip()
        value = lines[1].strip() if len(lines) > 1 else ""
        if value == "_No response_":
            value = ""

        if key == "Name":
            data["name"] = value
        elif key == "Description":
            data["description"] = value
        elif key == "Homepage":
            data["homepage"] = value
        elif key == "Image":
            data["image"] = value
        elif key == "Theme Styles":
            data["styles"] = value
        elif key == "Theme Config":
            data["config"] = value
        elif key == "Readme":
            data["readme"] = value
    return data


def main():
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        print("GITHUB_EVENT_PATH is missing or file does not exist.", file=sys.stderr)
        exit(1)

    try:
        with open(event_path, "r", encoding="utf-8") as f:
            event_data = json.load(f)
    except Exception as e:
        print(f"Failed to parse GITHUB_EVENT_PATH: {e}", file=sys.stderr)
        exit(1)

    issue_body = event_data.get("issue", {}).get("body", "")
    if not issue_body:
        print("Issue body is empty.", file=sys.stderr)
        exit(1)

    issue_data = parse_issue_body(issue_body)

    name = issue_data.get("name", "")
    description = sanitize_description(issue_data.get("description", ""))
    homepage = issue_data.get("homepage", "")
    image = issue_data.get("image", "")
    author = os.environ.get("THEME_AUTHOR", "Unknown")

    styles_content = strip_markdown_block(issue_data.get("styles", ""), "css")
    config_content = strip_markdown_block(issue_data.get("config", ""), "yaml")
    readme_content = strip_markdown_block(issue_data.get("readme", ""), "markdown")

    validate_name(name)
    validate_description(description)
    validate_url(image)
    validate_url(homepage, allow_empty=True)

    try:
        print(
            "Starting validation of config with YASB deprecation scanner...",
            file=sys.stderr,
        )
        patched_config, issues = migrate_config(config_content)
        if issues:
            print(
                f"ERROR: Found {len(issues)} deprecation issues. Please update your config:",
                file=sys.stderr,
            )
            for issue in issues:
                print(
                    f" - {issue['action']} on {issue['path']}: {issue['message']}",
                    file=sys.stderr,
                )
            exit(1)

        print("Starting validation of config against YASB schema...", file=sys.stderr)
        config_dict = yaml.safe_load(patched_config)
        YasbConfig.model_validate(config_dict)

        # Validate individual widgets
        from importlib import import_module

        widgets = config_dict.get("widgets", {})
        for wname, wdata in widgets.items():
            if not isinstance(wdata, dict):
                continue
            wtype = wdata.get("type", "")
            if not wtype:
                continue
            try:
                mod, cls_name = wtype.rsplit(".", 1)
                schema = getattr(
                    import_module(f"core.widgets.{mod}"), cls_name
                ).validation_schema
            except Exception as e:
                print(
                    f"Warning: Could not load schema for widget type '{wtype}': {e}",
                    file=sys.stderr,
                )
                continue

            opts = wdata.get("options")
            if isinstance(opts, dict):
                try:
                    schema.model_validate(opts)
                except Exception as e:
                    print(
                        f"ERROR: Widget '{wname}' validation failed: {e}",
                        file=sys.stderr,
                    )
                    exit(1)

        print("Config validation passed successfully.", file=sys.stderr)
        config_content = patched_config
    except Exception as e:
        print(f"Config validation failed: {e}", file=sys.stderr)
        exit(1)

    theme_id = create_theme_id()
    current_time = datetime.datetime.now().isoformat()

    theme = {
        "id": theme_id,
        "name": name,
        "description": description,
        "homepage": homepage,
        "style": get_static_asset(theme_id, STYLES_FILE),
        "config": get_static_asset(theme_id, CONFIG_FILE),
        "readme": get_static_asset(theme_id, README_FILE),
        "image": get_static_asset(theme_id, IMAGE_FILE),
        "author": author,
        "publish_date": current_time,
    }
    os.makedirs(f"themes/{theme_id}")

    with open(f"themes/{theme_id}/{STYLES_FILE}", "w", encoding="utf-8") as f:
        f.write(styles_content)

    with open(f"themes/{theme_id}/{CONFIG_FILE}", "w", encoding="utf-8") as f:
        f.write(config_content)

    with open(f"themes/{theme_id}/{README_FILE}", "w", encoding="utf-8") as f:
        f.write(readme_content)

    download_image(image, f"themes/{theme_id}/{IMAGE_FILE}")
    with open(f"themes/{theme_id}/theme.json", "w", encoding="utf-8") as f:
        json.dump(theme, f, indent=4)

    # Write to GitHub Env so the PR steps can use them
    write_github_env("THEME_NAME", name)
    write_github_env("THEME_DESCRIPTION", description)
    write_github_env("THEME_HOMEPAGE", homepage)
    write_github_env("THEME_IMAGE", image)
    write_github_env("THEME_AUTHOR", author)

    print(f"Theme submitted with ID: {theme_id}")
    for key, value in theme.items():
        print(f"\t{key}: {value}")


if __name__ == "__main__":
    main()
