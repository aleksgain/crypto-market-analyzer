"""CoinGecko service for cryptocurrency price data."""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from ..config import COIN_API_KEY, COIN_MAPPING, COINGECKO_MIN_REQUEST_INTERVAL
from ..utils.rate_limiting import RateLimitedAPIClient
from ..db.connection import get_connection
from ..utils.datetime_utils import get_utc_now

logger = logging.getLogger(__name__)

# Rate limiter for CoinGecko API
coingecko_rate_limiter = RateLimitedAPIClient(
    name="CoinGecko",
    min_request_interval=COINGECKO_MIN_REQUEST_INTERVAL,
    tokens_per_minute=50,  # CoinGecko allows 50 calls per minute
    max_tokens=10
)

def get_coin_id(symbol: str) -> str:
    """Convert a cryptocurrency symbol to its CoinGecko ID.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., BTC)
        
    Returns:
        str: CoinGecko ID for the symbol
    """
    return COIN_MAPPING.get(symbol.upper(), symbol.lower())

def get_current_prices(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get current prices for the given symbols.
    
    Args:
        symbols: List of cryptocurrency symbols
        
    Returns:
        dict: Dictionary of price data by symbol
    """
    result = {}
    
    for symbol in symbols:
        try:
            # Get coin ID
            coin_id = get_coin_id(symbol)
            
            # Construct URL
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            if COIN_API_KEY:
                url += f"?x_cg_demo_api_key={COIN_API_KEY}"
                
            # Execute request with rate limiting
            def fetch_price_data():
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    logger.error(f"CoinGecko API error: {response.status_code} - {response.text}")
                    return None
                return response.json()
                
            data = coingecko_rate_limiter.execute(fetch_price_data)
            
            if not data:
                logger.error(f"Failed to get price data for {symbol}")
                continue
                
            # Extract relevant data
            result[symbol] = {
                'price': data['market_data']['current_price']['usd'],
                'market_cap': data['market_data']['market_cap']['usd'],
                'volume_24h': data['market_data']['total_volume']['usd'],
                'price_change_24h': data['market_data']['price_change_percentage_24h'],
                'last_updated': data['last_updated']
            }
            
            # Store in database
            store_price_data(
                symbol,
                result[symbol]['price'],
                result[symbol]['market_cap'],
                result[symbol]['volume_24h']
            )
            
        except Exception as e:
            logger.error(f"Error getting price data for {symbol}: {str(e)}")
            logger.exception(f"Price data error for {symbol}")
    
    return result

def store_price_data(symbol: str, price: float, market_cap: float, volume_24h: float):
    """Store price data in the database.
    
    Args:
        symbol: Cryptocurrency symbol
        price: Current price
        market_cap: Market capitalization
        volume_24h: 24-hour trading volume
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO crypto_prices (symbol, price, market_cap, volume_24h, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (symbol, price, market_cap, volume_24h, get_utc_now())
        )
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error storing price data: {str(e)}")
        logger.exception("Price data storage error")

def get_historical_prices(
    symbol: str, 
    days: int = 90
) -> List[Dict[str, Any]]:
    """Get historical price data for a symbol.
    
    Args:
        symbol: Cryptocurrency symbol
        days: Number of days of historical data
        
    Returns:
        list: List of historical price data points
    """
    try:
        # Try to get from database first
        db_data = get_historical_prices_from_db(symbol, days)
        if len(db_data) >= 30:  # Need at least 30 data points for good analysis
            logger.info(f"Using historical price data from database for {symbol}")
            return db_data
        
        # If not enough data in DB, fetch from API
        logger.info(f"Not enough historical data in DB, fetching from CoinGecko for {symbol}")
        
        # Get coin ID
        coin_id = get_coin_id(symbol)
        
        # Construct URL and parameters
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days
        }
        
        if COIN_API_KEY:
            params["x_cg_demo_api_key"] = COIN_API_KEY
            
        # Execute request with rate limiting
        def fetch_historical_data():
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                logger.error(f"Error fetching historical data: {response.status_code} - {response.text}")
                return None
            return response.json()
            
        data = coingecko_rate_limiter.execute(fetch_historical_data)
        
        if not data:
            logger.error(f"Failed to get historical data for {symbol}")
            return []
            
        # Format and store in DB
        return process_and_store_historical_data(symbol, data)
        
    except Exception as e:
        logger.error(f"Error getting historical prices for {symbol}: {str(e)}")
        logger.exception(f"Historical price error for {symbol}")
        return []

def get_historical_prices_from_db(
    symbol: str, 
    days: int
) -> List[Dict[str, Any]]:
    """Get historical price data from the database.
    
    Args:
        symbol: Cryptocurrency symbol
        days: Number of days of historical data
        
    Returns:
        list: List of historical price data points
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT timestamp, price 
            FROM crypto_prices 
            WHERE symbol = %s 
            ORDER BY timestamp DESC 
            LIMIT %s
            """,
            (symbol, days)
        )
        
        # Convert to list of dictionaries
        result = []
        for row in cur.fetchall():
            result.append({
                "timestamp": row[0],
                "price": row[1]
            })
            
        cur.close()
        conn.close()
        
        return result
    except Exception as e:
        logger.error(f"Error getting historical prices from DB: {str(e)}")
        logger.exception("DB historical price error")
        return []

def process_and_store_historical_data(
    symbol: str, 
    data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Process and store historical price data.
    
    Args:
        symbol: Cryptocurrency symbol
        data: Historical price data from CoinGecko
        
    Returns:
        list: Processed historical price data
    """
    try:
        # Format data
        formatted_data = []
        conn = get_connection()
        cur = conn.cursor()
        
        for timestamp, price in data['prices']:
            # Convert timestamp (milliseconds) to datetime
            dt = datetime.fromtimestamp(timestamp / 1000)
            
            # Store in DB
            cur.execute(
                """
                INSERT INTO crypto_prices (symbol, price, timestamp) 
                VALUES (%s, %s, %s)
                ON CONFLICT (symbol, timestamp) DO NOTHING
                """,
                (symbol, price, dt)
            )
            
            formatted_data.append({"timestamp": dt, "price": price})
        
        conn.commit()
        cur.close()
        conn.close()
        
        return formatted_data
    except Exception as e:
        logger.error(f"Error processing historical data: {str(e)}")
        logger.exception("Historical data processing error")
        return [] 