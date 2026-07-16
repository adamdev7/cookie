import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)


def _env(key: str, default: str = "") -> str:
    value = os.environ.get(key, default)
    if value and len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


class Config:
    SECRET_KEY = _env("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = _env(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/cookie_orders",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = BASE_DIR / "static" / "images" / "uploads"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # Mail
    MAIL_SERVER = _env("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(_env("MAIL_PORT", "587"))
    MAIL_USE_TLS = _env("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = _env("MAIL_USERNAME", "")
    MAIL_PASSWORD = _env("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = _env("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # Business
    BUSINESS_NAME = _env("BUSINESS_NAME", "Biscuits faits avec amour")
    ETRANSFER_EMAIL = _env("ETRANSFER_EMAIL", "orders@example.com")
    CONTACT_PHONE = _env("CONTACT_PHONE", "514-594-4092")

    # Telegram
    TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID", "")
    TELEGRAM_WEBHOOK_SECRET = _env("TELEGRAM_WEBHOOK_SECRET", "")

    # Delivery fee (optional flat fee)
    DELIVERY_FEE = float(_env("DELIVERY_FEE", "5.00"))

    # Pricing — boxes always 6× and 12× unit price (only COOKIE_UNIT_PRICE is configurable)
    COOKIE_UNIT_PRICE = float(_env("COOKIE_UNIT_PRICE", "4.00"))
    BOX_6_PRICE = COOKIE_UNIT_PRICE * 6
    BOX_12_PRICE = COOKIE_UNIT_PRICE * 12
