import os
import logging
import secrets
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask import Flask, request, jsonify
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    limiter = Limiter(
        get_remote_address,
        app=app
    )
    load_dotenv()
    app.config.from_mapping(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY"),
        DATABASE="/data/database.db",
    )

    from . import db
    db.init_app(app)

    with app.app_context():
        db.init_db()

    @app.post('/newsletter/subscribe')
    @limiter.limit("5 per hour")
    def subscribe():
        email = request.form.get("email")
        name = request.form.get("name") or None


        if not email:
            return jsonify({"status": "Email is required"}), 400

        secret = secrets.token_urlsafe(32)
        conn = db.get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM newsletter_users WHERE email = ?",
                (email,)
            )

            row = cursor.fetchone()

            if row is None:
                cursor.execute(
                    "INSERT INTO newsletter_users (email, name, unsubscribe_secret) VALUES (?, ?, ?)",
                    (email, name, secret)
                )
                conn.commit()
                return jsonify({"status": "Subscribed!"}), 200

            elif row["unsubscribed"] == 1:
                cursor.execute(
                    "UPDATE newsletter_users SET unsubscribe_secret = ?, unsubscribed = 0 WHERE email = ?",
                    (secret, email)
                )
                conn.commit()
                return jsonify({"status": "Subscribed!"}), 200

            elif row["unsubscribed"] == 0:
                return jsonify(
                    {"status": "You're already subscribed to the newsletter!"}), 400

        except (Exception,):
            logging.exception("Subscription request failed!")
            return jsonify({"status": "An error occurred while processing your request, please try again later!"}), 500
        finally:
            conn.close()


    @limiter.limit("5 per hour")
    @app.post('/newsletter/unsubscribe/<secret>')
    def unsubscribe(secret):
        conn = db.get_db()
        cursor = conn.cursor()

        if secret == "" or secret is None:
            return jsonify({"status": "Invalid request!"}), 400

        try:
            cursor.execute(
                "SELECT * FROM newsletter_users WHERE unsubscribe_secret = ?",
                (secret,)
            )

            row = cursor.fetchone()

            if row is None:
                return jsonify({"status": "Invalid request!"}), 400
            elif row["unsubscribed"] == 1:
                return jsonify({"status": "You've already unsubscribed from the newsletter."}), 400
            else:
                cursor.execute(
                    "UPDATE newsletter_users SET unsubscribed = 1 WHERE unsubscribe_secret = ?",
                    (secret,)
                )
                conn.commit()
                return jsonify({"status": "Unsubscribed!"}), 200
        except (Exception,):
            logging.exception("Unsubscription request failed!")
            return jsonify({
                "status": "An error occurred while processing your request, please try again later!"
            }), 500
        finally:
            conn.close()



    return app

