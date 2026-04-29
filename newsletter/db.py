import uuid
from datetime import UTC
from .extensions import db
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKey

class Admin(db.Model, UserMixin):
    __tablename__ = "admins"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.Text, unique=True, nullable=False)
    pw_hash = db.Column(db.Text, nullable=False)

class NewsletterList(db.Model):
    __tablename__ = "newsletter_list"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    datetime_added = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    created_by = db.Column(db.String(36), db.ForeignKey("admins.id"), nullable=True)
    last_update_by = db.Column(db.String(36), db.ForeignKey("admins.id"), nullable=True)
    datetime_updated = db.Column(db.DateTime, nullable=True, default=None)
    delta_content = db.Column(db.Text, nullable=False, default='{"delta":"","html":""}')
    sent_to_users = db.Column(db.Boolean, nullable=False, default=False)
    datetime_sent = db.Column(db.DateTime, nullable=True, default=None)

    created_by_admin = db.relationship(
        "Admin",
        foreign_keys=[created_by],
        backref="created_newsletters"
    )
    updated_by_admin = db.relationship(
        "Admin",
        foreign_keys=[last_update_by],
        backref="updated_newsletters"
    )
    deliveries = db.relationship("NewsletterDelivery", back_populates="newsletter")

    def get_content(self):
        return {
            "id": self.id,
            "datetime_added_raw": int(self.datetime_added.timestamp()) if self.datetime_added else None,
            "datetime_added": self.datetime_added.strftime("%A, %B %d, %Y") if self.datetime_added else None,
            "datetime_updated_raw": int(self.datetime_updated.timestamp()) if self.datetime_updated else None,
            "datetime_updated": self.datetime_updated.strftime("%A, %B %d, %Y") if self.datetime_updated else None,
            "delta_content": self.delta_content,
            "sent_to_users": self.sent_to_users,
            "datetime_sent": self.datetime_sent.strftime("%A, %B %d, %Y") if self.datetime_sent else None,
            "created_by": self.created_by_admin.username if self.created_by_admin else None,
            "last_update_by": self.updated_by_admin.username if self.updated_by_admin else None,
        }

    def get_identifiers(self):
        return {
            "id": self.id,
            "datetime_added_raw": int(self.datetime_added.timestamp()) if self.datetime_added else None,
            "datetime_added": self.datetime_added.strftime("%A, %B %d, %Y") if self.datetime_added else None,
            "datetime_updated_raw": int(self.datetime_updated.timestamp()) if self.datetime_updated else None,
            "datetime_updated": self.datetime_updated.strftime("%A, %B %d, %Y") if self.datetime_updated else None,
            "sent_to_users": self.sent_to_users,
            "datetime_sent": self.datetime_sent.strftime("%A, %B %d, %Y") if self.datetime_sent else None,
            "created_by": self.created_by_admin.username if self.created_by_admin else None,
            "last_update_by": self.updated_by_admin.username if self.updated_by_admin else None,
        }

class NewsletterUser(db.Model):
    __tablename__ = "newsletter_users"

    email = db.Column(db.Text, primary_key=True, nullable=False)
    name = db.Column(db.Text, nullable=True, default=None)
    datetime_joined = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    unsubscribed = db.Column(db.Boolean, nullable=False, default=False)
    unsubscribe_secret = db.Column(db.Text, unique=True, nullable=False)

    deliveries = db.relationship("NewsletterDelivery", back_populates="user")

    def to_dict(self):
        if self.unsubscribed:
            return None
        return {
            "email": self.email,
            "name": self.name if self.name else None,
            "date_joined": self.datetime_joined.strftime("%A, %B %d, %Y") if self.datetime_joined else None,
        }


class NewsletterDelivery(db.Model):
    __tablename__ = "newsletter_deliveries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    newsletter_id = db.Column(
        db.String(36),
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
