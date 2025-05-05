"""Test endpoints for the Market Analyzer API."""

from flask import Blueprint, jsonify
import logging
from ...services import news_service, openai_service

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
            
    @bp.route('/test-connectivity', methods=['GET'])
    def test_connectivity():
        """Test endpoint to check API connectivity.
        
        Returns:
            Flask response with connectivity status
        """
        try:
            return jsonify({
                'status': 'ok',
                'message': 'Backend API is reachable'
            })
        except Exception as e:
            logger.error(f"Error in connectivity test: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @bp.route('/test-eventregistry', methods=['GET'])
    def test_eventregistry():
        """Test endpoint to check Event Registry connectivity.
        
        Returns:
            Flask response with Event Registry status
        """
        try:
            # Simple test call to news service
            status = news_service.check_eventregistry_status()
            return jsonify({
                'status': 'ok' if status else 'error',
                'message': 'Event Registry is working' if status else 'Event Registry is not available'
            })
        except Exception as e:
            logger.error(f"Error in Event Registry test: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @bp.route('/test-openai', methods=['GET'])
    def test_openai():
        """Test endpoint to check OpenAI connectivity.
        
        Returns:
            Flask response with OpenAI status
        """
        try:
            # Return status based on openai_client availability
            status = openai_service.openai_client is not None
            return jsonify({
                'status': 'ok' if status else 'disabled',
                'message': 'OpenAI is working' if status else 'OpenAI client is disabled or not available'
            })
        except Exception as e:
            logger.error(f"Error in OpenAI test: {str(e)}")
            return jsonify({'error': str(e)}), 500 