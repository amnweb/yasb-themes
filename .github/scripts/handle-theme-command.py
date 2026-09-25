import json
import os
import re
import sys

COMMENT_BODY = os.environ.get("ISSUE_COMMENT_BODY", "")
ISSUE_BODY = os.environ.get("ISSUE_BODY", "")
COMPATIBILITY_ISSUE = os.environ.get("COMPATIBILITY_ISSUE") == "true"
THEMES_DATA_FILE = "./themes.json"
USAGE = "Usage: /theme disable <theme-id> or /theme enable <theme-id>. In a compatibility issue the id can be left out."

COMMAND_RE = re.compile(
    r"\s*/theme\s+(disable|enable)(?:\s+([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}))?\s*",
    re.IGNORECASE,
)
MARKER_RE = re.compile(r"<!-- theme-compat:([0-9a-f-]{36}) -->")


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
    first_line = COMMENT_BODY.strip().splitlines()[0] if COMMENT_BODY.strip() else ""
    match = COMMAND_RE.fullmatch(first_line)
    if not match:
        sys.exit(USAGE)

    action = match.group(1).lower()
    theme_id = match.group(2)
    if not theme_id and COMPATIBILITY_ISSUE:
        marker = MARKER_RE.search(ISSUE_BODY)
        theme_id = marker.group(1) if marker else None
    if not theme_id:
        sys.exit(USAGE)
    theme_id = theme_id.lower()

    with open(THEMES_DATA_FILE, encoding="utf-8") as handle:
        themes_data = json.load(handle)

    if theme_id not in themes_data:
        sys.exit(f"Theme {theme_id} is not in {THEMES_DATA_FILE}.")

    disabled = action == "disable"
    theme_name = themes_data[theme_id].get("name", theme_id)

    if disabled:
        themes_data[theme_id]["disabled"] = True
    else:
        themes_data[theme_id].pop("disabled", None)

    with open(THEMES_DATA_FILE, "w", encoding="utf-8") as handle:
        json.dump(themes_data, handle, indent=4)
        handle.write("\n")

    message = f"I've {action}d theme “{theme_name}” (ID: {theme_id}). The README has been refreshed to reflect the current status."
    close_reason = "completed"
    if COMPATIBILITY_ISSUE and disabled:
        message += "\n\nThis issue stays open, and the theme is re-enabled automatically once it passes the compatibility check again."
        close_reason = ""
    elif COMPATIBILITY_ISSUE:
        message += "\n\nThe compatibility check stops tracking this theme, so this issue is closed as not planned."
        close_reason = "not planned"

    payload = {
        "theme_id": theme_id,
        "theme_name": theme_name,
        "action": action,
        "disabled": disabled,
        "message": message,
        "close_reason": close_reason,
    }
    write_output(payload)


if __name__ == "__main__":
    main()
