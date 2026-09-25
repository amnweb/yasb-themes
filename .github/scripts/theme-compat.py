import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta

THEMES_DATA_FILE = "themes.json"
LABEL = "theme-compatibility"
DISABLED_LABEL = "theme-disabled"
LABEL_SETTINGS = {
    LABEL: ("d93f0b", "Theme fails the automated YASB compatibility check"),
    DISABLED_LABEL: ("b60205", "Theme was disabled by the compatibility check"),
}
MARKER = "<!-- theme-compat:{} -->"
MARKER_RE = re.compile(r"<!-- theme-compat:([0-9a-f-]{36}) -->")
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "amnweb/yasb-themes")


def gh(*args, stdin=None):
    result = subprocess.run(["gh", *args], capture_output=True, encoding="utf-8", input=stdin)
    if result.returncode != 0:
        raise RuntimeError(f"`gh {' '.join(args[:2])}` failed: {result.stderr.strip()}")
    return result.stdout


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def marked_theme(issue):
    match = MARKER_RE.search(issue.get("body") or "")
    return match.group(1) if match else None


def load_issues():
    open_issues = json.loads(
        gh("issue", "list", "--label", LABEL, "--state", "open", "--limit", "500", "--json", "number,createdAt,body")
    )
    closed_issues = json.loads(
        gh(
            "issue",
            "list",
            "--label",
            LABEL,
            "--state",
            "closed",
            "--limit",
            "500",
            "--json",
            "number,stateReason,body",
        )
    )
    tracked = {}
    for issue in sorted(open_issues, key=lambda issue: issue["number"]):
        theme_id = marked_theme(issue)
        if theme_id and theme_id not in tracked:
            tracked[theme_id] = issue
    ignored = set()
    seen = set()
    for issue in sorted(closed_issues, key=lambda issue: issue["number"], reverse=True):
        theme_id = marked_theme(issue)
        if theme_id and theme_id not in seen:
            seen.add(theme_id)
            if issue.get("stateReason") == "NOT_PLANNED":
                ignored.add(theme_id)
    return tracked, ignored - set(tracked)


def load_pull_requests():
    touched = {}
    for pull_request in json.loads(gh("pr", "list", "--state", "open", "--limit", "200", "--json", "number,files")):
        for file in pull_request.get("files") or []:
            parts = file["path"].split("/")
            if len(parts) > 2 and parts[0] == "themes":
                touched.setdefault(parts[1], set()).add(pull_request["number"])
    return {theme_id: sorted(numbers) for theme_id, numbers in touched.items()}


def deadline_for(issue, grace_days):
    return (parse_time(issue["createdAt"]) + timedelta(days=grace_days)).date()


def issue_body(theme, yasb, deadline, pull_requests=(), disabled=False):
    theme_id = theme["id"]
    folder_url = f"https://github.com/{REPOSITORY}/tree/main/themes/{theme_id}"
    edit_url = f"https://github.com/{REPOSITORY}/edit/main/themes/{theme_id}/config.yaml"
    if disabled:
        status = [
            "### Theme disabled",
            "",
            "This theme has been **disabled** in the theme gallery because it still failed the check after the deadline. "
            "It is re-enabled automatically once a fix is merged and the theme passes the check again.",
        ]
    else:
        status = [
            "### Deadline",
            "",
            f"If the theme still fails the check on **{deadline:%A}, {deadline.day} {deadline:%B %Y}**, "
            "and there is no open pull request for it, the theme will be disabled in the theme gallery. "
            "A disabled theme is re-enabled automatically once it passes the check again.",
        ]
        if pull_requests:
            numbers = ", ".join(f"#{number}" for number in pull_requests)
            status += ["", f"The theme will not be disabled while {numbers} is open."]
    greeting = f"Hi @{theme['author']}," if theme["author"] else "Hi,"
    lines = [
        MARKER.format(theme_id),
        greeting,
        "",
        f"Your theme **[{theme['name']}]({folder_url})** does not pass the automated compatibility check "
        f"against {yasb['description']}, the latest YASB release. "
        "Please update it so it keeps working for everyone who installs it from the theme gallery.",
        "",
        "### What needs to change",
        "",
        theme["details"],
        "",
        "### How to fix it",
        "",
        f"1. Update the files in [`themes/{theme_id}`]({folder_url}). The quickest way is to "
        f"[edit `config.yaml` on GitHub]({edit_url}), which opens a pull request for you.",
        "2. Pull requests that change a theme are checked automatically, so you will see whether everything is fixed "
        "before it is merged.",
        "3. Once the fix is merged, this issue is closed automatically.",
        "",
        *status,
        "",
        "---",
        "<sub>This issue is opened and updated by the daily theme compatibility check. "
        'Maintainers can close it as "not planned" to stop tracking this theme.</sub>',
    ]
    return "\n".join(lines)


def normalized(body):
    return (body or "").replace("\r\n", "\n").strip()


def plan_actions(report, themes_data, existing, tracked, ignored, pull_requests, now, grace_days):
    yasb = report["yasb"]
    results = {theme["id"]: theme for theme in report["themes"]}
    actions = []
    for theme_id, issue in tracked.items():
        if theme_id not in results and theme_id not in existing:
            actions.append(
                {
                    "action": "close",
                    "theme": theme_id,
                    "name": theme_id,
                    "issue": issue["number"],
                    "enable": False,
                    "comment": "This theme no longer exists in the repository, so there is nothing left to check.",
                }
            )

    for theme_id, theme in results.items():
        entry = themes_data.get(theme_id)
        if entry is None:
            continue
        disabled = bool(entry.get("disabled"))
        issue = tracked.get(theme_id)
        base = {"theme": theme_id, "name": theme["name"]}

        if theme["ok"]:
            if issue:
                comment = f"✅ **{theme['name']}** now passes the compatibility check against {yasb['description']}. Thank you!"
                if disabled:
                    comment += " The theme has been re-enabled in the theme gallery."
                actions.append(
                    {**base, "action": "close", "issue": issue["number"], "enable": disabled, "comment": comment}
                )
            continue

        if issue is None:
            if disabled:
                actions.append({**base, "action": "skip", "reason": "disabled by a maintainer, not tracked"})
            elif theme_id in ignored:
                actions.append(
                    {**base, "action": "skip", "reason": "ignored, the last issue was closed as not planned"}
                )
            else:
                deadline = (now + timedelta(days=grace_days)).date()
                actions.append(
                    {
                        **base,
                        "action": "open",
                        "author": theme["author"],
                        "title": f"[theme-compat]: {theme['name']} needs an update",
                        "body": issue_body(theme, yasb, deadline),
                        "deadline": f"{deadline:%Y-%m-%d}",
                    }
                )
            continue

        numbers = pull_requests.get(theme_id, [])
        deadline = deadline_for(issue, grace_days)
        disable = not disabled and now.date() >= deadline and not numbers
        body = issue_body(theme, yasb, deadline, numbers, disabled or disable)
        details = {**base, "issue": issue["number"], "body": body, "deadline": f"{deadline:%Y-%m-%d}"}
        if disable:
            mention = f"@{theme['author']} " if theme["author"] else ""
            comment = (
                f"{mention}**{theme['name']}** still fails the compatibility check, so it has been disabled in the theme gallery. "
                "It is re-enabled automatically once a fix is merged and the theme passes the check again. "
                "The issue description lists what needs to change."
            )
            actions.append({**details, "action": "disable", "comment": comment})
        else:
            changed = normalized(body) != normalized(issue["body"])
            actions.append(
                {**details, "action": "update" if changed else "keep", "disabled": disabled, "pull_requests": numbers}
            )
    return actions


def describe(action):
    issue = f"#{action['issue']}" if action.get("issue") else ""
    kind = action["action"]
    if kind == "open":
        return f"Open an issue for `{action['author'] or 'unknown'}`, deadline {action['deadline']}"
    if kind == "disable":
        return f"Disable the theme and comment on {issue}"
    if kind == "close":
        return f"Close {issue}" + (" and re-enable the theme" if action["enable"] else "")
    if kind == "skip":
        return f"Nothing to do: {action['reason']}"
    if action["disabled"]:
        state = "theme is disabled"
    elif action["pull_requests"]:
        state = "waiting for " + ", ".join(f"#{number}" for number in action["pull_requests"])
    else:
        state = f"deadline {action['deadline']}"
    return f"{'Update' if kind == 'update' else 'Keep'} {issue}, {state}"


def write_summary(path, actions, dry_run, note=""):
    lines = ["## Compatibility issues", ""]
    if dry_run:
        lines += ["> [!NOTE]", "> Dry run, nothing was changed.", ""]
    if note:
        lines += [note, ""]
    if actions:
        lines += ["| Theme | Action |", "| --- | --- |"]
        lines += [f"| {action['name']} | {describe(action)} |" for action in actions]
    else:
        lines.append("Nothing to do.")
    text = "\n".join(lines) + "\n"
    print(text)
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)


def update_themes_data(themes_data, actions):
    disabled = []
    enabled = []
    for action in actions:
        entry = themes_data.get(action["theme"])
        if entry is None:
            continue
        if action["action"] == "disable":
            entry["disabled"] = True
            disabled.append(action["name"])
        elif action["action"] == "close" and action["enable"]:
            entry.pop("disabled", None)
            enabled.append(action["name"])
    lines = []
    if disabled:
        lines.append(f"Disabled: {', '.join(disabled)}")
    if enabled:
        lines.append(f"Re-enabled: {', '.join(enabled)}")
    return lines


def command_plan(args):
    with open(args.report, encoding="utf-8") as f:
        report = json.load(f)
    if report.get("error"):
        sys.exit(f"The theme check could not run, so no issues were changed: {report['error']}")
    themes_data = {}
    if os.path.exists(THEMES_DATA_FILE):
        with open(THEMES_DATA_FILE, encoding="utf-8") as f:
            themes_data = json.load(f)

    existing = set(os.listdir("themes")) if os.path.isdir("themes") else set()
    tracked, ignored = load_issues()
    pull_requests = load_pull_requests()
    now = datetime.now(UTC)
    actions = plan_actions(report, themes_data, existing, tracked, ignored, pull_requests, now, args.grace_days)
    if args.close_only:
        actions = [action for action in actions if action["action"] == "close"]

    new_issues = sum(action["action"] == "open" for action in actions)
    if new_issues > args.max_new_issues:
        note = (
            f"> [!CAUTION]\n> {new_issues} themes would get a new issue, more than the limit of {args.max_new_issues}. "
            "This usually means a YASB change broke many themes at once, or the check itself is broken. "
            "Nothing was changed. If this is expected, run the workflow manually with a higher `max_new_issues`."
        )
        write_summary(args.summary, actions, args.dry_run, note)
        sys.exit(1)

    status_lines = update_themes_data(themes_data, actions)
    write_summary(args.summary, actions, args.dry_run)
    with open(args.plan, "w", encoding="utf-8") as f:
        json.dump([action for action in actions if action["action"] not in ("keep", "skip")], f, indent=2)
    if args.dry_run or not status_lines:
        return
    with open(THEMES_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(themes_data, f, indent=4)
    with open(args.commit_message, "w", encoding="utf-8") as f:
        f.write("Update theme status after compatibility check\n\n" + "\n".join(status_lines) + "\n")


def command_apply(args):
    with open(args.plan, encoding="utf-8") as f:
        actions = json.load(f)
    if not actions:
        print("Nothing to do.")
        return
    for name, (color, description) in LABEL_SETTINGS.items():
        gh("label", "create", name, "--color", color, "--description", description, "--force")
    for action in actions:
        number = str(action.get("issue", ""))
        print(f"{action['name']}: {describe(action)}")
        if action["action"] == "open":
            url = gh(
                "issue",
                "create",
                "--title",
                action["title"],
                "--label",
                LABEL,
                "--body-file",
                "-",
                stdin=action["body"],
            )
            print(f"  {url.strip()}")
        elif action["action"] == "update":
            gh("issue", "edit", number, "--body-file", "-", stdin=action["body"])
        elif action["action"] == "disable":
            gh("issue", "edit", number, "--add-label", DISABLED_LABEL, "--body-file", "-", stdin=action["body"])
            gh("issue", "comment", number, "--body-file", "-", stdin=action["comment"])
        elif action["action"] == "close":
            gh("issue", "close", number, "--reason", "completed", "--comment", action["comment"])
        time.sleep(1)


def command_tracked_in_pr(args):
    files = json.loads(gh("pr", "view", str(args.number), "--json", "files"))["files"]
    touched = {
        parts[1] for parts in (file["path"].split("/") for file in files) if len(parts) > 2 and parts[0] == "themes"
    }
    tracked, _ = load_issues()
    print(" ".join(sorted(touched & set(tracked))))


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Open, update and close theme compatibility issues.")
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="Decide what to do and update themes.json.")
    plan.add_argument("--report", required=True)
    plan.add_argument("--plan", required=True)
    plan.add_argument("--commit-message", default="commit-message.txt")
    plan.add_argument("--summary")
    plan.add_argument("--grace-days", type=int, default=7)
    plan.add_argument("--max-new-issues", type=int, default=25)
    plan.add_argument("--dry-run", action="store_true")
    plan.add_argument("--close-only", action="store_true", help="Only close issues of themes that pass now.")
    apply = commands.add_parser("apply", help="Open, update and close the planned issues.")
    apply.add_argument("--plan", required=True)
    tracked = commands.add_parser(
        "tracked-in-pr", help="Print the themes changed by a pull request that have an open issue."
    )
    tracked.add_argument("number", type=int)
    args = parser.parse_args()
    if args.command == "plan":
        command_plan(args)
    elif args.command == "apply":
        command_apply(args)
    else:
        command_tracked_in_pr(args)


if __name__ == "__main__":
    main()
