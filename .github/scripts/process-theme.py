import datetime
import json
import os
import re
import sys
import urllib.parse
import uuid

import requests
from theme_check import CheckError, Yasb

STYLES_FILE = "styles.css"
README_FILE = "readme.md"
IMAGE_FILE = "image.png"
CONFIG_FILE = "config.yaml"
IMAGE_URL_RE = re.compile(r'\]\((https://[^)\s]+)\)|src="(https://[^"]+)"|(https://\S+)')
FORM_FIELDS = {
    "Name": "name",
    "Description": "description",
    "Homepage": "homepage",
    "Image": "image",
    "Theme Styles": "styles",
    "Theme Config": "config",
    "Readme": "readme",
}


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
            print("Name must only contain letters, numbers, and spaces.", file=sys.stderr)
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


def extract_image_urls(value):
    urls = []
    for match in IMAGE_URL_RE.finditer(value or ""):
        url = next(group for group in match.groups() if group)
        if url not in urls:
            urls.append(url)
    return urls


def parse_issue_body(body: str) -> dict:
    headings = []
    position = 0
    for label, key in FORM_FIELDS.items():
        match = re.compile(rf"^### {re.escape(label)}[ \t]*\r?$", re.MULTILINE).search(body, position)
        if match:
            headings.append((key, match.start(), match.end()))
            position = match.end()
    data = {}
    for index, (key, _, start) in enumerate(headings):
        end = headings[index + 1][1] if index + 1 < len(headings) else len(body)
        value = body[start:end].strip()
        data[key] = "" if value == "_No response_" else value
    return data


def main():
    # Windows runners default to cp1252 for redirected output, which cannot encode many config values.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        print("GITHUB_EVENT_PATH is missing or file does not exist.", file=sys.stderr)
        exit(1)

    try:
        with open(event_path, encoding="utf-8") as f:
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
    image_urls = extract_image_urls(issue_data.get("image", ""))
    author = os.environ.get("THEME_AUTHOR", "Unknown")

    styles_content = strip_markdown_block(issue_data.get("styles", ""), "css")
    config_content = strip_markdown_block(issue_data.get("config", ""), "yaml")
    readme_content = strip_markdown_block(issue_data.get("readme", ""), "markdown")

    validate_name(name)
    validate_description(description)
    if len(image_urls) != 1:
        print(
            f"Please upload exactly one PNG screenshot of your bar in the Image field (found {len(image_urls)}).",
            file=sys.stderr,
        )
        exit(1)
    image = image_urls[0]
    validate_url(image)
    validate_url(homepage, allow_empty=True)

    try:
        problems, _, _ = Yasb("./yasb-repo/src").check_config(config_content)
    except CheckError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        exit(1)
    if problems:
        print(f"ERROR: Found {len(problems)} problem(s) in your config. Please update it:", file=sys.stderr)
        for problem in problems:
            location = ", ".join(
                part for part in (problem.path, f"line {problem.line}" if problem.line else "") if part
            )
            print(f" - {location}: {problem.message}" if location else f" - {problem.message}", file=sys.stderr)
        exit(1)
    print("Config validation passed successfully.", file=sys.stderr)

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
