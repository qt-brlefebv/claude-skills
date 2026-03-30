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
