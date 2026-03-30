# notify-ntfy Skill Design

## Overview

A self-contained Claude Code skill that sends push notifications via [ntfy.sh](https://ntfy.sh) when Claude is waiting for user input. Includes a guided setup wizard, runtime configuration, and an interruptible timer so notifications only fire after a configurable delay.

## Problem

When Claude Code finishes work and needs user input, there's no way to know without watching the terminal. This skill sends a phone notification after a delay, so you can context-switch safely.

## Approach

**Approach C: Wrapper script does everything.** A single bundled Python script (`ntfy-hook.py`) handles timer logic, notification sending, and config management. The hooks in `settings.json` are write-once and never need rewriting — all behavior is controlled by a config file the script reads at runtime.

## Skill Structure

```
notify-ntfy/
  notify-ntfy.md     — skill file (subcommand dispatch, setup wizard, config UI)
  ntfy-hook.py       — bundled Python script (timer, sending, config I/O)
  README.md          — usage and installation docs
```

**Installed location:** `~/.claude/skills/notify-ntfy/`

**Config location:** `~/.claude/skills/notify-ntfy/ntfy-config.json`

## Skill Frontmatter

```yaml
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
```

Arguments are received via `{{ args }}` and parsed as the subcommand + parameters (e.g., `setup`, `test`, `config timer 60`, `enable`, `disable`, `status`).

## Hook Integration

Two hooks are written to the **user-level** `~/.claude/settings.json` during setup. The skill must read the existing file, merge the new hooks into any existing `Notification` and `UserPromptSubmit` arrays (or create them), and avoid duplicating hooks on repeated setup runs. Detection of already-installed hooks: check if any existing hook command contains `ntfy-hook.py`.

### Notification hook (async)

```json
{
  "Notification": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "python <ABSOLUTE_SKILLS_PATH>/notify-ntfy/ntfy-hook.py notify",
          "async": true
        }
      ]
    }
  ]
}
```

- Fires on Claude Code's `Notification` event.
- The script reads **stdin** to extract context from the hook JSON payload (see "Hook stdin payload" below).
- `<ABSOLUTE_SKILLS_PATH>` is the fully expanded path (e.g., `C:/Users/brlefebv/.claude/skills`) — **not** `~`, which does not expand reliably on Windows outside of bash.

### UserPromptSubmit hook (sync)

```json
{
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "python <ABSOLUTE_SKILLS_PATH>/notify-ntfy/ntfy-hook.py cancel"
        }
      ]
    }
  ]
}
```

- Fires when the user submits a prompt.
- Removes the pending marker file(s), causing any sleeping notify process to no-op.

### Hook stdin payload

Claude Code hooks receive context as a JSON object on stdin. The `Notification` hook payload includes the tool name or notification reason. The script should:

1. Try to read stdin (non-blocking / with timeout).
2. Parse as JSON.
3. Extract the tool or action name from the payload if available.
4. Fall back to `"your response"` if stdin is empty or unparseable.

The exact JSON schema should be verified during implementation by logging the stdin payload from a test hook.

## ntfy-hook.py Behavior

### `notify` subcommand

1. Read `ntfy-config.json` — if missing or `enabled: false`, exit immediately.
2. Read stdin for hook context JSON; extract tool/action name if available.
3. Clean up any stale marker files (age > 2x `timer_seconds`).
4. Write a pending marker file with the current PID and timestamp.
5. `time.sleep(timer_seconds)`.
6. Check if marker still exists and contains this process's PID — if gone or PID mismatch, exit silently.
7. Remove marker, build notification:
   - **Title:** `Claude Code [<HOSTNAME> :: <project_folder>]`
   - **Body:** `Waiting for: <tool_name>` (or `Waiting for: your response` if no tool name)
   - `project_folder` = basename of CWD at invocation time.
8. POST to `https://<server>/<topic>` with title as HTTP header. Use a 10-second timeout on the request. Catch `URLError`/`HTTPError` and exit gracefully (print to stderr for debugging, but don't block).

### `cancel` subcommand

1. Remove all marker files matching the session pattern in the temp directory.
2. Exit.

### `test` subcommand

1. Read config, send a test notification immediately (no timer).
2. Print success/failure to stdout.
3. Exit.

### Notification HTTP request

```
POST https://<server>/<topic>
Content-Type: text/plain
Title: Claude Code [<HOSTNAME> :: <project_folder>]

Waiting for: Edit
```

Uses only `urllib.request` (stdlib) — no external dependencies. 10-second timeout.

## Config File

`~/.claude/skills/notify-ntfy/ntfy-config.json`:

```json
{
  "topic": "<USERNAME>_claude_<HOSTNAME>",
  "timer_seconds": 30,
  "server": "https://ntfy.sh",
  "enabled": true
}
```

- **topic:** Defaults to `<USERNAME>_claude_<HOSTNAME>` — unique per machine, allows subscribing per-machine or to all.
- **timer_seconds:** Delay before notification fires. User prompt within this window cancels it.
- **server:** ntfy server URL. Defaults to public `ntfy.sh`.
- **enabled:** Toggle without removing hooks.

Generated on first run or by `/ntfy setup`. The script resolves `<USERNAME>` via `getpass.getuser()` (robust across platforms) and `<HOSTNAME>` via `platform.node()`.

## Skill Subcommands

Invoked as `/ntfy <subcommand>` (skill name `notify-ntfy`, alias `ntfy`).

User args: `{{ args }}`

### `/ntfy setup`

First-time guided setup:

1. **Verify installation** — check `ntfy-hook.py` exists alongside the skill `.md`. If not, error with install instructions (copy `notify-ntfy/` folder to `~/.claude/skills/`).
2. **Generate config** — create `ntfy-config.json` with defaults (`<USERNAME>_claude_<HOSTNAME>`, 30s timer). If config already exists, show current values and ask if user wants to regenerate.
3. **Guide phone subscription** — display the topic name and instruct the user to:
   - Install the ntfy app (Android/iOS)
   - Subscribe to the displayed topic
4. **Write hooks** — read `~/.claude/settings.json`, check for existing ntfy hooks (search for `ntfy-hook.py` in hook commands). If found, report they're already installed. If not, merge new hooks into existing structure and write back.
5. **Test** — send a test notification, ask user to confirm receipt.
6. **Report success.**

### `/ntfy test`

Send a test notification immediately. Runs `python <path>/ntfy-hook.py test` and reports result.

### `/ntfy config [key] [value]`

Update a config value. Supported keys:
- `timer <seconds>` — e.g., `/ntfy config timer 60`
- `topic <name>` — e.g., `/ntfy config topic my_custom_topic`
- `server <url>` — e.g., `/ntfy config server https://my.ntfy.server`

With no args, displays current config (intentionally aliases `/ntfy status`).

### `/ntfy status`

Display current config values and whether hooks are present in `settings.json`.

### `/ntfy enable` / `/ntfy disable`

Toggle the `enabled` flag in config. Confirms with "Notifications enabled" / "Notifications paused".

## Pending Marker

The marker file signals whether a notification is pending.

**Location:** `<tempdir>/claude-ntfy-<PPID>.pending` where `<PPID>` is the parent process ID (the Claude Code session). This discriminates markers per-session so multiple concurrent sessions don't interfere with each other.

**Contents:** JSON with `pid` (of the notify process) and `timestamp` (Unix epoch).

**Stale detection:** On `notify`, before writing a new marker, scan for `claude-ntfy-*.pending` files older than 2x `timer_seconds` and remove them. This handles markers left by killed processes or system reboots.

**Cancel behavior:** The `cancel` subcommand removes all `claude-ntfy-*.pending` files for the current session's PPID. If PPID is not deterministic (e.g., hook runner varies), fall back to removing all `claude-ntfy-*.pending` files — this is acceptable since a user prompt in any session means the user is present.

## Platform Considerations

- **Windows (MSYS2/Git Bash):** `python` command must be available on PATH. Hook commands use absolute paths with forward slashes (e.g., `C:/Users/brlefebv/.claude/skills/notify-ntfy/ntfy-hook.py`). Do NOT use `~` in hook commands — it does not expand reliably outside bash on Windows.
- **macOS/Linux:** Works as-is. `~` could work in hook commands but absolute paths are used for consistency.
- **Temp directory:** Use `tempfile.gettempdir()` for marker files (cross-platform).
- **Username resolution:** Use `getpass.getuser()` which works across platforms including non-login contexts.

## Installation

Per the repo pattern, users install by copying the `notify-ntfy/` folder:

```bash
cp -r notify-ntfy/ ~/.claude/skills/notify-ntfy/
```

Then run `/ntfy setup` in Claude Code.

## What This Replaces

The current manual setup in `settings.json`:
- Hardcoded topic (`nadnerb97_cc_qtpad`)
- Generic message ("Claude Code needs you!")
- Bash-based timer (`touch + sleep + test -f` chain)
- No config management, no enable/disable, no status

The new skill provides all of this through a guided experience with richer notifications.
