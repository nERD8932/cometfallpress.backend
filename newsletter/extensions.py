import logging
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address, default_limits=["2000 per day"])