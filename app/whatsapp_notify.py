"""WhatsApp order alerts via CallMeBot (simple free API for personal alerts)."""
from __future__ import annotations

import requests
from flask import current_app

from app.models import Order
from app.telegram_bot import format_order_message


def _plain_order_message(order: Order) -> str:
    """Strip HTML tags from Telegram formatter for WhatsApp plain text."""
    html = format_order_message(order)
    return (
        html.replace("<b>", "")
        .replace("</b>", "")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
    )


def send_whatsapp_notification(order: Order) -> bool:
    if not current_app.config.get("WHATSAPP_ENABLED"):
        return False

    phone = str(current_app.config.get("WHATSAPP_PHONE") or "").strip()
    api_key = str(current_app.config.get("WHATSAPP_API_KEY") or "").strip()
    if not phone or not api_key:
        current_app.logger.warning("WhatsApp not fully configured; skipping.")
        return False

    # Digits only, keep leading country code (CallMeBot wants e.g. 15145944092)
    digits = "".join(ch for ch in phone if ch.isdigit())
    text = _plain_order_message(order)
    # Use params= so requests encodes safely (avoids CallMeBot PHP $var bugs)
    try:
        resp = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": digits, "text": text, "apikey": api_key},
            timeout=15,
        )
        if resp.status_code >= 400:
            current_app.logger.error("WhatsApp send failed: %s %s", resp.status_code, resp.text[:200])
            return False
        return True
    except requests.RequestException as exc:
        current_app.logger.error("WhatsApp send failed: %s", exc)
        return False


def send_whatsapp_test(message: str = "Test — notifications commandes OK ✅") -> tuple[bool, str]:
    phone = str(current_app.config.get("WHATSAPP_PHONE") or "").strip()
    api_key = str(current_app.config.get("WHATSAPP_API_KEY") or "").strip()
    if not phone or not api_key:
        return False, "Numéro WhatsApp ou clé API manquant."

    digits = "".join(ch for ch in phone if ch.isdigit())
    try:
        resp = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": digits, "text": message, "apikey": api_key},
            timeout=15,
        )
        if resp.status_code >= 400:
            return False, f"Erreur CallMeBot ({resp.status_code}): {resp.text[:180]}"
        return True, "Message WhatsApp de test envoyé."
    except requests.RequestException as exc:
        return False, str(exc)
