"""Market insights endpoints for the Market Analyzer API."""

from flask import Blueprint, jsonify, request
import logging

from ...services.openai_service import extract_market_insights, generate_market_analysis

logger = logging.getLogger(__name__)

def register_routes(bp: Blueprint):
    """Register routes with blueprint.
    
    Args:
        bp: Blueprint to register routes with
    """
    @bp.route('/insights', methods=['GET'])
    def get_market_insights():
        """Get market insights based on news and price data.
        
        Returns:
            Flask response with market insights
        """
        try:
            # This endpoint combines news and price data to provide insights
            # It will pass the news data to OpenAI for analysis
            
            # Import here to avoid circular imports
            from ...services.news_service import get_recent_news
            from ...services.coin_service import get_current_prices
            
            # Get news and price data
            news_data = get_recent_news()
            crypto_data = get_current_prices(['BTC', 'ETH'])
            
            # Extract insights from news
            news_insights = extract_market_insights(news_data.get('news', []), limit=3)
            
            # Generate market analysis
            market_analysis = generate_market_analysis(crypto_data)
            
            # Combine insights
            insights = {
                'news_insights': news_insights,
                'market_analysis': market_analysis
            }
            
            return jsonify({'insights': insights})
        except Exception as e:
            logger.error(f"Error in get_market_insights endpoint: {str(e)}")
            logger.exception("Insights endpoint error")
            return jsonify({'error': str(e)}), 500 