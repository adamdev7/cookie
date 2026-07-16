"""Persist admin-editable notification settings (outside git)."""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, current_app

SETTINGS_KEYS = (
    "BUSINESS_NAME",
    "CONTACT_PHONE",
    "ETRANSFER_EMAIL",
    "MAIL_SERVER",
    "MAIL_PORT",
    "MAIL_USE_TLS",
    "MAIL_USERNAME",
    "MAIL_PASSWORD",
    "MAIL_DEFAULT_SENDER",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_WEBHOOK_SECRET",
    "WHATSAPP_ENABLED",
    "WHATSAPP_PHONE",
    "WHATSAPP_API_KEY",
)

SECRET_KEYS = {"MAIL_PASSWORD", "TELEGRAM_BOT_TOKEN", "WHATSAPP_API_KEY", "TELEGRAM_WEBHOOK_SECRET"}


def settings_path(app: Flask | None = None) -> Path:
    root = Path(app.root_path) if app else Path(current_app.root_path)
    # app.root_path is .../app → store next to project
    base = root.parent
    folder = base / "instance"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "settings.json"


def load_settings(app: Flask | None = None) -> dict:
    path = settings_path(app)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(data: dict, app: Flask | None = None) -> None:
    path = settings_path(app)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def apply_settings_to_app(app: Flask, data: dict | None = None) -> None:
    """Merge stored settings into Flask config (overrides .env for these keys)."""
    stored = data if data is not None else load_settings(app)
    for key in SETTINGS_KEYS:
        if key not in stored:
            continue
        value = stored[key]
        if key == "MAIL_PORT":
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = 587
        elif key == "MAIL_USE_TLS":
            value = str(value).lower() in {"1", "true", "yes", "on"}
        elif key == "WHATSAPP_ENABLED":
            value = str(value).lower() in {"1", "true", "yes", "on"}
        elif value is None:
            value = ""
        else:
            value = str(value)
        app.config[key] = value

    # Keep sender in sync when empty
    if not app.config.get("MAIL_DEFAULT_SENDER") and app.config.get("MAIL_USERNAME"):
        app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]


def notification_status(app: Flask | None = None) -> dict:
    cfg = (app or current_app).config
    mail_ok = bool(cfg.get("MAIL_USERNAME") and cfg.get("MAIL_PASSWORD"))
    telegram_ok = bool(cfg.get("TELEGRAM_BOT_TOKEN") and cfg.get("TELEGRAM_CHAT_ID"))
    whatsapp_ok = bool(
        cfg.get("WHATSAPP_ENABLED")
        and cfg.get("WHATSAPP_PHONE")
        and cfg.get("WHATSAPP_API_KEY")
    )
    return {
        "mail": mail_ok,
        "telegram": telegram_ok,
        "whatsapp": whatsapp_ok,
    }


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    text = str(value)
    if len(text) <= 4:
        return "••••"
    return "••••••••" + text[-4:]
