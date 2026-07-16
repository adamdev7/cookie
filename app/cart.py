import json
import uuid
from decimal import Decimal

from flask import session

from app.models import Product


def _empty_cart() -> dict:
    return {"flavors": {}, "boxes": []}


def get_cart() -> dict:
    raw = session.get("cart")
    if not raw:
        return _empty_cart()
    if isinstance(raw, dict) and "flavors" in raw:
        return raw
    # Legacy: {product_id: qty}
    flavors = {}
    if isinstance(raw, dict):
        for key, qty in raw.items():
            try:
                flavors[str(int(key))] = int(qty)
            except (TypeError, ValueError):
                continue
    cart = _empty_cart()
    cart["flavors"] = flavors
    session["cart"] = cart
    session.modified = True
    return cart


def save_cart(cart: dict) -> None:
    session["cart"] = cart
    session.modified = True


def _flavor_products():
    return {
        p.id: p
        for p in Product.query.filter_by(
            is_active=True, product_kind=Product.KIND_FLAVOR
        ).all()
    }


def add_flavor(product_id: int, qty: int) -> None:
    cart = get_cart()
    key = str(product_id)
    cart["flavors"][key] = cart["flavors"].get(key, 0) + max(1, qty)
    save_cart(cart)


def set_flavor_qty(product_id: int, qty: int) -> None:
    cart = get_cart()
    key = str(product_id)
    if qty <= 0:
        cart["flavors"].pop(key, None)
    else:
        cart["flavors"][key] = qty
    save_cart(cart)


def remove_flavor(product_id: int) -> None:
    cart = get_cart()
    cart["flavors"].pop(str(product_id), None)
    save_cart(cart)


def add_box(box_size: int, mix: dict, box_product_id: int, price: float) -> str:
    cart = get_cart()
    key = uuid.uuid4().hex[:10]
    cart["boxes"].append(
        {
            "key": key,
            "size": box_size,
            "mix": {str(k): int(v) for k, v in mix.items()},
            "box_product_id": box_product_id,
            "price": float(price),
        }
    )
    save_cart(cart)
    return key


def remove_box(box_key: str) -> None:
    cart = get_cart()
    cart["boxes"] = [b for b in cart["boxes"] if b.get("key") != box_key]
    save_cart(cart)


def cart_is_empty(cart: dict | None = None) -> bool:
    cart = cart or get_cart()
    return not cart.get("flavors") and not cart.get("boxes")


def build_cart_lines():
    """Return display lines and subtotal for templates/checkout."""
    cart = get_cart()
    flavors_db = _flavor_products()
    lines = []
    subtotal = Decimal("0")

    for pid_str, qty in cart.get("flavors", {}).items():
        pid = int(pid_str)
        product = flavors_db.get(pid)
        if not product:
            continue
        line_total = Decimal(str(product.price_float * qty))
        subtotal += line_total
        lines.append(
            {
                "type": "flavor",
                "key": pid_str,
                "product": product,
                "quantity": qty,
                "line_total": float(line_total),
                "label": product.name,
            }
        )

    for box in cart.get("boxes", []):
        box_product = flavors_db.get(box.get("box_product_id"))  # wrong - need Product.get
        from app import db

        box_prod = db.session.get(Product, box.get("box_product_id"))
        if not box_prod:
            continue
        price = Decimal(str(box.get("price", box_prod.price_float)))
        subtotal += price
        mix_parts = []
        for fid_str, fq in box.get("mix", {}).items():
            fp = flavors_db.get(int(fid_str))
            if fp:
                mix_parts.append(f"{fp.name}×{fq}")
        lines.append(
            {
                "type": "box",
                "key": box["key"],
                "product": box_prod,
                "quantity": 1,
                "line_total": float(price),
                "label": f"{box_prod.name}",
                "box_size": box["size"],
                "mix": box.get("mix", {}),
                "mix_label": ", ".join(mix_parts),
            }
        )

    return lines, float(subtotal)


def cart_lines_for_order():
    """Flatten cart into order rows: flavors + one row per box."""
    cart = get_cart()
    flavors_db = _flavor_products()
    rows = []

    for pid_str, qty in cart.get("flavors", {}).items():
        product = flavors_db.get(int(pid_str))
        if product and qty > 0:
            rows.append(
                {
                    "product": product,
                    "quantity": qty,
                    "line_type": "flavor",
                    "box_contents": None,
                    "unit_price": product.price,
                }
            )

    from app import db

    for box in cart.get("boxes", []):
        box_prod = db.session.get(Product, box.get("box_product_id"))
        if not box_prod:
            continue
        rows.append(
            {
                "product": box_prod,
                "quantity": 1,
                "line_type": "box",
                "box_contents": json.dumps(
                    {"size": box["size"], "mix": box.get("mix", {})}
                ),
                "unit_price": Decimal(str(box.get("price", box_prod.price_float))),
            }
        )
    return rows
