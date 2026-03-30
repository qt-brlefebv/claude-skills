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
