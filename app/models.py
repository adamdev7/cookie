import json
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    KIND_FLAVOR = "flavor"
    KIND_BOX = "box"

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    product_kind = db.Column(db.String(20), default=KIND_FLAVOR, nullable=False)
    box_size = db.Column(db.Integer, nullable=True)

    order_items = db.relationship("OrderItem", back_populates="product")

    @property
    def price_float(self) -> float:
        return float(self.price)

    @property
    def is_flavor(self) -> bool:
        return self.product_kind == self.KIND_FLAVOR

    @property
    def is_box(self) -> bool:
        return self.product_kind == self.KIND_BOX


class Order(db.Model):
    __tablename__ = "orders"

    STATUS_NEW = "new"
    STATUS_PREPARING = "preparing"
    STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUSES = [
        STATUS_NEW,
        STATUS_PREPARING,
        STATUS_OUT_FOR_DELIVERY,
        STATUS_COMPLETED,
        STATUS_CANCELLED,
    ]

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.Text, nullable=True)
    delivery_type = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), default=STATUS_NEW, nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    items = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    @property
    def total_float(self) -> float:
        return float(self.total_price)

    @property
    def status_label(self) -> str:
        labels = {
            self.STATUS_NEW: "New",
            self.STATUS_PREPARING: "Preparing",
            self.STATUS_OUT_FOR_DELIVERY: "Out for Delivery",
            self.STATUS_COMPLETED: "Completed",
            self.STATUS_CANCELLED: "Cancelled",
        }
        return labels.get(self.status, self.status)


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    line_type = db.Column(db.String(20), default="flavor", nullable=False)
    box_contents = db.Column(db.Text, nullable=True)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")

    @property
    def line_total(self) -> float:
        return float(self.price) * self.quantity

    def box_mix_dict(self) -> dict:
        if not self.box_contents:
            return {}
        try:
            data = json.loads(self.box_contents)
            return {int(k): int(v) for k, v in data.get("mix", {}).items()}
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}

    def box_mix_label(self, flavor_map: dict | None = None) -> str:
        mix = self.box_mix_dict()
        if not mix:
            return ""
        parts = []
        for pid, qty in mix.items():
            name = flavor_map.get(pid, f"#{pid}") if flavor_map else f"#{pid}"
            parts.append(f"{name}×{qty}")
        return ", ".join(parts)
