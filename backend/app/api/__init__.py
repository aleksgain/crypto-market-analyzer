"""API module for the Market Analyzer API."""

from flask import Flask

def register_routes(app: Flask):
    """Register API routes with Flask app.
    
    Args:
        app: Flask application
    """
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api') 