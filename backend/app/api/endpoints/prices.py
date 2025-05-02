"""Price endpoints for the Market Analyzer API."""

from flask import Blueprint, jsonify, request
import logging

from ...services.coin_service import get_current_prices

logger = logging.getLogger(__name__)

def register_routes(bp: Blueprint):
    """Register routes with blueprint.
    
    Args:
        bp: Blueprint to register routes with
    """
    @bp.route('/prices', methods=['GET'])
    def get_prices():
        """Get current prices for cryptocurrency symbols.
        
        Returns:
            Flask response with price data
        """
        symbols = request.args.get('symbols', 'BTC,ETH').split(',')
        
        try:
            result = get_current_prices(symbols)
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in get_prices: {str(e)}")
            logger.exception("Price endpoint error")
            return jsonify({'error': str(e)}), 500 