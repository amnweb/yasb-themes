import datetime
import io
import json
import os
import re
import sys
import urllib.parse
import uuid
import zipfile

import requests
import yaml
from PIL import Image, ImageOps
from theme_check import CheckError, Yasb, widget_names

STYLES_FILE = "styles.css"
README_FILE = "readme.md"
IMAGE_FILE = "image.png"
CONFIG_FILE = "config.yaml"
ASSETS_FOLDER = "assets"
MAX_PREVIEW_IMAGES = 5
MAX_IMAGE_SIDE = 3840
JPEG_QUALITY = 90
MAX_THEME_FILE_SIZE = 1024 * 1024
URL_RE = re.compile(r'\]\((https://[^)\s]+)\)|src="(https://[^"]+)"|(https://\S+)')
FENCE_RE = re.compile(r" {0,3}(`{3,}|~{3,})")
FORM_FIELDS = {
    "Name": "name",
    "Description": "description",
    "Theme screenshot": "image",
    "Theme files": "files",
    "About": "about",
    "Requirements": "requirements",
    "Preview images": "images",
}


def create_theme_id():
    return str(uuid.uuid4())


def get_static_asset(theme_id, asset):
    return f"https://raw.githubusercontent.com/amnweb/yasb-themes/main/themes/{theme_id}/{asset}"


def validate_url(url):
    if not url:
        url = ""
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


def extract_urls(value):
    urls = []
    for match in URL_RE.finditer(value or ""):
        url = next(group for group in match.groups() if group)
        if url not in urls:
            urls.append(url)
    return urls


def parse_issue_body(body: str) -> dict:
    labels = list(FORM_FIELDS)
    headings = []
    next_label = 0
    fence = ""
    position = 0
    for line in body.splitlines(keepends=True):
        start = position
        position += len(line)
        text = line.rstrip()
        if fence:
            closing = text.strip()
            if closing and set(closing) == {fence[0]} and len(closing) >= len(fence):
                fence = ""
            continue
        opening = FENCE_RE.match(text)
        if opening:
            fence = opening.group(1)
            continue
        for index in range(next_label, len(labels)):
            if text == f"### {labels[index]}":
                headings.append((FORM_FIELDS[labels[index]], start, position))
                next_label = index + 1
                break
    data = {}
    for index, (key, _, start) in enumerate(headings):
        end = headings[index + 1][1] if index + 1 < len(headings) else len(body)
        value = body[start:end].strip()
        data[key] = "" if value == "_No response_" else value
    return data


def requirement_lines(text):
    requirements = []
    for line in text.splitlines():
        requirement = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line).strip()
        if requirement and requirement != "_No response_":
            requirements.append(requirement)
    return requirements


def read_theme_files(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Epicture"}, timeout=60)
    except requests.RequestException:
        response = None
    if response is None or response.status_code != 200:
        print("The ZIP file in the Theme files field could not be downloaded.", file=sys.stderr)
        exit(1)
    try:
        archive = zipfile.ZipFile(io.BytesIO(response.content))
    except zipfile.BadZipFile:
        print("The file in the Theme files field is not a ZIP file.", file=sys.stderr)
        exit(1)
    found = {}
    for info in archive.infolist():
        name = info.filename.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if info.is_dir() or name not in (CONFIG_FILE, STYLES_FILE):
            continue
        if name in found:
            print(f"The ZIP file contains more than one {name}. Please include only one.", file=sys.stderr)
            exit(1)
        found[name] = info
    missing = [name for name in (CONFIG_FILE, STYLES_FILE) if name not in found]
    if missing:
        print(
            f"The ZIP file must contain {CONFIG_FILE} and {STYLES_FILE} (missing: {', '.join(missing)}).",
            file=sys.stderr,
        )
        exit(1)
    contents = {}
    for name, info in found.items():
        try:
            with archive.open(info) as f:
                data = f.read(MAX_THEME_FILE_SIZE + 1)
        except RuntimeError, NotImplementedError, OSError, zipfile.BadZipFile:
            print(f"{name} could not be read from the ZIP file.", file=sys.stderr)
            exit(1)
        if len(data) > MAX_THEME_FILE_SIZE:
            print(f"{name} in the ZIP file is too large (at most 1 MB).", file=sys.stderr)
            exit(1)
        try:
            contents[name] = data.decode("utf-8-sig").replace("\r\n", "\n")
        except UnicodeDecodeError:
            print(f"{name} must be saved as UTF-8 text.", file=sys.stderr)
            exit(1)
    return contents[CONFIG_FILE], contents[STYLES_FILE]


def save_preview_image(number, url, path):
    try:
        response = requests.get(url, headers={"User-Agent": "Epicture"}, timeout=60)
    except requests.RequestException:
        response = None
    if response is None or response.status_code != 200:
        print(f"Preview image {number} could not be downloaded.", file=sys.stderr)
        exit(1)
    try:
        image = Image.open(io.BytesIO(response.content))
        if image.format not in ("PNG", "JPEG"):
            print(f"Preview image {number} is a {image.format} file. Please upload PNG or JPG images.", file=sys.stderr)
            exit(1)
        image = ImageOps.exif_transpose(image).convert("RGBA")
    except OSError, ValueError, Image.DecompressionBombError:
        print(f"Preview image {number} could not be read as a PNG or JPG image.", file=sys.stderr)
        exit(1)
    image = Image.alpha_composite(Image.new("RGBA", image.size, (0, 0, 0, 255)), image).convert("RGB")
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
    image.save(path, format="JPEG", quality=JPEG_QUALITY, optimize=True)


def build_readme(name, about, image_urls, widgets, requirements):
    parts = [f"# {name}", about, "## Screenshots"]
    parts += [f"![{name} preview {number}]({url})" for number, url in enumerate(image_urls, 1)]
    if widgets:
        parts.append("## Widgets\n\n" + "\n".join(f"- {widget}" for widget in widgets))
    if requirements:
        parts.append("## Requirements\n\n" + "\n".join(f"- {requirement}" for requirement in requirements))
    return "\n\n".join(parts) + "\n"


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
    image_urls = extract_urls(issue_data.get("image", ""))
    file_urls = extract_urls(issue_data.get("files", ""))
    preview_urls = extract_urls(issue_data.get("images", ""))
    author = os.environ.get("THEME_AUTHOR", "Unknown")

    about = strip_markdown_block(issue_data.get("about", ""), "markdown")
    requirements = requirement_lines(strip_markdown_block(issue_data.get("requirements", ""), "markdown"))

    validate_name(name)
    validate_description(description)
    if len(image_urls) != 1:
        print(
            f"Please upload exactly one PNG screenshot of your bar in the Theme screenshot field (found {len(image_urls)}).",
            file=sys.stderr,
        )
        exit(1)
    if len(file_urls) != 1:
        print(
            f"Please upload one ZIP file with {CONFIG_FILE} and {STYLES_FILE} in the Theme files field "
            f"(found {len(file_urls)}).",
            file=sys.stderr,
        )
        exit(1)
    if not about:
        print("Please write a few words about your theme in the About field.", file=sys.stderr)
        exit(1)
    if not 1 <= len(preview_urls) <= MAX_PREVIEW_IMAGES:
        print(
            f"Please upload 1 to {MAX_PREVIEW_IMAGES} PNG or JPG images in the Preview images field "
            f"(found {len(preview_urls)}).",
            file=sys.stderr,
        )
        exit(1)
    image = image_urls[0]
    validate_url(image)

    config_content, styles_content = read_theme_files(file_urls[0])
    if not styles_content.strip():
        print(f"{STYLES_FILE} is empty. YASB does not start with an empty stylesheet.", file=sys.stderr)
        exit(1)

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
    widgets = widget_names(yaml.safe_load(config_content))

    theme_id = create_theme_id()
    current_time = datetime.datetime.now().isoformat()

    theme = {
        "id": theme_id,
        "name": name,
        "description": description,
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

    download_image(image, f"themes/{theme_id}/{IMAGE_FILE}")

    os.makedirs(f"themes/{theme_id}/{ASSETS_FOLDER}")
    preview_assets = []
    for number, url in enumerate(preview_urls, 1):
        asset = f"{ASSETS_FOLDER}/preview-{number}.jpg"
        save_preview_image(number, url, f"themes/{theme_id}/{asset}")
        preview_assets.append(get_static_asset(theme_id, asset))

    with open(f"themes/{theme_id}/{README_FILE}", "w", encoding="utf-8") as f:
        f.write(build_readme(name, about, preview_assets, widgets, requirements))

    with open(f"themes/{theme_id}/theme.json", "w", encoding="utf-8") as f:
        json.dump(theme, f, indent=4)

    # Write to GitHub Env so the PR steps can use them
    write_github_env("THEME_NAME", name)
    write_github_env("THEME_DESCRIPTION", description)
    write_github_env("THEME_IMAGE", image)
    write_github_env("THEME_AUTHOR", author)

    print(f"Theme submitted with ID: {theme_id}")
    for key, value in theme.items():
        print(f"\t{key}: {value}")


if __name__ == "__main__":
    main()
