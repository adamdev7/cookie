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
        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
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

    return render_template(
        "admin_dashboard.html",
        orders=orders,
        products=products,
        stats=stats,
        status_filter=status_filter,
        statuses=Order.STATUSES,
        flavor_map=flavor_map,
    )


def _compute_stats():
    completed_statuses = [Order.STATUS_COMPLETED]
    paid_orders = Order.query.filter(
        Order.status.in_(completed_statuses + [Order.STATUS_NEW, Order.STATUS_PREPARING, Order.STATUS_OUT_FOR_DELIVERY])
    ).filter(Order.status != Order.STATUS_CANCELLED)

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

    return {
        "total_orders": total_orders,
        "total_sales": float(total_sales or 0),
        "cash_sales": float(cash_total or 0),
        "etransfer_sales": float(etransfer_total or 0),
        "popular_cookie": popular[0] if popular else "—",
        "popular_qty": int(popular[1]) if popular else 0,
    }


@bp.route("/orders/<int:order_id>/status", methods=["POST"])
@login_required
def update_order_status(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    new_status = request.form.get("status")
    if new_status not in Order.STATUSES:
        flash("Invalid status.", "danger")
    else:
        order.status = new_status
        db.session.commit()
        flash(f"Order #{order.id} updated to {order.status_label}.", "success")
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
        flash("Invalid price.", "danger")
        return redirect(url_for("admin.dashboard") + "#products")

    if not name:
        flash("Product name is required.", "danger")
        return redirect(url_for("admin.dashboard") + "#products")

    product = Product(name=name, description=description, price=price, is_active=is_active)
    image_url = _save_upload(request.files.get("image"))
    if image_url:
        product.image_url = image_url

    db.session.add(product)
    db.session.commit()
    flash(f"Product '{name}' added.", "success")
    return redirect(url_for("admin.dashboard") + "#products")


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
        flash("Invalid price.", "danger")
        return redirect(url_for("admin.dashboard") + "#products")

    image_url = _save_upload(request.files.get("image"))
    if image_url:
        product.image_url = image_url

    db.session.commit()
    flash(f"Product '{product.name}' updated.", "success")
    return redirect(url_for("admin.dashboard") + "#products")


@bp.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)
    product.is_active = False
    db.session.commit()
    flash(f"Product '{product.name}' deactivated.", "info")
    return redirect(url_for("admin.dashboard") + "#products")


def _save_upload(file_storage) -> str | None:
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        flash("Invalid image type.", "danger")
        return None
    filename = secure_filename(file_storage.filename)
    base, ext = os.path.splitext(filename)
    unique = f"{base}_{os.urandom(4).hex()}{ext}"
    path = Path(current_app.config["UPLOAD_FOLDER"]) / unique
    file_storage.save(path)
    return f"images/uploads/{unique}"
