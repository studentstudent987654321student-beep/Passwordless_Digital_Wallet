"""
Flask application factory and initialization.
"""
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import config_by_name

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
session = Session()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# In-memory challenge storage (for development without Redis)
challenge_store = {}


def get_redis_client():
    """Get Redis client if available, otherwise return None."""
    try:
        from redis import Redis
        redis_url = os.getenv('REDIS_URL', '')
        if redis_url and 'redis://' in redis_url:
            client = Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
    except:
        pass
    return None


def create_app(config_name=None):
    """
    Application factory pattern.
    Creates and configures the Flask application.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Load configuration
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Try Redis, fallback to filesystem sessions
    redis_client = get_redis_client()
    if redis_client:
        app.config['SESSION_TYPE'] = 'redis'
        app.config['SESSION_REDIS'] = redis_client
        app.logger.info('Using Redis for sessions')
    else:
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['SESSION_FILE_DIR'] = os.path.join(app.instance_path, 'sessions')
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
        app.logger.info('Using filesystem for sessions (Redis not available)')
    
    session.init_app(app)
    limiter.init_app(app)
    
    # Store redis client in app config for routes
    app.config['REDIS_CLIENT'] = redis_client
    
    # Configure logging
    configure_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Add security headers
    @app.after_request
    def add_security_headers(response):
        for header, value in app.config.get('SECURITY_HEADERS', {}).items():
            response.headers[header] = value
        return response
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    app.logger.info(f'Passwordless Wallet started in {config_name} mode')
    
    return app


def configure_logging(app):
    """Configure application logging."""
    log_level = getattr(logging, app.config['LOG_LEVEL'])
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(app.config['LOG_FILE'])
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # File handler
    file_handler = logging.FileHandler(app.config['LOG_FILE'])
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)


def register_blueprints(app):
    """Register Flask blueprints."""
    from app.routes.auth import auth_bp
    from app.routes.wallet import wallet_bp
    from app.routes.main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(wallet_bp, url_prefix='/wallet')


def register_error_handlers(app):
    """Register error handlers."""
    from flask import render_template, jsonify
    
    @app.errorhandler(404)
    def not_found(error):
        if app.config['FLASK_ENV'] == 'development':
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Internal error: {error}')
        if app.config['FLASK_ENV'] == 'development':
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(error):
        app.logger.warning(f'Rate limit exceeded: {error}')
        return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
