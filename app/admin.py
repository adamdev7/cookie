import os
from decimal import Decimal
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app import db
from app.models import Order, OrderItem, Product, User
from app.settings_store import (
    apply_settings_to_app,
    load_settings,
    mask_secret,
    notification_status,
    save_settings,
)

bp = Blueprint("admin", __name__)


def allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("admin.dashboard"))
        flash("Identifiant ou mot de passe invalide.", "danger")

    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Déconnecté.", "info")
    return redirect(url_for("admin.login"))


@bp.route("/")
@login_required
def dashboard():
    status_filter = request.args.get("status", "")
    query = Order.query.order_by(Order.created_at.desc())
    if status_filter and status_filter in Order.STATUSES:
        query = query.filter_by(status=status_filter)
    orders = query.limit(100).all()

    stats = _compute_stats()
    products = (
        Product.query.filter_by(product_kind=Product.KIND_FLAVOR)
        .order_by(Product.name)
        .all()
    )
    flavor_map = {
        p.id: p.name
        for p in Product.query.filter_by(product_kind=Product.KIND_FLAVOR).all()
    }
    notif = notification_status()
    webhook_url = request.url_root.rstrip("/") + url_for("public.telegram_webhook")

    return render_template(
        "admin_dashboard.html",
        orders=orders,
        products=products,
        stats=stats,
        status_filter=status_filter,
        statuses=Order.STATUSES,
        flavor_map=flavor_map,
        notif=notif,
        settings=current_app.config,
        secrets={
            "MAIL_PASSWORD": mask_secret(current_app.config.get("MAIL_PASSWORD")),
            "TELEGRAM_BOT_TOKEN": mask_secret(current_app.config.get("TELEGRAM_BOT_TOKEN")),
            "WHATSAPP_API_KEY": mask_secret(current_app.config.get("WHATSAPP_API_KEY")),
            "TELEGRAM_WEBHOOK_SECRET": mask_secret(
                current_app.config.get("TELEGRAM_WEBHOOK_SECRET")
            ),
        },
        webhook_url=webhook_url,
        active_tab=request.args.get("tab", "orders"),
    )


def _compute_stats():
    total_orders = Order.query.filter(Order.status != Order.STATUS_CANCELLED).count()
    total_sales = (
        db.session.query(func.coalesce(func.sum(Order.total_price), 0))
        .filter(Order.status != Order.STATUS_CANCELLED)
        .scalar()
    )

    popular = (
        db.session.query(
            Product.name,
            func.sum(OrderItem.quantity).label("qty"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status != Order.STATUS_CANCELLED)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .first()
    )

    cash_total = (
        db.session.query(func.coalesce(func.sum(Order.total_price), 0))
        .filter(Order.payment_method == "cash", Order.status != Order.STATUS_CANCELLED)
        .scalar()
    )
    etransfer_total = (
        db.session.query(func.coalesce(func.sum(Order.total_price), 0))
        .filter(Order.payment_method == "etransfer", Order.status != Order.STATUS_CANCELLED)
        .scalar()
    )
    new_count = Order.query.filter_by(status=Order.STATUS_NEW).count()

    return {
        "total_orders": total_orders,
        "total_sales": float(total_sales or 0),
        "cash_sales": float(cash_total or 0),
        "etransfer_sales": float(etransfer_total or 0),
        "popular_cookie": popular[0] if popular else "—",
        "popular_qty": int(popular[1]) if popular else 0,
        "new_orders": new_count,
    }


@bp.route("/settings", methods=["POST"])
@login_required
def save_notification_settings():
    stored = load_settings()

    def _get(name: str, default: str = "") -> str:
        return request.form.get(name, default).strip()

    # Business
    stored["BUSINESS_NAME"] = _get("BUSINESS_NAME") or current_app.config.get("BUSINESS_NAME", "")
    stored["CONTACT_PHONE"] = _get("CONTACT_PHONE") or current_app.config.get("CONTACT_PHONE", "")
    stored["ETRANSFER_EMAIL"] = _get("ETRANSFER_EMAIL") or current_app.config.get(
        "ETRANSFER_EMAIL", ""
    )

    # Gmail
    stored["MAIL_SERVER"] = _get("MAIL_SERVER") or "smtp.gmail.com"
    stored["MAIL_PORT"] = _get("MAIL_PORT") or "587"
    stored["MAIL_USE_TLS"] = "true" if request.form.get("MAIL_USE_TLS") == "on" else "false"
    stored["MAIL_USERNAME"] = _get("MAIL_USERNAME")
    stored["MAIL_DEFAULT_SENDER"] = _get("MAIL_DEFAULT_SENDER") or stored["MAIL_USERNAME"]
    mail_password = _get("MAIL_PASSWORD")
    if mail_password:
        stored["MAIL_PASSWORD"] = mail_password
    elif "MAIL_PASSWORD" not in stored:
        stored["MAIL_PASSWORD"] = current_app.config.get("MAIL_PASSWORD") or ""

    # Telegram
    tg_token = _get("TELEGRAM_BOT_TOKEN")
    if tg_token:
        stored["TELEGRAM_BOT_TOKEN"] = tg_token
    elif "TELEGRAM_BOT_TOKEN" not in stored:
        stored["TELEGRAM_BOT_TOKEN"] = current_app.config.get("TELEGRAM_BOT_TOKEN") or ""
    stored["TELEGRAM_CHAT_ID"] = _get("TELEGRAM_CHAT_ID")
    tg_secret = _get("TELEGRAM_WEBHOOK_SECRET")
    if tg_secret:
        stored["TELEGRAM_WEBHOOK_SECRET"] = tg_secret
    elif "TELEGRAM_WEBHOOK_SECRET" not in stored:
        stored["TELEGRAM_WEBHOOK_SECRET"] = current_app.config.get("TELEGRAM_WEBHOOK_SECRET") or ""

    # WhatsApp
    stored["WHATSAPP_ENABLED"] = "true" if request.form.get("WHATSAPP_ENABLED") == "on" else "false"
    stored["WHATSAPP_PHONE"] = _get("WHATSAPP_PHONE")
    wa_key = _get("WHATSAPP_API_KEY")
    if wa_key:
        stored["WHATSAPP_API_KEY"] = wa_key
    elif "WHATSAPP_API_KEY" not in stored:
        stored["WHATSAPP_API_KEY"] = current_app.config.get("WHATSAPP_API_KEY") or ""

    save_settings(stored)
    apply_settings_to_app(current_app, stored)
    flash("Paramètres enregistrés. Les nouvelles commandes utiliseront cette configuration.", "success")
    return redirect(url_for("admin.dashboard", tab="settings") + "#settings-tab")


@bp.route("/settings/test/email", methods=["POST"])
@login_required
def test_email():
    from app.email_service import send_test_email

    to_addr = request.form.get("test_email_to", "").strip() or current_app.config.get("MAIL_USERNAME")
    ok, message = send_test_email(to_addr)
    flash(message, "success" if ok else "danger")
    return redirect(url_for("admin.dashboard", tab="settings") + "#settings-tab")


@bp.route("/settings/test/telegram", methods=["POST"])
@login_required
def test_telegram():
    from app.telegram_bot import send_telegram_test

    ok, message = send_telegram_test()
    flash(message, "success" if ok else "danger")
    return redirect(url_for("admin.dashboard", tab="settings") + "#settings-tab")


@bp.route("/settings/test/whatsapp", methods=["POST"])
@login_required
def test_whatsapp():
    from app.whatsapp_notify import send_whatsapp_test

    ok, message = send_whatsapp_test()
    flash(message, "success" if ok else "danger")
    return redirect(url_for("admin.dashboard", tab="settings") + "#settings-tab")


@bp.route("/orders/<int:order_id>/status", methods=["POST"])
@login_required
def update_order_status(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    new_status = request.form.get("status")
    if new_status not in Order.STATUSES:
        flash("Statut invalide.", "danger")
    else:
        order.status = new_status
        db.session.commit()
        flash(f"Commande #{order.id} → {order.status_label}.", "success")
    return redirect(url_for("admin.dashboard", status=request.args.get("status", "")))


@bp.route("/products/add", methods=["POST"])
@login_required
def add_product():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    price_str = request.form.get("price", "0")
    is_active = request.form.get("is_active") == "on"

    try:
        price = Decimal(price_str)
    except Exception:
        flash("Prix invalide.", "danger")
        return redirect(url_for("admin.dashboard", tab="products") + "#products-tab")

    if not name:
        flash("Le nom du produit est requis.", "danger")
        return redirect(url_for("admin.dashboard", tab="products") + "#products-tab")

    product = Product(name=name, description=description, price=price, is_active=is_active)
    image_url = _save_upload(request.files.get("image"))
    if image_url:
        product.image_url = image_url

    db.session.add(product)
    db.session.commit()
    flash(f"Produit « {name} » ajouté.", "success")
    return redirect(url_for("admin.dashboard", tab="products") + "#products-tab")


@bp.route("/products/<int:product_id>/edit", methods=["POST"])
@login_required
def edit_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)

    product.name = request.form.get("name", product.name).strip()
    product.description = request.form.get("description", product.description)
    product.is_active = request.form.get("is_active") == "on"
    try:
        product.price = Decimal(request.form.get("price", product.price))
    except Exception:
        flash("Prix invalide.", "danger")
        return redirect(url_for("admin.dashboard", tab="products") + "#products-tab")

    image_url = _save_upload(request.files.get("image"))
    if image_url:
        product.image_url = image_url

    db.session.commit()
    flash(f"Produit « {product.name} » mis à jour.", "success")
    return redirect(url_for("admin.dashboard", tab="products") + "#products-tab")


@bp.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)
    product.is_active = False
    db.session.commit()
    flash(f"Produit « {product.name} » désactivé.", "info")
    return redirect(url_for("admin.dashboard", tab="products") + "#products-tab")


def _save_upload(file_storage) -> str | None:
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        flash("Type d'image invalide.", "danger")
        return None
    filename = secure_filename(file_storage.filename)
    base, ext = os.path.splitext(filename)
    unique = f"{base}_{os.urandom(4).hex()}{ext}"
    path = Path(current_app.config["UPLOAD_FOLDER"]) / unique
    file_storage.save(path)
    return f"images/uploads/{unique}"
