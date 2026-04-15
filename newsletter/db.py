from .extensions import db
from datetime import datetime
from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKey

class NewsletterUser(db.Model):
    __tablename__ = "newsletter_users"

    email = db.Column(db.Text, primary_key=True)
    name = db.Column(db.Text)
    datetime_joined = db.Column(db.DateTime, default=datetime.utcnow)

    unsubscribed = db.Column(db.Boolean, nullable=False, default=False)
    unsubscribe_secret = db.Column(db.Text, unique=True, nullable=False)

    deliveries = db.relationship("NewsletterDelivery", back_populates="user")


class NewsletterList(db.Model):
    __tablename__ = "newsletter_list"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime_added = db.Column(db.DateTime, default=datetime.utcnow)

    email_content = db.Column(db.Text, nullable=False)
    sent_to_users = db.Column(db.Integer, nullable=False, default=0)
    datetime_sent = db.Column(db.DateTime, nullable=True)

    deliveries = db.relationship("NewsletterDelivery", back_populates="newsletter")


class NewsletterDelivery(db.Model):
    __tablename__ = "newsletter_deliveries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    newsletter_id = db.Column(
        db.Integer,
        ForeignKey("newsletter_list.id"),
        nullable=False
    )

    user_email = db.Column(
        db.Text,
        ForeignKey("newsletter_users.email"),
        nullable=False
    )

    datetime_sent = db.Column(db.DateTime, nullable=True)

    status = db.Column(
        db.Text,
        default="pending"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','sent','failed','opened')",
            name="check_status"
        ),
        UniqueConstraint("newsletter_id", "user_email", name="unique_delivery"),
    )

    newsletter = db.relationship("NewsletterList", back_populates="deliveries")
    user = db.relationship("NewsletterUser", back_populates="deliveries")


class Admin(db.Model):
    __tablename__ = "admins"

    username = db.Column(db.Text, primary_key=True)
    pw_hash = db.Column(db.Text, nullable=False)