import os
import smtplib
import logging
import hashlib
from pathlib import Path
from typing import Optional
from sqlalchemy import MetaData
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_executor import Executor
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_limiter.util import get_remote_address


convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=convention))
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
limiter = Limiter(key_func=get_remote_address, default_limits=["2000 per day"])
allowed_image_mimes = {"jpg", "jpeg", "png", "webp"}
upload_path = Path(os.getenv("UPLOAD_PATH", ""))
backend_origin = os.getenv('BACKEND_ORIGIN', 'https://api.cometfallpress.com')
hasher = hashlib.sha256()
executor = Executor()

def get_smtp() -> smtplib.SMTP_SSL | None:
    smtp = None
    try:
        smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
        smtp.login(
            os.getenv("GMAIL_USER", ""),
            os.getenv("GMAIL_PASSWORD", ""),
        )
    except (Exception, ):
        pass

    return smtp

def hash_file(file_storage):
    hasher = hashlib.sha256()

    for chunk in iter(lambda: file_storage.stream.read(8192), b""):
        hasher.update(chunk)

    file_storage.stream.seek(0)
    return hasher.hexdigest()

def clean_html(html):
    return html