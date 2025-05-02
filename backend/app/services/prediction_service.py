"""Prediction service for cryptocurrency price forecasting."""

import logging
from datetime import timedelta
from typing import Dict, List, Optional, Any

from ..config import PREDICTION_INTERVALS
from ..db.connection import get_connection
from ..utils.datetime_utils import get_utc_now
from ..services.coin_service import get_historical_prices
from ..services.technical_analysis import calculate_technical_indicators

logger = logging.getLogger(__name__)

def get_price_predictions(symbols: List[str]) -> Dict[str, Any]:
    """Get price predictions for multiple cryptocurrency symbols.
    
    Args:
        symbols: List of cryptocurrency symbols
        
    Returns:
        dict: Predictions by symbol
    """
    result = {}
    
    for symbol in symbols:
        try:
            # Get current price and prediction data
            symbol_data = generate_predictions_for_symbol(symbol)
            if symbol_data:
                result[symbol] = symbol_data
        except Exception as e:
            logger.error(f"Error generating predictions for {symbol}: {str(e)}")
            logger.exception(f"Prediction error for {symbol}")
    
    return result

def generate_predictions_for_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Generate predictions for a specific cryptocurrency symbol.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        dict: Prediction data for the symbol
    """
    try:
        # Get current price
        current_price, price_data = get_current_price_and_data(symbol)
        if not current_price:
            logger.error(f"Could not get current price for {symbol}")
            return None
            
        # Get sentiment data
        sentiment_data = get_sentiment_data()
        
        # Get technical analysis
        historical_prices = get_historical_prices(symbol)
        tech_signals = calculate_technical_indicators(historical_prices, symbol)
        
        # Generate predictions for each interval
        predictions = {}
        current_time = get_utc_now()
        
        for days in PREDICTION_INTERVALS:
            # Calculate prediction
            prediction_data = calculate_prediction(
                symbol, 
                current_price, 
                current_time,
                days,
                sentiment_data,
                tech_signals
            )
            
            # Store prediction
            store_prediction(
                symbol,
                current_price,
                prediction_data['predicted_price'],
                current_time,
                current_time + timedelta(days=days),
                sentiment_data['sentiment_score'],
                sentiment_data['ai_sentiment_score']
            )
            
            # Add to results
            predictions[f"{days}_day"] = prediction_data
        
        # Return complete data
        return {
            'current_price': current_price,
            'predictions': predictions,
            'technical_signals': tech_signals
        }
    except Exception as e:
        logger.error(f"Error generating predictions for {symbol}: {str(e)}")
        logger.exception(f"Prediction error for {symbol}")
        return None

def get_current_price_and_data(symbol: str) -> tuple:
    """Get current price and related data for a symbol.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        tuple: (current_price, price_data)
    """
    try:
        # Query the database for the most recent price
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT price, market_cap, volume_24h
            FROM crypto_prices
            WHERE symbol = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (symbol,)
        )
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            logger.warning(f"No price data found for {symbol}")
            return None, None
            
        current_price = row[0]
        price_data = {
            'price': row[0],
            'market_cap': row[1],
            'volume_24h': row[2]
        }
        
        return current_price, price_data
    except Exception as e:
        logger.error(f"Error getting current price for {symbol}: {str(e)}")
        logger.exception("Price data error")
        return None, None

def get_sentiment_data() -> Dict[str, Any]:
    """Get recent sentiment data from news.
    
    Returns:
        dict: Sentiment data
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        current_time = get_utc_now()
        
        # Get traditional sentiment from recent news (1 day)
        cur.execute(
            """
            SELECT AVG(sentiment_score) as avg_sentiment 
            FROM news_sentiment 
            WHERE timestamp > %s
            """,
            (current_time - timedelta(days=1),)
        )
        
        sentiment_data = cur.fetchone()
        recent_sentiment_score = sentiment_data[0] if sentiment_data and sentiment_data[0] else 0
        
        # Get AI sentiment if available from recent news
        cur.execute(
            """
            SELECT AVG(ai_score) as avg_ai_sentiment 
            FROM news_sentiment 
            WHERE timestamp > %s AND ai_score IS NOT NULL
            """,
            (current_time - timedelta(days=1),)
        )
        
        ai_sentiment_data = cur.fetchone()
        recent_ai_sentiment_score = ai_sentiment_data[0] if ai_sentiment_data and ai_sentiment_data[0] else None
        
        # Get significant historical events (7 days) - only those with high impact
        cur.execute(
            """
            SELECT AVG(sentiment_score) as avg_sentiment,
                   AVG(CASE WHEN ai_score IS NOT NULL THEN ai_score ELSE NULL END) as avg_ai_sentiment,
                   COUNT(*) as significant_events_count
            FROM news_sentiment 
            WHERE timestamp BETWEEN %s AND %s
            AND ((ABS(sentiment_score) > 0.6) OR (ABS(ai_score) > 6))
            """,
            (current_time - timedelta(days=7), current_time - timedelta(days=1))
        )
        
        historical_data = cur.fetchone()
        historical_sentiment_score = historical_data[0] if historical_data and historical_data[0] else 0
        historical_ai_sentiment_score = historical_data[1] if historical_data and historical_data[1] else None
        significant_events_count = historical_data[2] if historical_data else 0
        
        cur.close()
        conn.close()
        
        # Combine recent and historical sentiment with appropriate weighting
        # If there are significant historical events, give them more weight
        historical_weight = min(0.4, 0.1 * significant_events_count) if significant_events_count > 0 else 0
        recent_weight = 1 - historical_weight
        
        # Combine sentiment scores
        sentiment_score = (recent_sentiment_score * recent_weight) + (historical_sentiment_score * historical_weight)
        
        # Combine AI sentiment scores if available
        ai_sentiment_score = None
        if recent_ai_sentiment_score is not None and historical_ai_sentiment_score is not None:
            ai_sentiment_score = (recent_ai_sentiment_score * recent_weight) + (historical_ai_sentiment_score * historical_weight)
        elif recent_ai_sentiment_score is not None:
            ai_sentiment_score = recent_ai_sentiment_score
        elif historical_ai_sentiment_score is not None:
            ai_sentiment_score = historical_ai_sentiment_score
        
        return {
            'sentiment_score': sentiment_score,
            'ai_sentiment_score': ai_sentiment_score,
            'recent_sentiment_score': recent_sentiment_score,
            'historical_sentiment_score': historical_sentiment_score,
            'recent_weight': recent_weight,
            'historical_weight': historical_weight,
            'significant_events_count': significant_events_count
        }
    except Exception as e:
        logger.error(f"Error getting sentiment data: {str(e)}")
        logger.exception("Sentiment data error")
        return {
            'sentiment_score': 0,
            'ai_sentiment_score': None,
            'recent_sentiment_score': 0,
            'historical_sentiment_score': 0,
            'recent_weight': 1,
            'historical_weight': 0,
            'significant_events_count': 0
        }

def calculate_prediction(
    symbol: str,
    current_price: float,
    current_time,
    days: int,
    sentiment_data: Dict[str, Any],
    tech_signals: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Calculate price prediction for a specific interval.
    
    Args:
        symbol: Cryptocurrency symbol
        current_price: Current price
        current_time: Current time
        days: Prediction interval in days
        sentiment_data: Sentiment data
        tech_signals: Technical analysis signals
        
    Returns:
        dict: Prediction data
    """
    try:
        # Base sentiment adjustment
        if sentiment_data['ai_sentiment_score'] is not None:
            # AI sentiment is on -10 to 10 scale, normalize to -1 to 1 for consistency
            normalized_ai_sentiment = sentiment_data['ai_sentiment_score'] / 10
            # Use a stronger factor for AI sentiment since it's more accurate
            sentiment_adjustment = normalized_ai_sentiment * 0.15 * days/10
            sentiment_for_prediction = normalized_ai_sentiment
        else:
            # Fall back to traditional sentiment
            sentiment_adjustment = sentiment_data['sentiment_score'] * 0.1 * days/10
            sentiment_for_prediction = sentiment_data['sentiment_score']
        
        # Technical analysis adjustment
        tech_adjustment = 0
        if tech_signals:
            # Apply technical signals to the prediction
            if tech_signals['overall']['signal'] == 'bullish':
                tech_adjustment = 0.05 * tech_signals['overall']['strength'] * days/10
            elif tech_signals['overall']['signal'] == 'bearish':
                tech_adjustment = -0.05 * tech_signals['overall']['strength'] * days/10
        
        # Combined adjustment
        total_adjustment = 1 + sentiment_adjustment + tech_adjustment
        predicted_price = current_price * total_adjustment
        
        # Direction of prediction
        direction = "up" if predicted_price > current_price else "down"
        
        # Confidence based on alignment of signals
        confidence = 0.5  # Base confidence
        
        if tech_signals:
            # If sentiment and technical signals align, increase confidence
            sent_direction = "up" if sentiment_adjustment > 0 else "down"
            tech_direction = "up" if tech_adjustment > 0 else "down"
            
            if sent_direction == tech_direction == direction:
                confidence = 0.8  # High confidence when all align
            elif sent_direction == tech_direction:
                confidence = 0.7  # Good confidence when sentiment and tech align
            elif sent_direction == direction or tech_direction == direction:
                confidence = 0.6  # Moderate confidence when one aligns with prediction
                
        # Calculate target date
        target_date = current_time + timedelta(days=days)
        
        return {
            'predicted_price': predicted_price,
            'target_date': target_date.isoformat(),
            'sentiment_factor': sentiment_data['sentiment_score'],
            'ai_sentiment_factor': sentiment_data['ai_sentiment_score'],
            'technical_factor': tech_adjustment,
            'direction': direction,
            'confidence': confidence,
            'using_ai': sentiment_data['ai_sentiment_score'] is not None,
            'using_technical': tech_signals is not None
        }
    except Exception as e:
        logger.error(f"Error calculating prediction: {str(e)}")
        logger.exception("Prediction calculation error")
        return {
            'predicted_price': current_price,  # Default to current price
            'target_date': (current_time + timedelta(days=days)).isoformat(),
            'sentiment_factor': 0,
            'ai_sentiment_factor': None,
            'technical_factor': 0,
            'direction': 'neutral',
            'confidence': 0.3,  # Low confidence
            'using_ai': False,
            'using_technical': False
        }

def store_prediction(
    symbol: str,
    current_price: float,
    predicted_price: float,
    prediction_date,
    target_date,
    sentiment_score: float,
    ai_sentiment_score: Optional[float]
):
    """Store a prediction in the database.
    
    Args:
        symbol: Cryptocurrency symbol
        current_price: Current price
        predicted_price: Predicted price
        prediction_date: Date of prediction
        target_date: Target date
        sentiment_score: Sentiment score
        ai_sentiment_score: AI sentiment score
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            INSERT INTO predictions 
            (symbol, current_price, predicted_price, prediction_date, target_date, sentiment_score, ai_sentiment_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (symbol, current_price, predicted_price, prediction_date, target_date, sentiment_score, ai_sentiment_score)
        )
        
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error storing prediction: {str(e)}")
        logger.exception("Prediction storage error") 