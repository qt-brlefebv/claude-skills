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
