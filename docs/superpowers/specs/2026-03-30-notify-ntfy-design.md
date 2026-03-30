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

## Hook Integration

Two hooks are written to `settings.json` during setup:

### Notification hook (async)

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python ~/.claude/skills/notify-ntfy/ntfy-hook.py notify \"$HOOK_TOOL_NAME\"",
      "async": true
    }
  ]
}
```

- Fires on Claude Code's `Notification` event.
- `$HOOK_TOOL_NAME` is passed if available in the hook environment; otherwise falls back to a generic message.
- The Python process sleeps for `timer_seconds`, then sends if not cancelled.

### UserPromptSubmit hook (sync)

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python ~/.claude/skills/notify-ntfy/ntfy-hook.py cancel"
    }
  ]
}
```

- Fires when the user submits a prompt.
- Removes the pending marker file, causing the sleeping notify process to no-op.

## ntfy-hook.py Behavior

### `notify <tool_name?>` subcommand

1. Read `ntfy-config.json` — if missing or `enabled: false`, exit immediately.
2. Write a pending marker file (with timestamp + PID to detect stale markers).
3. `time.sleep(timer_seconds)`.
4. Check if marker still exists — if removed, exit silently.
5. Remove marker, build notification:
   - **Title:** `Claude Code [<HOSTNAME> :: <project_folder>]`
   - **Body:** `Waiting for: <tool_name>` (or `Waiting for: your response` if no tool name)
   - `project_folder` = basename of CWD at invocation time.
6. POST to `https://<server>/<topic>` with title as HTTP header.

### `cancel` subcommand

1. Remove the pending marker file if it exists.
2. Exit.

### `test` subcommand

1. Read config, send a test notification immediately (no timer).
2. Exit with success/failure message.

### Notification HTTP request

```
POST https://<server>/<topic>
Content-Type: text/plain
Title: Claude Code [<HOSTNAME> :: <project_folder>]

Waiting for: Edit
```

Uses only `urllib.request` (stdlib) — no external dependencies.

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

Generated on first run or by `/ntfy setup`. The script fills `<USERNAME>` and `<HOSTNAME>` from `os.getlogin()` / `platform.node()` at generation time.

## Skill Subcommands

Invoked as `/ntfy <subcommand>` (skill name `notify-ntfy`, alias `ntfy`).

### `/ntfy setup`

First-time guided setup:

1. **Verify installation** — check `ntfy-hook.py` exists alongside the skill `.md`. If not, error with install instructions (copy `notify-ntfy/` folder to `~/.claude/skills/`).
2. **Generate config** — create `ntfy-config.json` with defaults (`<USERNAME>_claude_<HOSTNAME>`, 30s timer).
3. **Guide phone subscription** — display the topic name and instruct the user to:
   - Install the ntfy app (Android/iOS)
   - Subscribe to the displayed topic
4. **Write hooks** — add the Notification and UserPromptSubmit hooks to `settings.json`.
5. **Test** — send a test notification, ask user to confirm receipt.
6. **Report success.**

### `/ntfy test`

Send a test notification immediately. Runs `python ntfy-hook.py test` and reports result.

### `/ntfy config [key] [value]`

Update a config value. Supported keys:
- `timer <seconds>` — e.g., `/ntfy config timer 60`
- `topic <name>` — e.g., `/ntfy config topic my_custom_topic`
- `server <url>` — e.g., `/ntfy config server https://my.ntfy.server`

With no args, displays current config (same as `/ntfy status`).

### `/ntfy status`

Display current config values and whether hooks are present in `settings.json`.

### `/ntfy enable` / `/ntfy disable`

Toggle the `enabled` flag in config. Confirms with "Notifications enabled" / "Notifications paused".

## Pending Marker

The marker file signals whether a notification is pending. Location: system temp directory (e.g., `/tmp/claude-ntfy-pending` or OS-appropriate equivalent via `tempfile`).

Contents: JSON with `pid` and `timestamp` for stale detection. The `cancel` subcommand unconditionally removes it. The `notify` subcommand checks for it after sleeping — if gone, another process cancelled it.

## Platform Considerations

- **Windows (MSYS2/Git Bash):** `python` command must be available on PATH. Paths use forward slashes in hook commands. `~` expands in bash hooks. `platform.node()` returns Windows hostname.
- **macOS/Linux:** Works as-is.
- **Temp directory:** Use `tempfile.gettempdir()` for the marker file to be cross-platform.

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
