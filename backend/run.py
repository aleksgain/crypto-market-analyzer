"""Market Analyzer API main application."""

import os
import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.config import logging_level
from app.db.connection import init_db
from app.api import register_routes

# Configure logging
logging.basicConfig(
    level=logging_level, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create Flask application."""
    app = Flask(__name__)
    CORS(app)
    
    # Initialize database
    init_db()
    
    # Register API routes
    register_routes(app)
    
    # Add health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'ok'}, 200
    
    logger.info("Application initialized successfully")
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 