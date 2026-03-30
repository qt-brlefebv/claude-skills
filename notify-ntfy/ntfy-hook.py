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
        "topic": f"{getpass.getuser()}_claude_{platform.node().split('.')[0]}",
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

    hostname = platform.node().split(".")[0]
    project = os.path.basename(os.getcwd())
    title = f"Claude Code [{hostname} :: {project}]"
    body = f"Waiting for: {tool_name}" if tool_name else "Waiting for: your response"

    send_notification(config, title, body)


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


def cmd_test():
    config = ensure_config()
    hostname = platform.node().split(".")[0]
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
    if command == "notify":
        cmd_notify()
    elif command == "cancel":
        cmd_cancel()
    elif command == "test":
        cmd_test()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
