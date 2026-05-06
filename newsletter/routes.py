import os
import json
import uuid
import logging
import secrets
from datetime import UTC
from PIL import Image as Img
from datetime import datetime
from email.message import EmailMessage
from flask_wtf.csrf import generate_csrf
from werkzeug.security import check_password_hash
from .db import db, NewsletterUser, Admin, NewsletterList, Image, NewsletterDelivery
from flask import Blueprint, jsonify, request, session, send_file
from flask_login import login_required, login_user, logout_user, current_user
from .extensions import (
    logger,
    limiter,
    get_smtp,
    hash_file,
    upload_path,
    login_manager,
    backend_origin,
    allowed_image_mimes, clean_html,
)

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
        return jsonify({"status": "Invalid Request!"}), 400

    user = Admin.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.pw_hash, pw):
        return jsonify({"status": "Invalid Request!"}), 400

    login_user(user)
    session.permanent = True
    return jsonify({"status": "Logged in!"}), 200


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"status": "Logged out!", "redirect_to": "/"}), 200

@bp.get("/csrf")
def get_csrf():
    return jsonify({"csrf_token": generate_csrf()})

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"status": "Unauthorized!", "redirect_to": "/login"}), 401

@bp.get("/me")
def me():
    if current_user is None or current_user.is_anonymous:
        return jsonify({
            "status": "Not Logged In!",
        }), 401

    return jsonify({
        "status": "Logged In!",
        "username": current_user.username,
    }), 200

@bp.post("/newsletter/subscribers")
@login_required
def newsletter_get_subscribers():
    subscribers = NewsletterUser.query.all()
    return jsonify([u.to_dict() for u in subscribers if u.to_dict() is not None]), 200

@limiter.limit("5 per hour")
@bp.post("/newsletter/new")
@login_required
def newsletter_new():
    newsletter = NewsletterList(
        created_by=current_user.id,
    )
    db.session.add(newsletter)
    db.session.commit()
    return jsonify({"status": "Created a new newsletter!", "id": newsletter.id}), 200

@bp.post("/newsletter/list")
@login_required
def newsletter_list():
    newsletters = NewsletterList.query.all()
    return jsonify([n.get_identifiers() for n in newsletters])

@bp.post("/newsletter/load/<nid>")
@login_required
def newsletter_load(nid):
    data = request.get_json(silent=True) or {}
    rnid = str(data.get("nid"))

    if rnid is None or rnid != str(nid):
        return jsonify({"status": "Invalid request!"}), 400

    newsletter = NewsletterList.query.filter_by(id=rnid).first()
    if newsletter is None:
        return jsonify({"status": "Invalid request!"}), 400
    return jsonify(newsletter.get_content()), 200

@bp.post("/newsletter/save/<nid>")
@login_required
def newsletter_save(nid):
    data = request.get_json(silent=True) or {}
    delta = json.loads(data.get("delta", ""))
    delta["html"] = clean_html(str(delta.get("html", "")))
    delta = json.dumps(delta)
    title = str(data.get("title"))
    rnid = str(data.get("nid"))

    if None in [rnid, delta] or rnid != str(nid):
        return jsonify({"status": "Invalid request!"}), 400

    newsletter = NewsletterList.query.filter_by(id=rnid).first()

    if newsletter is None:
        return jsonify({"status": "Invalid request!"}), 400

    if delta and newsletter.delta_content != delta:
        newsletter.delta_content = delta

    if title and newsletter.title != title:
        newsletter.title = title

    newsletter.last_update_by = current_user.id
    newsletter.datetime_updated = datetime.now(UTC)
    db.session.commit()

    return jsonify({"status": "Saved!"}), 200

@bp.post("/newsletter/publish/<nid>")
@login_required
def newsletter_publish(nid):
    data = request.get_json(silent=True) or {}
    rnid = str(data.get("nid"))
    p_type = str(request.args.get('type'))

    if rnid is None or rnid != str(nid) or p_type not in ["draft", "publish"]:
        return jsonify({"status": "Invalid request!"}), 400

    newsletter = NewsletterList.query.filter_by(id=rnid).first()
    if newsletter is None:
        return jsonify({"status": "Invalid request!"}), 400
    else:
        emails = []
        errors = {}

        try:
            html_content = str(json.loads(newsletter.delta_content).get("html"))
            sender_email = os.environ["GMAIL_USER"]
        except (Exception, ) as e:
            logger.error(e)
            return jsonify({"status": "An internal server error occurred, please try again later!"}), 500

        if p_type == "publish":
            for usr in NewsletterUser.query.all():
                try:
                    msg = EmailMessage()
                    msg["Subject"] = newsletter.title
                    msg["From"] = sender_email
                    msg["To"] = usr.email
                    iden = usr.name if usr.name is not None else usr.email
                    msg.set_content("This email requires an HTML-compatible client.")
                    msg.add_alternative(html_content.replace("{{username}}", iden), subtype="html")
                    emails.append(msg)
                    ns_delivery = NewsletterDelivery(
                        newsletter_id = newsletter.id,
                        user_email = usr.email,
                        status = "pending"
                    )
                    db.session.add(ns_delivery)
                except (Exception, ) as e:
                    logging.error(e)
                    errors[usr.email] = str(e)
                    db.session.rollback()
            db.session.commit()
        else:
            try:
                msg = EmailMessage()
                msg["Subject"] = newsletter.title
                msg["From"] = sender_email
                msg["To"] = sender_email
                msg.set_content("This email requires an HTML-compatible client.")
                msg.add_alternative(html_content, subtype="html")
                emails.append(msg)
            except (Exception,) as e:
                logging.error(e)
                return jsonify({"status": "An internal server error occurred, please try again later!"}), 500

        smtp = get_smtp()
        if smtp is None:
            return jsonify({"status": "An internal server error occurred, please try again later!"}), 500

        for email in emails:
            try:
                smtp.send_message(
                    email,
                    to_addrs=[email["To"]]
                )
                if p_type == "publish":
                    nsd = NewsletterDelivery.query.filter_by(newsletter_id=newsletter.id, user_email=email["To"]).first()
                    nsd.status = "sent"
                    newsletter.sent_to_users = True
                    newsletter.datetime_sent = datetime.now()
                    db.session.add(nsd)
                    db.session.add(newsletter)
                    db.session.commit()
            except (Exception,) as e:
                logger.error(e)
                errors[email["To"]] = str(e)
                if p_type == "publish":
                    db.session.rollback()
                    try:
                        nsd = NewsletterDelivery.query.filter_by(newsletter_id=newsletter.id, user_email=email["To"]).first()
                        nsd.status = "failed"
                        db.session.add(nsd)
                        db.session.commit()
                    except (Exception,) as e:
                        pass

        if len(errors) > 0:
            return jsonify({"status": "An error occurred while sending emails to some of the addresses", "errors": errors}), 500

    return jsonify({"status": "Published!"}), 200

@bp.post("/newsletter/upload")
@login_required
def upload_image():
    file = request.files.get('image')

    if not file or not file.filename:
        return jsonify({"status": "Failed!"}), 400

    ext = str(file.filename).split(".")[-1]
    if ext not in allowed_image_mimes:
        return jsonify({"status": "Disallowed file type!"}), 400

    file_hash = hash_file(file)

    existing = Image.query.filter_by(hash=file_hash).first()
    if existing:
        return jsonify({
            "status": "Saved!",
            "image_url": f"{backend_origin}/images/{existing.filename}"
        }), 200

    name = str(uuid.uuid4())
    mime_type = str(file.mimetype)

    temp_path = upload_path / f"{name}.upload"
    final_path = upload_path / f"{name}.png"
    file.save(temp_path)

    try:
        with Img.open(temp_path) as im:
            im.verify()
        with Img.open(temp_path) as im:
            im.save(final_path)
            mime_type = im.get_format_mimetype()
        temp_path.unlink(missing_ok=True)

    except (Exception, ) as e:
        temp_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        return jsonify({"status": "Image rejected!"}), 400

    img = Image(filename=name, mime_type=mime_type, hash=file_hash)
    db.session.add(img)
    db.session.commit()

    return jsonify({"status": "Saved!", "image_url": f"{backend_origin}/images/{name}"}), 200

@bp.get("/images/<image_id>")
def image(image_id):
    row = Image.query.get_or_404(image_id)
    return send_file(str(upload_path / f"{row.filename}.png"), mimetype=row.mime_type)

@bp.errorhandler(Exception)
def handle_global_exception(e):
    logger.error(e)
    response = jsonify({
        "status": "Internal Server Error",
    })
    db.session.rollback()
    return response, 500

