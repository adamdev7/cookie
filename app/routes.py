from decimal import Decimal

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app import db
from app.cart import (
    add_box,
    add_flavor,
    build_cart_lines,
    cart_is_empty,
    cart_lines_for_order,
    get_cart,
    remove_box,
    remove_flavor,
    save_cart,
    set_flavor_qty,
)
from app.catalog import get_active_flavors, get_box_product
from app.email_service import send_order_confirmation
from app.models import Order, OrderItem, Product
from app.telegram_bot import process_callback, send_order_notification

bp = Blueprint("public", __name__)


@bp.route("/")
def index():
    flavors = get_active_flavors()
    featured = flavors[:3]
    return render_template("index.html", featured=featured)


@bp.route("/products")
def products():
    flavors = get_active_flavors()
    return render_template("products.html", flavors=flavors)


@bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = db.session.get(Product, product_id)
    if not product or not product.is_active or not product.is_flavor:
        abort(404)
    return render_template("product_detail.html", product=product)


@bp.route("/box/<int:size>")
def box_builder(size):
    if size not in (6, 12):
        abort(404)
    box_product = get_box_product(size)
    if not box_product:
        abort(404)
    flavors = get_active_flavors()
    unit = current_app.config["COOKIE_UNIT_PRICE"]
    box_price = unit * size
    return render_template(
        "box_builder.html",
        box_size=size,
        box_product=box_product,
        flavors=flavors,
        box_price=box_price,
    )


@bp.route("/box/<int:size>/add", methods=["POST"])
def box_add(size):
    if size not in (6, 12):
        abort(404)
    box_product = get_box_product(size)
    if not box_product:
        abort(404)

    flavors = get_active_flavors()
    valid_ids = {f.id for f in flavors}
    mix = {}
    total = 0
    for flavor in flavors:
        qty = int(request.form.get(f"flavor_{flavor.id}", 0) or 0)
        if qty > 0:
            mix[flavor.id] = qty
            total += qty

    if total != size:
        flash(
            f"Veuillez choisir exactement {size} biscuits (vous en avez {total}).",
            "danger",
        )
        return redirect(url_for("public.box_builder", size=size))

    price = current_app.config["COOKIE_UNIT_PRICE"] * size
    add_box(size, mix, box_product.id, price)
    flash(f"Boîte de {size} ajoutée au panier.", "success")
    return redirect(url_for("public.cart"))


@bp.route("/cart/add/<int:product_id>", methods=["POST"])
def cart_add(product_id):
    product = db.session.get(Product, product_id)
    if not product or not product.is_active or not product.is_flavor:
        abort(404)
    qty = max(1, int(request.form.get("quantity", 1)))
    add_flavor(product.id, qty)
    flash(f"{product.name} ajouté au panier.", "success")
    next_url = request.form.get("next") or url_for("public.cart")
    # Only allow same-site relative redirects (quick-add stay on page)
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = url_for("public.cart")
    return redirect(next_url)


@bp.route("/cart/update", methods=["POST"])
def cart_update():
    cart = get_cart()
    for key in list(cart.get("flavors", {}).keys()):
        qty = int(request.form.get(f"qty_f_{key}", 0))
        set_flavor_qty(int(key), qty)
    save_cart(get_cart())
    return redirect(url_for("public.cart"))


@bp.route("/cart/remove/flavor/<int:product_id>", methods=["POST"])
def cart_remove_flavor(product_id):
    remove_flavor(product_id)
    flash("Article retiré.", "info")
    return redirect(url_for("public.cart"))


@bp.route("/cart/remove/box/<box_key>", methods=["POST"])
def cart_remove_box(box_key):
    remove_box(box_key)
    flash("Boîte retirée.", "info")
    return redirect(url_for("public.cart"))


@bp.route("/cart")
def cart():
    lines, subtotal = build_cart_lines()
    return render_template("cart.html", lines=lines, subtotal=subtotal)


@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    lines, subtotal = build_cart_lines()
    if not lines:
        flash("Votre panier est vide.", "warning")
        return redirect(url_for("public.products"))

    delivery_fee = float(current_app.config["DELIVERY_FEE"])

    if request.method == "POST":
        return _place_order(lines, subtotal, delivery_fee)

    return render_template(
        "checkout.html",
        lines=lines,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
    )


def _place_order(lines, subtotal, delivery_fee):
    name = request.form.get("customer_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    delivery_type = request.form.get("delivery_type", "pickup")
    address = request.form.get("address", "").strip()
    payment_method = request.form.get("payment_method", "cash")

    if not name or not email or not phone:
        flash("Veuillez remplir le nom, le courriel et le téléphone.", "danger")
        return redirect(url_for("public.checkout"))

    if delivery_type not in ("pickup", "delivery"):
        flash("Option de livraison invalide.", "danger")
        return redirect(url_for("public.checkout"))

    if delivery_type == "delivery" and not address:
        flash("L'adresse est requise pour la livraison.", "danger")
        return redirect(url_for("public.checkout"))

    if payment_method not in ("cash", "etransfer"):
        flash("Mode de paiement invalide.", "danger")
        return redirect(url_for("public.checkout"))

    total = subtotal
    if delivery_type == "delivery":
        total += delivery_fee

    order = Order(
        customer_name=name,
        email=email,
        phone=phone,
        address=address if delivery_type == "delivery" else None,
        delivery_type=delivery_type,
        payment_method=payment_method,
        status=Order.STATUS_NEW,
        total_price=Decimal(str(round(total, 2))),
    )
    db.session.add(order)
    db.session.flush()

    for row in cart_lines_for_order():
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=row["product"].id,
                quantity=row["quantity"],
                price=row["unit_price"],
                line_type=row["line_type"],
                box_contents=row["box_contents"],
            )
        )

    db.session.commit()

    session.pop("cart", None)
    session.modified = True

    send_order_notification(order)
    try:
        from app.whatsapp_notify import send_whatsapp_notification

        send_whatsapp_notification(order)
    except Exception as exc:
        current_app.logger.error("WhatsApp notification error: %s", exc)
    send_order_confirmation(order)

    return render_template("order_confirmation.html", order=order)


@bp.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    secret = current_app.config.get("TELEGRAM_WEBHOOK_SECRET")
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        abort(403)

    data = request.get_json(silent=True) or {}
    process_callback(data)
    return "", 200
