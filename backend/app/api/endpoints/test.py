"""Test endpoints for the Market Analyzer API."""

from flask import Blueprint, jsonify
import logging

logger = logging.getLogger(__name__)

def register_routes(bp: Blueprint):
    """Register routes with blueprint.
    
    Args:
        bp: Blueprint to register routes with
    """
    @bp.route('/test', methods=['GET'])
    def test_endpoint():
        """Simple test endpoint to check if API is working.
        
        Returns:
            Flask response with test status
        """
        try:
            return jsonify({
                'status': 'ok',
                'message': 'API is running correctly'
            })
        except Exception as e:
            logger.error(f"Error in test endpoint: {str(e)}")
            logger.exception("Test endpoint error")
            return jsonify({'error': str(e)}), 500 