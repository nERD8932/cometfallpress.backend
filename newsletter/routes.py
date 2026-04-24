import os
import secrets
from flask_wtf.csrf import generate_csrf
from .db import db, NewsletterUser, Admin
from werkzeug.security import check_password_hash
from .extensions import limiter, logger, login_manager
from flask import Blueprint, jsonify, request, redirect, session
from flask_login import login_required, login_user, logout_user, current_user


bp = Blueprint("main", __name__)

@bp.post('/newsletter/subscribe')
@limiter.limit("5 per hour")
def subscribe():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    name = data.get("name") or None

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
@bp.get('/newsletter/unsubscribe/<secret>')
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

@bp.post('/login')
@limiter.limit("5 per hour")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    pw = data.get("pw")

    if not username or not pw:
        return jsonify({"status": "Invalid Request"}), 400

    user = Admin.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.pw_hash, pw):
        return jsonify({"status": "Invalid Request"}), 400

    login_user(user)
    session.permanent = True
    return jsonify({"status": "Logged in"}), 200


@bp.get("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"status": "Logged out", "redirect_to": "/"}), 200

@bp.get("/csrf")
def get_csrf():
    return jsonify({"csrf_token": generate_csrf()})

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"status": "Unauthorized", "redirect_to": "/login"}), 401

@bp.get("/me")
def me():
    if current_user is None or current_user.is_anonymous:
        return jsonify({
            "status": "Not Logged In!",
        }), 401

    return jsonify({
        "status": "Logged In.",
        "username": current_user.username,
    }), 200

@bp.post("/newsletter/list")
@login_required
def newsletter_list():
    return jsonify({})

@bp.post("/newsletter/load")
@login_required
def newsletter_list():
    return jsonify({})

@bp.post("/newsletter/save")
@login_required
def newsletter_list():
    return jsonify({})