"""News endpoints for the Market Analyzer API."""

from flask import Blueprint, jsonify, request
import logging

from ...services.news_service import get_recent_news

logger = logging.getLogger(__name__)

def register_routes(bp: Blueprint):
    """Register routes with blueprint.
    
    Args:
        bp: Blueprint to register routes with
    """
    @bp.route('/news', methods=['GET'])
    def get_news():
        """Get recent news articles with sentiment analysis.
        
        Returns:
            Flask response with news data
        """
        try:
            limit = request.args.get('limit', default=10, type=int)
            result = get_recent_news(limit=limit)
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in get_news endpoint: {str(e)}")
            logger.exception("News endpoint error")
            return jsonify({'error': str(e)}), 500 