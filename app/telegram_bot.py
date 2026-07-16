import requests
from flask import current_app

from app.models import Order


STATUS_BUTTONS = [
    ("preparing", "✅ Accept Order"),
    ("preparing", "🍪 Preparing"),
    ("out_for_delivery", "🚚 Out for Delivery"),
    ("completed", "✔ Completed"),
    ("cancelled", "❌ Cancel"),
]


def format_order_message(order: Order) -> str:
    lines = [
        f"🍪 <b>NEW ORDER #{order.id}</b>",
        "",
        f"<b>Customer:</b> {order.customer_name}",
        f"<b>Phone:</b> {order.phone}",
        f"<b>Email:</b> {order.email}",
        f"<b>Type:</b> {order.delivery_type.upper()}",
    ]
    if order.delivery_type == "delivery" and order.address:
        lines.append(f"<b>Address:</b> {order.address}")
    lines.extend(
        [
            f"<b>Payment:</b> {_payment_label(order.payment_method)}",
            "",
            "<b>Items:</b>",
        ]
    )
    from app.models import Product

    flavor_map = {
        p.id: p.name for p in Product.query.filter_by(product_kind=Product.KIND_FLAVOR).all()
    }
    for item in order.items:
        name = item.product.name if item.product else f"Product #{item.product_id}"
        if item.line_type == "box" and item.box_contents:
            mix = item.box_mix_label(flavor_map)
            lines.append(f"  • {name} — ${item.line_total:.2f}")
            if mix:
                lines.append(f"      ↳ {mix}")
        else:
            lines.append(f"  • {name} x{item.quantity} — ${item.line_total:.2f}")
    lines.extend(["", f"<b>Total: ${order.total_float:.2f}</b>", f"<b>Status:</b> {order.status_label}"])
    return "\n".join(lines)


def _payment_label(method: str) -> str:
    return "Cash" if method == "cash" else "Interac e-Transfer"


def build_inline_keyboard(order_id: int) -> dict:
    rows = [
        [{"text": label, "callback_data": f"order:{order_id}:{status}"}]
        for status, label in STATUS_BUTTONS
    ]
    return {"inline_keyboard": rows}


def send_order_notification(order: Order) -> bool:
    token = current_app.config.get("TELEGRAM_BOT_TOKEN")
    chat_id = current_app.config.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        current_app.logger.warning("Telegram not configured; skipping notification.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": format_order_message(order),
        "parse_mode": "HTML",
        "reply_markup": build_inline_keyboard(order.id),
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        current_app.logger.error("Telegram send failed: %s", exc)
        return False


def answer_callback(callback_id: str, text: str) -> None:
    token = current_app.config.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_id, "text": text}, timeout=10)


def edit_order_message(chat_id, message_id: int, order: Order) -> None:
    token = current_app.config.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": format_order_message(order),
        "parse_mode": "HTML",
        "reply_markup": build_inline_keyboard(order.id),
    }
    requests.post(url, json=payload, timeout=10)


def process_callback(data: dict) -> str | None:
    """Handle Telegram callback_query. Returns status message or None."""
    callback = data.get("callback_query")
    if not callback:
        return None

    callback_data = callback.get("data", "")
    if not callback_data.startswith("order:"):
        return None

    parts = callback_data.split(":")
    if len(parts) != 3:
        return None

    _, order_id_str, new_status = parts
    from app import db
    from app.models import Order as OrderModel

    order = db.session.get(OrderModel, int(order_id_str))
    if not order:
        answer_callback(callback["id"], "Order not found")
        return None

    if new_status not in OrderModel.STATUSES:
        answer_callback(callback["id"], "Invalid status")
        return None

    order.status = new_status
    db.session.commit()

    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    if chat_id and message_id:
        edit_order_message(chat_id, message_id, order)

    answer_callback(callback["id"], f"Order #{order.id} → {order.status_label}")
    return order.status_label
