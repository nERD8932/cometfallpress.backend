import os
from .routes import bp
from flask import Flask
from flask_cors import CORS
from .extensions import db, migrate, limiter
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app():
    app = Flask(__name__, static_folder='public', static_url_path='')
    CORS(app, resources={
        r"/*": {
            "origins": [
                "https://cometfallpress.com",
            ]
        }
    })
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

    db_path = os.getenv("DATABASE_PATH")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    app.register_blueprint(bp)
    return app
