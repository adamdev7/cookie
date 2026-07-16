from sqlalchemy import text

from app import create_app, db
from app.models import Order, OrderItem

app = create_app()
with app.app_context():
    n_items = OrderItem.query.count()
    n_orders = Order.query.count()
    OrderItem.query.delete()
    Order.query.delete()
    db.session.commit()
    try:
        db.session.execute(text("ALTER SEQUENCE orders_id_seq RESTART WITH 1"))
        db.session.execute(text("ALTER SEQUENCE order_items_id_seq RESTART WITH 1"))
        db.session.commit()
        seq = "reset to 1"
    except Exception as exc:
        db.session.rollback()
        seq = f"skip ({exc})"
    print(f"Deleted {n_orders} orders and {n_items} line items.")
    print(f"Sequence: {seq}")
    print(f"Remaining orders: {Order.query.count()}")
