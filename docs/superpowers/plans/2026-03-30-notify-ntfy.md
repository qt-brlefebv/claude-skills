# notify-ntfy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained Claude Code skill that sends ntfy.sh push notifications when Claude is waiting for user input, with guided setup, runtime config, and an interruptible timer.

**Architecture:** A Python script (`ntfy-hook.py`) handles all runtime behavior (timer, sending, config I/O). A skill markdown file (`notify-ntfy.md`) provides the user-facing subcommands that invoke the script and manage `settings.json` hooks. Config lives in a JSON file alongside the script.

**Tech Stack:** Python 3.8+ (stdlib only: `urllib.request`, `json`, `time`, `tempfile`, `getpass`, `platform`, `os`, `sys`), Claude Code skills (markdown + YAML frontmatter)

**Spec:** `docs/superpowers/specs/2026-03-30-notify-ntfy-design.md`

---

## File Structure

```
notify-ntfy/
  notify-ntfy.md      — skill file (subcommand dispatch, setup wizard, config management)
  ntfy-hook.py         — Python script (timer, notification sending, config I/O, marker management)
  README.md            — installation and usage docs
```

No test files — this is a standalone script with no importable modules. Verification is done via `/ntfy test` (sends a real notification) and manual hook testing.

---

### Task 1: Create `ntfy-hook.py` — config management

**Files:**
- Create: `notify-ntfy/ntfy-hook.py`

- [ ] **Step 1: Create the script with config helpers**

Write `ntfy-hook.py` with:
- Shebang line `#!/usr/bin/env python3`
- `CONFIG_DIR` — resolved at runtime as the directory containing the script (`os.path.dirname(os.path.abspath(__file__))`)
- `CONFIG_FILE` — `os.path.join(CONFIG_DIR, "ntfy-config.json")`
- `DEFAULT_CONFIG` dict with:
  - `"topic"`: `f"{getpass.getuser()}_claude_{platform.node()}"`
  - `"timer_seconds"`: `60`
  - `"server"`: `"https://ntfy.sh"`
  - `"enabled"`: `True`
- `load_config()` — read and return config JSON; return `None` if file doesn't exist
- `save_config(config)` — write config JSON with indent=2
- `ensure_config()` — load config, or generate defaults and save, then return config

```python
#!/usr/bin/env python3
"""ntfy-hook.py — Claude Code notification hook for ntfy.sh."""

import getpass
import json
import os
import platform
import sys
import time
import tempfile
import urllib.request
import urllib.error

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, "ntfy-config.json")


def default_config():
    return {
        "topic": f"{getpass.getuser()}_claude_{platform.node()}",
        "timer_seconds": 60,
        "server": "https://ntfy.sh",
        "enabled": True,
    }


def load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def ensure_config():
    config = load_config()
    if config is None:
        config = default_config()
        save_config(config)
    return config
```

- [ ] **Step 2: Add `ntfy-config.json` to `.gitignore`**

Append `ntfy-config.json` to `notify-ntfy/.gitignore` (create if needed) so
config files generated during development/testing aren't committed:

```
ntfy-config.json
```

- [ ] **Step 3: Verify the script parses without errors**

Run: `python notify-ntfy/ntfy-hook.py 2>&1; echo "exit: $?"`
Expected: some usage error or clean exit (no syntax errors)

- [ ] **Step 4: Commit**

```bash
git add notify-ntfy/ntfy-hook.py notify-ntfy/.gitignore
git commit -m "Add ntfy-hook.py with config management"
```

---

### Task 2: Create `ntfy-hook.py` — notification sending

**Files:**
- Modify: `notify-ntfy/ntfy-hook.py`

- [ ] **Step 1: Add the send_notification function**

Append to `ntfy-hook.py`:

```python
def send_notification(config, title, body):
    url = f"{config['server'].rstrip('/')}/{config['topic']}"
    data = body.encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "text/plain")
    req.add_header("Title", title)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 201, 202)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
        print(f"ntfy error: {e}", file=sys.stderr)
        return False
```

- [ ] **Step 2: Add the `test` subcommand handler**

```python
def cmd_test():
    config = ensure_config()
    hostname = platform.node()
    project = os.path.basename(os.getcwd())
    title = f"Claude Code [{hostname} :: {project}]"
    body = "Test notification — ntfy is working!"
    ok = send_notification(config, title, body)
    if ok:
        print("OK: test notification sent")
    else:
        print("FAIL: could not send notification", file=sys.stderr)
    sys.exit(0 if ok else 1)
```

- [ ] **Step 3: Add minimal argument dispatch to verify test works**

```python
def main():
    if len(sys.argv) < 2:
        print("Usage: ntfy-hook.py <notify|cancel|test>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    if command == "test":
        cmd_test()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify test subcommand works**

Run: `python notify-ntfy/ntfy-hook.py test`
Expected: `OK: test notification sent` (or `FAIL` if no network — either way, no crash)

- [ ] **Step 5: Commit**

```bash
git add notify-ntfy/ntfy-hook.py
git commit -m "Add notification sending and test subcommand"
```

---

### Task 3: Create `ntfy-hook.py` — notify with timer and marker

**Files:**
- Modify: `notify-ntfy/ntfy-hook.py`

- [ ] **Step 1: Add marker file helpers**

```python
def marker_path():
    ppid = os.getppid()
    return os.path.join(tempfile.gettempdir(), f"claude-ntfy-{ppid}.pending")


def write_marker():
    path = marker_path()
    data = {"pid": os.getpid(), "timestamp": time.time()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def read_marker():
    path = marker_path()
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def remove_marker():
    path = marker_path()
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def cleanup_stale_markers(max_age_seconds):
    tmpdir = tempfile.gettempdir()
    now = time.time()
    for name in os.listdir(tmpdir):
        if name.startswith("claude-ntfy-") and name.endswith(".pending"):
            full = os.path.join(tmpdir, name)
            try:
                with open(full, encoding="utf-8") as f:
                    data = json.load(f)
                if now - data.get("timestamp", 0) > max_age_seconds:
                    os.remove(full)
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                pass
```

- [ ] **Step 2: Add stdin reading for hook context**

```python
def read_hook_context():
    try:
        if sys.stdin.isatty():
            return None
        raw = sys.stdin.read()
        if not raw.strip():
            return None
        return json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return None


def extract_tool_name(context):
    if context is None:
        return None
    # Try common payload shapes — exact schema to be verified during testing
    for key in ("tool_name", "toolName", "tool"):
        if key in context:
            return context[key]
    return None
```

- [ ] **Step 3: Add the `notify` subcommand handler**

```python
def cmd_notify():
    config = ensure_config()
    if not config.get("enabled", True):
        sys.exit(0)

    context = read_hook_context()
    tool_name = extract_tool_name(context)

    timer = config.get("timer_seconds", 60)
    cleanup_stale_markers(timer * 2)
    write_marker()

    time.sleep(timer)

    marker = read_marker()
    if marker is None or marker.get("pid") != os.getpid():
        sys.exit(0)

    remove_marker()

    hostname = platform.node()
    project = os.path.basename(os.getcwd())
    title = f"Claude Code [{hostname} :: {project}]"
    body = f"Waiting for: {tool_name}" if tool_name else "Waiting for: your response"

    send_notification(config, title, body)
```

- [ ] **Step 4: Add the `cancel` subcommand handler**

Falls back to removing all markers if the PPID-specific one isn't found (handles
cases where the hook runner's PPID differs from the notify process's PPID).

```python
def cmd_cancel():
    path = marker_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    else:
        # PPID may differ — remove all pending markers as fallback
        tmpdir = tempfile.gettempdir()
        for name in os.listdir(tmpdir):
            if name.startswith("claude-ntfy-") and name.endswith(".pending"):
                try:
                    os.remove(os.path.join(tmpdir, name))
                except FileNotFoundError:
                    pass
```

- [ ] **Step 5: Update main() dispatch**

Replace the existing `main()` with:

```python
def main():
    if len(sys.argv) < 2:
        print("Usage: ntfy-hook.py <notify|cancel|test>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    if command == "notify":
        cmd_notify()
    elif command == "cancel":
        cmd_cancel()
    elif command == "test":
        cmd_test()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 6: Verify cancel works (no crash on missing marker)**

Run: `python notify-ntfy/ntfy-hook.py cancel; echo "exit: $?"`
Expected: exit 0, no output

- [ ] **Step 7: Verify notify doesn't crash (quick syntax/import check)**

Run: `python -c "import py_compile; py_compile.compile('notify-ntfy/ntfy-hook.py', doraise=True)"`
Expected: no output (success)

- [ ] **Step 8: Commit**

```bash
git add notify-ntfy/ntfy-hook.py
git commit -m "Add notify/cancel subcommands with timer and marker logic"
```

---

### Task 4: Create `notify-ntfy.md` — skill file

**Files:**
- Create: `notify-ntfy/notify-ntfy.md`

- [ ] **Step 1: Write the skill file**

The skill file dispatches subcommands and guides the user through setup. It instructs Claude how to handle each `/ntfy` subcommand.

```markdown
---
name: notify-ntfy
description: >
  Send push notifications via ntfy.sh when Claude is waiting. Use for setup,
  testing, configuring, enabling/disabling ntfy notifications. Trigger on
  "ntfy", "notifications", "notify", "push notification".
aliases:
  - ntfy
user_invocable: true
---

# ntfy.sh Notification Skill

Push notifications to your phone when Claude Code is waiting for your input.

## Arguments

User args: `{{ args }}`

Parse the first word of args as the subcommand. If no args, show a brief help
message listing available subcommands.

## Subcommand: setup

First-time guided setup.

### Step 1: Verify installation

Check that `ntfy-hook.py` exists in the same directory as this skill file.
Use Glob to search for `**/notify-ntfy/ntfy-hook.py` under `~/.claude/skills/`.

If not found, tell the user:
> ntfy-hook.py not found. Install the full notify-ntfy folder:
> ```
> cp -r notify-ntfy/ ~/.claude/skills/notify-ntfy/
> ```

Then stop.

### Step 2: Generate config

Run:
```bash
python <SCRIPT_PATH>/ntfy-hook.py test 2>&1 | head -1
```

This triggers `ensure_config()` which creates `ntfy-config.json` with defaults
if it doesn't exist. Then read the config file and display the values to the user.

If config already exists, show the current values and ask if the user wants to
regenerate with defaults.

### Step 3: Guide phone subscription

Tell the user:
> Your ntfy topic is: `<TOPIC>`
>
> To receive notifications:
> 1. Install the ntfy app — Android (Play Store) or iOS (App Store)
> 2. Open the app and tap "+" to subscribe
> 3. Enter your topic: `<TOPIC>`
> 4. If using a custom server, set the server URL to: `<SERVER>`

### Step 4: Write hooks

Read `~/.claude/settings.json`. Check if any hook command already contains
`ntfy-hook.py`. If found, report hooks are already installed and skip.

If not found, resolve the absolute path to `ntfy-hook.py` (use the path from
Step 1, NOT `~`). Merge these hooks into the existing settings:

Under `"hooks"."Notification"`, add:
```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python <ABSOLUTE_PATH>/ntfy-hook.py notify",
      "async": true
    }
  ]
}
```

Under `"hooks"."UserPromptSubmit"`, add:
```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python <ABSOLUTE_PATH>/ntfy-hook.py cancel"
    }
  ]
}
```

Preserve all existing hooks. Write the merged settings back.

### Step 5: Test

Run: `python <SCRIPT_PATH>/ntfy-hook.py test`

Report the result. Ask the user to confirm they received the notification on
their phone.

### Step 6: Done

Report success. Remind the user they can use:
- `/ntfy test` — send a test notification
- `/ntfy config` — view or change settings
- `/ntfy disable` / `/ntfy enable` — toggle notifications

## Subcommand: test

Run: `python <SCRIPT_PATH>/ntfy-hook.py test`

Report success or failure.

## Subcommand: config

If additional args are provided (e.g., `config timer 90`), parse the key and
value. Read the config file, update the key, write it back:

- `timer <N>` → set `timer_seconds` to integer N
- `topic <name>` → set `topic` to the string
- `server <url>` → set `server` to the string

If no additional args, display current config values (same as `status`).

## Subcommand: status

Read and display `ntfy-config.json` values. Also check `~/.claude/settings.json`
for the presence of ntfy hooks and report whether they are installed.

## Subcommand: enable

Read config, set `enabled` to `true`, save. Report: "Notifications enabled."

## Subcommand: disable

Read config, set `enabled` to `false`, save. Report: "Notifications paused."

## Subcommand: (none / help)

Display:
> **ntfy.sh Notification Skill**
>
> Commands:
> - `/ntfy setup` — first-time setup wizard
> - `/ntfy test` — send a test notification
> - `/ntfy config [key] [value]` — view or change settings
> - `/ntfy status` — show current config and hook status
> - `/ntfy enable` / `/ntfy disable` — toggle notifications

## Resolving Script Path

Throughout this skill, `<SCRIPT_PATH>` means the absolute path to the directory
containing `ntfy-hook.py`. Resolve it by searching for the file:

```
~/.claude/skills/notify-ntfy/ntfy-hook.py
```

Use the absolute expanded path (e.g., `C:/Users/brlefebv/.claude/skills/notify-ntfy/ntfy-hook.py`),
NOT `~`. This is critical on Windows where `~` does not expand in all contexts.
```

- [ ] **Step 2: Verify the frontmatter parses correctly**

Run:
```bash
python -c "
content = open('notify-ntfy/notify-ntfy.md', encoding='utf-8').read()
parts = content.split('---', 2)
assert len(parts) >= 3, 'No frontmatter delimiters'
print('OK: frontmatter found')
print(parts[1].strip()[:200])
"
```
Expected: `OK: frontmatter found` followed by the YAML fields

- [ ] **Step 3: Commit**

```bash
git add notify-ntfy/notify-ntfy.md
git commit -m "Add notify-ntfy skill file with subcommand dispatch"
```

---

### Task 5: Create `README.md`

**Files:**
- Create: `notify-ntfy/README.md`

- [ ] **Step 1: Write the README**

```markdown
# notify-ntfy

Push notifications via [ntfy.sh](https://ntfy.sh) when Claude Code is waiting
for your input.

## What it does

When Claude finishes work and needs your input, a notification is sent to your
phone after a configurable delay (default: 60 seconds). If you respond before
the timer expires, the notification is cancelled.

Notifications include the hostname, project name, and what Claude is waiting
for (e.g., "Waiting for: Edit").

## Installation

Copy the `notify-ntfy/` folder to your Claude Code skills directory:

```bash
cp -r notify-ntfy/ ~/.claude/skills/notify-ntfy/
```

Then run `/ntfy setup` in Claude Code to configure hooks and subscribe on your
phone.

## Requirements

- Python 3.8+ on PATH (as `python`)
- Network access to ntfy.sh (or your own ntfy server)
- ntfy app on your phone ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [iOS](https://apps.apple.com/app/ntfy/id1625396347))

## Commands

| Command | Description |
|---------|-------------|
| `/ntfy setup` | First-time setup wizard |
| `/ntfy test` | Send a test notification |
| `/ntfy config [key] [value]` | View or change settings |
| `/ntfy status` | Show current config and hook status |
| `/ntfy enable` | Enable notifications |
| `/ntfy disable` | Pause notifications |

## Configuration

Config is stored at `~/.claude/skills/notify-ntfy/ntfy-config.json`:

| Key | Default | Description |
|-----|---------|-------------|
| `topic` | `<user>_claude_<host>` | ntfy topic name |
| `timer_seconds` | `60` | Seconds to wait before sending |
| `server` | `https://ntfy.sh` | ntfy server URL |
| `enabled` | `true` | Toggle notifications |

## How it works

Two Claude Code hooks power the notifications:

1. **Notification hook** (async) — starts a timer; if not cancelled, sends a
   push notification via ntfy.sh
2. **UserPromptSubmit hook** — cancels any pending timer when you respond

The hooks call `ntfy-hook.py` which manages the timer, config, and sending.
```

- [ ] **Step 2: Commit**

```bash
git add notify-ntfy/README.md
git commit -m "Add notify-ntfy README"
```

---

### Task 6: Update repo README and verify

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add notify-ntfy to the skills list in the repo README**

Add to the skills list in `README.md`:

```markdown
- **[notify-ntfy](notify-ntfy/)** — Push notifications via ntfy.sh when Claude Code is waiting for input
```

Also update the Installation section to note that some skills (like notify-ntfy)
require copying the entire folder rather than just the `.md` file. Add a note
after the existing user-level instructions:

```markdown
> **Note:** Some skills (e.g., notify-ntfy) include companion scripts and must
> be installed as a folder. See each skill's README for details.
```

- [ ] **Step 2: Verify the full script runs without syntax errors**

Run: `python -c "import py_compile; py_compile.compile('notify-ntfy/ntfy-hook.py', doraise=True)"`
Expected: no output (success)

- [ ] **Step 3: Verify cancel handles missing marker gracefully**

Run: `python notify-ntfy/ntfy-hook.py cancel; echo "exit: $?"`
Expected: exit 0

- [ ] **Step 4: Verify test sends a notification (if network available)**

Run: `python notify-ntfy/ntfy-hook.py test`
Expected: `OK: test notification sent` or a network error (no crash)

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "Add notify-ntfy to repo skills list"
```
