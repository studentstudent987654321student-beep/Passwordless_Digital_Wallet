"""
Main routes for the application.
Renders pages and handles general navigation.
"""
from flask import Blueprint, render_template, session, redirect, url_for

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page - redirect based on auth status."""
    if session.get('authenticated'):
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@main_bp.route('/register')
def register_page():
    """Registration page."""
    if session.get('authenticated'):
        return redirect(url_for('main.dashboard'))
    return render_template('register.html')


@main_bp.route('/login')
def login_page():
    """Login page."""
    if session.get('authenticated'):
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')


@main_bp.route('/dashboard')
def dashboard():
    """Wallet dashboard - requires authentication."""
    if not session.get('authenticated'):
        return redirect(url_for('main.login_page'))
    return render_template('dashboard.html', 
                         user_email=session.get('email'))


@main_bp.route('/about')
def about():
    """About page - information about the project."""
    return render_template('about.html')
