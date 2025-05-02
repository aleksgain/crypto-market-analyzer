"""API route definitions."""

from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import endpoints
from .endpoints.prices import register_routes as register_prices_routes
from .endpoints.news import register_routes as register_news_routes
from .endpoints.predictions import register_routes as register_predictions_routes
from .endpoints.accuracy import register_routes as register_accuracy_routes
from .endpoints.insights import register_routes as register_insights_routes
from .endpoints.test import register_routes as register_test_routes

# Register endpoints
register_prices_routes(api_bp)
register_news_routes(api_bp)
register_predictions_routes(api_bp)
register_accuracy_routes(api_bp)
register_insights_routes(api_bp)
register_test_routes(api_bp) 