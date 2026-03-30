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
