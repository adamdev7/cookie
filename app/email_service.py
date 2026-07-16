from flask import current_app, render_template_string
from flask_mail import Message

from app import mail
from app.models import Order, Product


def send_order_confirmation(order: Order) -> bool:
    """Send confirmation email with payment instructions."""
    if not current_app.config.get("MAIL_USERNAME"):
        current_app.logger.warning("Mail not configured; skipping confirmation email.")
        return False

    payment_block = _payment_instructions(order)
    flavor_map = {
        p.id: p.name
        for p in Product.query.filter_by(product_kind=Product.KIND_FLAVOR).all()
    }
    body = render_template_string(
        EMAIL_TEMPLATE,
        business_name=current_app.config["BUSINESS_NAME"],
        order=order,
        payment_block=payment_block,
        contact_phone=current_app.config["CONTACT_PHONE"],
        flavor_map=flavor_map,
    )

    msg = Message(
        subject=f"Order #{order.id} confirmed — {current_app.config['BUSINESS_NAME']}",
        recipients=[order.email],
        html=body,
    )

    try:
        mail.send(msg)
        return True
    except Exception as exc:
        current_app.logger.error("Failed to send email: %s", exc)
        return False


def _payment_instructions(order: Order) -> str:
    if order.payment_method == "etransfer":
        email = current_app.config["ETRANSFER_EMAIL"]
        return f"""
        <p><strong>Interac e-Transfer</strong></p>
        <p>Please send <strong>${order.total_float:.2f}</strong> to:</p>
        <p><a href="mailto:{email}">{email}</a></p>
        <p>Include <strong>Order #{order.id}</strong> in the message field.</p>
        """
    return """
    <p><strong>Cash payment</strong></p>
    <p>Please have exact change ready. Payment is due at pickup or upon delivery.</p>
    """


EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
  <h2 style="color: #8B4513;">Thank you, {{ order.customer_name }}!</h2>
  <p>Your order <strong>#{{ order.id }}</strong> at {{ business_name }} has been received.</p>

  <h3>Order summary</h3>
  <table style="width:100%; border-collapse: collapse;">
    <tr style="background:#f5f0eb;">
      <th style="text-align:left; padding:8px;">Item</th>
      <th style="padding:8px;">Qty</th>
      <th style="text-align:right; padding:8px;">Price</th>
    </tr>
    {% for item in order.items %}
    <tr>
      <td style="padding:8px; border-bottom:1px solid #eee;">
        {{ item.product.name }}
        {% if item.line_type == 'box' %}
        <br><small style="color:#888;">{{ item.box_mix_label(flavor_map) }}</small>
        {% endif %}
      </td>
      <td style="padding:8px; border-bottom:1px solid #eee; text-align:center;">{{ item.quantity }}</td>
      <td style="padding:8px; border-bottom:1px solid #eee; text-align:right;">${{ "%.2f"|format(item.line_total) }}</td>
    </tr>
    {% endfor %}
    <tr>
      <td colspan="2" style="padding:8px; text-align:right;"><strong>Total</strong></td>
      <td style="padding:8px; text-align:right;"><strong>${{ "%.2f"|format(order.total_float) }}</strong></td>
    </tr>
  </table>

  <p><strong>Delivery:</strong> {{ order.delivery_type|capitalize }}
  {% if order.delivery_type == 'delivery' and order.address %}
  <br>{{ order.address }}
  {% endif %}
  </p>
  <p><strong>Payment:</strong> {{ order.payment_method|replace('etransfer', 'Interac e-Transfer')|capitalize }}</p>

  <div style="background:#fff8f0; padding:16px; border-radius:8px; margin:16px 0;">
    {{ payment_block|safe }}
  </div>

  <p>Questions? Call us at {{ contact_phone }}.</p>
  <p style="color:#888; font-size:12px;">{{ business_name }}</p>
</body>
</html>
"""
