import json
import os
from .db import Admin
from .routes import bp
from flask import Flask
from flask_cors import CORS
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash
from .extensions import db, migrate, csrf, login_manager, logger, limiter

def create_app():
    app = Flask(__name__, static_folder='public', static_url_path='')
    CORS(
        app,
        supports_credentials = True,
        resources={
        r"/*": {
            "origins": [
                os.getenv("FRONTEND_ORIGIN", "https://www.cometfallpress.com"),
            ]
        }
    })

    db_path = os.getenv("DATABASE_PATH")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY"),
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=120),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_TRUSTED_ORIGINS= [os.getenv("FRONTEND_ORIGIN", "https://www.cometfallpress.com")]
    )

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.register_blueprint(bp)

    with app.app_context():
        create_admins()

    return app

def create_admins():
    admins = json.loads(os.getenv("ADMINS"))
    for a in admins:
        try:
            admin = Admin.query.filter_by(username=a["username"]).first()
            if not admin:
                admin = Admin(username=a["username"], pw_hash=generate_password_hash(a["password"]))
                db.session.add(admin)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.exception(e)