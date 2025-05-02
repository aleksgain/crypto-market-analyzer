"""Prediction endpoints for the Market Analyzer API."""

from flask import Blueprint, jsonify, request
import logging

from ...services.prediction_service import get_price_predictions

logger = logging.getLogger(__name__)

def register_routes(bp: Blueprint):
    """Register routes with blueprint.
    
    Args:
        bp: Blueprint to register routes with
    """
    @bp.route('/predictions', methods=['GET'])
    def get_predictions():
        """Get price predictions for cryptocurrencies.
        
        Returns:
            Flask response with prediction data
        """
        try:
            # Get symbols from query params or use defaults
            symbols = request.args.get('symbols', 'BTC,ETH').split(',')
            
            # Get predictions
            predictions = get_price_predictions(symbols)
            
            return jsonify({'predictions': predictions})
        except Exception as e:
            logger.error(f"Error in get_predictions endpoint: {str(e)}")
            logger.exception("Predictions endpoint error")
            return jsonify({'error': str(e)}), 500 