from sqlalchemy import inspect, text

from app import db


def ensure_schema():
    """Add new columns on existing PostgreSQL databases."""
    inspector = inspect(db.engine)
    if "products" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("products")}
        stmts = []
        if "slug" not in cols:
            stmts.append("ALTER TABLE products ADD COLUMN slug VARCHAR(80)")
        if "product_kind" not in cols:
            stmts.append(
                "ALTER TABLE products ADD COLUMN product_kind VARCHAR(20) DEFAULT 'flavor'"
            )
        if "box_size" not in cols:
            stmts.append("ALTER TABLE products ADD COLUMN box_size INTEGER")
        for stmt in stmts:
            with db.engine.begin() as conn:
                conn.execute(text(stmt))

    if "order_items" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("order_items")}
        stmts = []
        if "line_type" not in cols:
            stmts.append(
                "ALTER TABLE order_items ADD COLUMN line_type VARCHAR(20) DEFAULT 'flavor'"
            )
        if "box_contents" not in cols:
            stmts.append("ALTER TABLE order_items ADD COLUMN box_contents TEXT")
        for stmt in stmts:
            with db.engine.begin() as conn:
                conn.execute(text(stmt))
