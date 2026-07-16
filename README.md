# Cookie Business Ordering System

A full-stack cookie shop ordering app: public storefront, session cart, checkout (cash + Interac e-Transfer only), Telegram order alerts with status buttons, confirmation emails, and an admin dashboard.

## Tech stack

- **Backend:** Python 3.10+ (3.13 or 3.10 on your machine), Flask, SQLAlchemy
- **Database:** PostgreSQL
- **Frontend:** HTML, Bootstrap 5, custom CSS
- **Integrations:** Telegram Bot API, Flask-Mail (SMTP)

## Project structure

```
project/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── admin.py
│   ├── telegram_bot.py
│   ├── email_service.py
│   └── config.py
├── templates/
├── static/
├── main.py
├── requirements.txt
└── README.md
```

## Quick start

### 1. PostgreSQL

Create a database:

```sql
CREATE DATABASE cookie_orders;
```

### 2. Environment

```bash
cp .env.example .env
# Edit .env with your DATABASE_URL, mail, and Telegram settings
```

### 3. Install & run

```powershell
py -0p                         # list installed versions (you have 3.10 and 3.13)
py -3.10 -m venv venv          # recommended on Windows (3.13 may fail on psycopg2)
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

> **Note:** Python 3.11 is not required. Use **3.10** or **3.13**. If `pip install` fails on 3.13, use `py -3.10` instead.

Open **http://127.0.0.1:5000**

- **Storefront:** `/`
- **Admin:** `/admin/login` (default `admin` / `admin123` from `.env` on first run)

## Telegram setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token into `TELEGRAM_BOT_TOKEN`.
2. Get your chat ID (message the bot, then open `https://api.telegram.org/bot<TOKEN>/getUpdates`) and set `TELEGRAM_CHAT_ID`.
3. **Local development:** Telegram needs HTTPS for webhooks. Options:
   - Use [ngrok](https://ngrok.com/) and register the webhook:
     ```bash
     curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://YOUR-NGROK-URL/telegram/webhook&secret_token=YOUR_SECRET"
     ```
     Set `TELEGRAM_WEBHOOK_SECRET` to the same secret.
   - Or update order status from the **admin dashboard** (works without webhook).

Inline buttons on each order message:

- Accept Order → Preparing
- Preparing / Out for Delivery / Completed / Cancel

## Email setup

Configure SMTP in `.env` (Gmail: use an [App Password](https://support.google.com/accounts/answer/185833)). If mail is not configured, orders still save and Telegram still fires; only the customer email is skipped.

## Admin features

- View and filter orders by status
- Update order status
- Add / edit / deactivate products
- Upload product images (`static/images/uploads/`)
- Stats: total orders, sales (cash vs e-Transfer), best-selling cookie

## Payment model

No Stripe or card processing. Customers choose **Cash** or **Interac e-Transfer** at checkout. Confirmation email includes payment instructions.

## Production notes

- Set a strong `SECRET_KEY` and change the default admin password.
- Use **gunicorn** behind nginx: `gunicorn -w 4 -b 0.0.0.0:8000 "main:app"`
- Serve uploaded images from `static/` or move to object storage for scale.

## License

MIT — use freely for your cookie business.
