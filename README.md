# claude-skills

A collection of reusable Claude Code skills. Each skill lives in its own folder with a skill `.md` file and a README.

## Skills

- **[find-msvc](find-msvc/)** — Discover and activate MSVC/Visual Studio developer environments on Windows
- **[check-screenshot](check-screenshot/)** — View and describe the most recent screenshot(s)
- **[notify-ntfy](notify-ntfy/)** — Push notifications via ntfy.sh when Claude Code is waiting for input

## Installation

Skills can be installed at the **project level** (available only in that project) or the **user level** (available in all projects).

### Project-level

Copy the skill's `.md` file into your project's `.claude/skills/` directory:

```
cp check-screenshot/check-screenshot.md /path/to/my-project/.claude/skills/
```

### User-level

Copy the skill's `.md` file into your global `~/.claude/skills/` directory:

```
mkdir -p ~/.claude/skills
cp check-screenshot/check-screenshot.md ~/.claude/skills/
```

User-level skills are available across all projects without per-project setup.

> **Note:** Some skills (e.g., notify-ntfy) include companion scripts and must
> be installed as a folder. See each skill's README for details.

See each skill's README for additional configuration instructions.
