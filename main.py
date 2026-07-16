import os

from dotenv import load_dotenv

load_dotenv(override=True)

from app import create_app

app = create_app()


if __name__ == "__main__":
    with app.app_context():
        pass

    app.run(debug=os.environ.get("FLASK_DEBUG", "true").lower() == "true", port=5000)
