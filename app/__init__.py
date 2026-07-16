import os
from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

from app.config import Config

db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
login_manager.login_view = "admin.login"
login_manager.login_message_category = "info"


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent.parent / "templates"),
        static_folder=str(Path(__file__).resolve().parent.parent / "static"),
    )
    app.config.from_object(config_class)

    from app.settings_store import apply_settings_to_app

    apply_settings_to_app(app)

    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes import bp as public_bp
    from app.admin import bp as admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.context_processor
    def inject_globals():
        from app.cart import cart_item_count

        unit = app.config["COOKIE_UNIT_PRICE"]
        try:
            count = cart_item_count()
        except Exception:
            count = 0
        return {
            "config": app.config,
            "cookie_unit_price": unit,
            "box_6_price": unit * 6,
            "box_12_price": unit * 12,
            "cart_count": count,
        }

    with app.app_context():
        db.create_all()
        try:
            from app.db_migrate import ensure_schema

            ensure_schema()
        except Exception as exc:
            app.logger.warning("Schema migration skipped: %s", exc)
        try:
            from app.catalog import sync_catalog

            sync_catalog(app.config["COOKIE_UNIT_PRICE"])
        except Exception as exc:
            app.logger.warning("Catalog sync skipped: %s", exc)
        _seed_admin_if_needed(app)

    return app


def _seed_admin_if_needed(app):
    """Create default admin from env if no users exist."""
    from app.models import User

    if User.query.first():
        return

    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "admin123")
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    app.logger.warning(
        "Default admin created (%s). Change password immediately.", username
    )
