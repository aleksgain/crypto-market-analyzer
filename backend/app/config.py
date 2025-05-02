"""Configuration handling for the Market Analyzer API."""

import os
import logging
from typing import List

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level_dict = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
logging_level = log_level_dict.get(LOG_LEVEL, logging.INFO)

# API keys
COIN_API_KEY = os.getenv('COIN_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Database
DATABASE_URL = os.getenv('DATABASE_URL')

# Prediction intervals in days
PREDICTION_INTERVALS: List[int] = [int(x) for x in os.getenv('PREDICTION_INTERVALS', '1,7,30').split(',')]

# News categories with weights for sentiment impact
NEWS_CATEGORIES = {
    'crypto': {
        'keywords': ["bitcoin", "ethereum", "cryptocurrency", "crypto market", "blockchain"],
        'weight': 1.0  # Base weight for crypto news
    },
    'economic': {
        'keywords': ["inflation", "interest rates", "federal reserve", "recession", "stock market"],
        'weight': 0.8  # Economic news has 80% of the impact of direct crypto news
    },
    'geopolitical': {
        'keywords': ["trade war", "sanctions", "tariffs", "ukraine", "regulation"],
        'weight': 0.6  # Geopolitical news has 60% of the impact of direct crypto news
    }
}

# Cryptocurrency symbol to CoinGecko ID mapping
COIN_MAPPING = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'XRP': 'ripple',
    'LTC': 'litecoin',
    'ADA': 'cardano',
    'DOT': 'polkadot',
    'LINK': 'chainlink',
    'XLM': 'stellar',
    'DOGE': 'dogecoin',
    'UNI': 'uniswap'
}

# OpenAI rate limiting configuration
OPENAI_TOKENS_PER_MINUTE = 10
OPENAI_TOKEN_REFILL_RATE = 10/60  # Tokens added per second
OPENAI_TOKEN_BUCKET_SIZE = 10
MIN_OPENAI_REQUEST_INTERVAL = 3.0  # Seconds

# API rate limiting configuration 
COINGECKO_MIN_REQUEST_INTERVAL = 1.5  # Seconds
EVENTREGISTRY_MIN_REQUEST_INTERVAL = 5.0  # Seconds 