import json
import os
import re
import sys

COMMENT_BODY = os.environ.get("ISSUE_COMMENT_BODY", "")
THEMES_DATA_FILE = "./themes.json"

COMMAND_RE = re.compile(
    r"^\s*/yasbbot\s+(disable|enable)\s+theme\s+([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\b",
    re.IGNORECASE,
)


def write_output(payload: dict) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        print(json.dumps(payload, indent=2))
        return

    with open(output_file, "a", encoding="utf-8") as handle:
        handle.write("result_json<<EOF\n")
        handle.write(json.dumps(payload, indent=2))
        handle.write("\nEOF\n")


def main() -> None:
    match = COMMAND_RE.search(COMMENT_BODY)
    if not match:
        payload = {
            "status": "ignored",
        }
        write_output(payload)
        sys.exit(0)

    action = match.group(1).lower()
    theme_id = match.group(2)

    if not os.path.exists(THEMES_DATA_FILE):
        payload = {"status": "error"}
        write_output(payload)
        sys.exit(1)

    with open(THEMES_DATA_FILE, "r", encoding="utf-8") as handle:
        themes_data = json.load(handle)

    if theme_id not in themes_data:
        payload = {"status": "error"}
        write_output(payload)
        sys.exit(1)

    disabled = action == "disable"
    theme_name = themes_data[theme_id].get("name", theme_id)
    
    if disabled:
        themes_data[theme_id]["disabled"] = True
    else:
        themes_data[theme_id].pop("disabled", None)

    with open(THEMES_DATA_FILE, "w", encoding="utf-8") as handle:
        json.dump(themes_data, handle, indent=4)
        handle.write("\n")

    payload = {
        "theme_id": theme_id,
        "theme_name": theme_name,
        "action": action,
        "disabled": disabled,
    }
    write_output(payload)


if __name__ == "__main__":
    main()
