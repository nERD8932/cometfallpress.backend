import secrets
import logging
from .db import db, NewsletterUser
from .extensions import limiter, logger
from flask import Blueprint, jsonify, request, redirect, url_for


bp = Blueprint("main", __name__)

@bp.route('/newsletter/subscribe', methods=['POST'])
@limiter.limit("5 per hour")
def subscribe():
    email = request.form.get("email")
    name = request.form.get("name") or None

    if not email:
        return jsonify({"status": "Email is required"}), 400

    secret = secrets.token_urlsafe(32)

    try:
        existing_user = NewsletterUser.query.filter_by(email=email).first()

        if existing_user is None:
            user = NewsletterUser(email=email, name=name, unsubscribe_secret=secret)
            db.session.add(user)
            db.session.commit()
            return jsonify({"status": "Subscribed!"}), 200

        elif existing_user.unsubscribed:
            existing_user.unsubscribe_secret = secret
            existing_user.unsubscribed = False
            db.session.commit()
            return jsonify({"status": "Subscribed!"}), 200

        elif not existing_user.unsubscribed:
            return jsonify(
                {"status": "You're already subscribed to the newsletter!"}), 400

    except (Exception,):
        db.session.rollback()
        logger.exception("Subscription request failed!")
        return jsonify({"status": "An error occurred while processing your request, please try again later!"}), 500

@limiter.limit("5 per hour")
@bp.route('/newsletter/unsubscribe/<secret>', methods=['GET'])
def unsubscribe(secret):
    if secret == "" or secret is None:
        return jsonify({"status": "Invalid request!"}), 400

    try:
        existing_user = NewsletterUser.query.filter_by(unsubscribe_secret=secret).first()

        if existing_user is None:
            return jsonify({"status": "Invalid request!"}), 400
        elif existing_user.unsubscribed:
            return jsonify({"status": "Invalid request!"}), 400
        else:
            existing_user.unsubscribed = True
            db.session.update(existing_user)
            db.session.commit()
            return jsonify({"status": "Unsubscribed!"}), 200
    except (Exception,):
        db.session.rollback()
        logger.exception("Unsubscription request failed!")
        return jsonify({
            "status": "An error occurred while processing your request, please try again later!"
        }), 50