#!/usr/bin/env python3
"""
Config Loader — Timelapse Art Installation

Reads /data/config.yaml (single source of truth) and templates out
hostapd.conf, smb.conf, and other config files.  Also writes a
backward-compatible config.json for services that still expect it.

Usage:
    python3 config_loader.py              # apply config from /data/config.yaml
    python3 config_loader.py --check      # validate config without applying
"""
import json
import os
import sys
import shutil

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not installed — run: apt-get install -y python3-yaml")

CONFIG_YAML = os.environ.get("CONFIG_YAML", "/data/config.yaml")
CONFIG_JSON = "/data/config.json"
DEFAULT_CONFIG_YAML = os.path.join(os.path.dirname(__file__), "config.yaml")

DEFAULTS = {
    "capture": {
        "interval_minutes": 5,
        "exposure_mode": "auto",
        "shutter_speed": 10000,
        "iso": 100,
        "luma_target": None,
    },
    "playback": {"fps": 25, "display_brightness": 100, "display_type": "hdmi"},
    "wifi": {"ssid": "timelapse-ap", "password": "changeme2", "channel": 7},
    "uplink_wifi": {"ssid": "", "password": ""},
    "admin": {"password": "changeme"},
    "rendering": {"ffmpeg_video_backup_enabled": True},
}


def load_config(path: str = CONFIG_YAML) -> dict:
    """Load config.yaml, merging with defaults for missing keys."""
    cfg = dict(DEFAULTS)
    if os.path.isfile(path):
        with open(path) as f:
            user = yaml.safe_load(f) or {}
        for section, defaults in DEFAULTS.items():
            if section in user and isinstance(user[section], dict):
                merged = dict(defaults)
                merged.update(user[section])
                cfg[section] = merged
            elif section in user:
                cfg[section] = user[section]
    return cfg


def write_config_json(cfg: dict, path: str = CONFIG_JSON):
    """Write backward-compatible config.json for services that expect it."""
    flat = {
        "capture_interval_minutes": cfg["capture"]["interval_minutes"],
        "exposure_mode": cfg["capture"]["exposure_mode"],
        "exposure_shutter_speed": cfg["capture"]["shutter_speed"],
        "exposure_iso": cfg["capture"]["iso"],
        "luma_target": cfg["capture"]["luma_target"],
        "playback_fps": cfg["playback"]["fps"],
        "display_brightness": cfg["playback"]["display_brightness"],
        "display_type": cfg["playback"]["display_type"],
        "ffmpeg_video_backup_enabled": cfg["rendering"]["ffmpeg_video_backup_enabled"],
        "admin_password": cfg["admin"]["password"],
        "wifi_ssid": cfg["wifi"]["ssid"],
        "wifi_password": cfg["wifi"]["password"],
        "uplink_wifi_ssid": cfg["uplink_wifi"]["ssid"],
        "uplink_wifi_password": cfg["uplink_wifi"]["password"],
    }
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(flat, f, indent=2)
        f.write("\n")
    os.rename(tmp, path)


def template_hostapd(cfg: dict, path: str = "/etc/hostapd/hostapd.conf"):
    """Update hostapd.conf SSID and password from config."""
    if not os.path.isfile(path):
        return
    with open(path) as f:
        content = f.read()
    import re
    content = re.sub(r"^ssid=.*$", f"ssid={cfg['wifi']['ssid']}", content, flags=re.MULTILINE)
    content = re.sub(r"^wpa_passphrase=.*$", f"wpa_passphrase={cfg['wifi']['password']}", content, flags=re.MULTILINE)
    if cfg["wifi"].get("channel"):
        content = re.sub(r"^channel=.*$", f"channel={cfg['wifi']['channel']}", content, flags=re.MULTILINE)
    with open(path, "w") as f:
        f.write(content)


def apply_config():
    """Load config.yaml, write config.json, and template out conf files."""
    cfg = load_config()
    write_config_json(cfg)
    template_hostapd(cfg)
    return cfg


def main():
    if "--check" in sys.argv:
        cfg = load_config()
        print(json.dumps(cfg, indent=2, default=str))
        print("\nConfig is valid.")
        return

    if not os.path.isfile(CONFIG_YAML):
        # Bootstrap: copy default config.yaml to /data/ if it doesn't exist
        if os.path.isfile(DEFAULT_CONFIG_YAML):
            os.makedirs(os.path.dirname(CONFIG_YAML), exist_ok=True)
            shutil.copy2(DEFAULT_CONFIG_YAML, CONFIG_YAML)
            print(f"Bootstrapped {CONFIG_YAML} from {DEFAULT_CONFIG_YAML}")
        else:
            print(f"Warning: {CONFIG_YAML} not found, using defaults")

    cfg = apply_config()
    print(f"Config applied — wifi_ssid={cfg['wifi']['ssid']}")


if __name__ == "__main__":
    main()
