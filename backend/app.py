import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import json
import logging
import traceback
from datetime import datetime, timedelta
import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import psycopg2
from psycopg2.extras import RealDictCursor
import openai
import importlib
import httpx
import sys
import types
import numpy as np

# Load environment variables
load_dotenv()

# Configure logging based on environment variable
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level_dict = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
logging_level = log_level_dict.get(LOG_LEVEL, logging.INFO)

logging.basicConfig(level=logging_level, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info(f"Log level set to {LOG_LEVEL}")

app = Flask(__name__)
CORS(app)

# Configuration
COIN_API_KEY = os.getenv('COIN_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
PREDICTION_INTERVALS = [int(x) for x in os.getenv('PREDICTION_INTERVALS', '1,7,30').split(',')]
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client if API key is provided
openai_client = None
if OPENAI_API_KEY:
    try:
        # Check OpenAI version
        openai_version = importlib.metadata.version('openai')
        logger.info(f"OpenAI version: {openai_version}")
        
        # Monkey patch the SyncHttpxClientWrapper class to avoid proxies
        # This approach directly modifies the OpenAI library code to skip proxy processing
        import inspect
        import openai._base_client
        
        # Find the SyncHttpxClientWrapper class
        if hasattr(openai._base_client, 'SyncHttpxClientWrapper'):
            # Get the source code of the class init
            wrapper_class = openai._base_client.SyncHttpxClientWrapper
            
            # Override the __init__ method to avoid using proxies
            original_init = wrapper_class.__init__
            
            def patched_init(self, *args, **kwargs):
                # Remove proxies argument completely
                kwargs.pop('proxies', None)
                
                # Call original init with modified kwargs
                return original_init(self, *args, **kwargs)
                
            # Apply the monkey patch
            wrapper_class.__init__ = patched_init
            logger.info("Successfully patched SyncHttpxClientWrapper to avoid proxies")
            
        # Create OpenAI client now that we've patched the library
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Fallback method - create a dummy client that logs but doesn't call OpenAI
        logger.info("Creating fallback mock OpenAI client")
        class MockOpenAIClient:
            def __init__(self):
                self.chat = types.SimpleNamespace()
                self.chat.completions = types.SimpleNamespace()
                self.chat.completions.create = self._mock_completion
                
            def _mock_completion(self, **kwargs):
                logger.info(f"Mock OpenAI call with: {kwargs}")
                class MockResponse:
                    def __init__(self):
                        self.choices = [types.SimpleNamespace(
                            message=types.SimpleNamespace(
                                content=json.dumps({
                                    "score": 0,
                                    "explanation": "Mock OpenAI response (API client failed to initialize)"
                                })
                            )
                        )]
                return MockResponse()
                
        openai_client = MockOpenAIClient()
        logger.info("Fallback mock OpenAI client initialized")

# Define mapping for crypto symbols to CoinGecko IDs
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

# Define news topic categories with weights for sentiment impact
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

# Debug info
logger.info(f"COIN_API_KEY present: {bool(COIN_API_KEY)}")
logger.info(f"NEWS_API_KEY present: {bool(NEWS_API_KEY)}")
logger.info(f"DATABASE_URL: {DATABASE_URL}")
logger.info(f"OPENAI_API_KEY present: {bool(OPENAI_API_KEY)}")
logger.info(f"PREDICTION_INTERVALS: {PREDICTION_INTERVALS}")

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()

# Function to analyze sentiment using OpenAI
def analyze_with_openai(title, content=None, source=None):
    """
    Analyze sentiment with OpenAI, providing a more nuanced cryptocurrency impact score
    Returns: dict with score (-10 to 10 scale) and explanation
    """
    if not openai_client:
        return None
        
    try:
        # Create a prompt that includes any available content
        article_text = f"Title: {title}"
        if content:
            article_text += f"\n\nContent: {content}"
        if source:
            article_text += f"\n\nSource: {source}"
            
        # Create the system prompt that explains what we want
        system_prompt = """You are a financial analyst specializing in cryptocurrency markets.
        Analyze the news article and rate its likely impact on cryptocurrency prices on a scale from -10 (extremely negative) to +10 (extremely positive).
        Consider economic, regulatory, and technological factors in your analysis.
        Return a JSON object with two fields:
        1. 'score': A number between -10 and 10
        2. 'explanation': A brief (25 words max) explanation of your rating"""
        
        # Make the API call
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": article_text}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        
        # Validate and ensure proper format
        if 'score' not in result or 'explanation' not in result:
            logger.warning(f"Invalid OpenAI response format: {result}")
            return None
            
        return result
    except Exception as e:
        logger.error(f"Error in OpenAI sentiment analysis: {str(e)}")
        return None

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

# Initialize database tables
def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Alter news_sentiment table to include additional fields for OpenAI analysis
        try:
            cur.execute('''
            ALTER TABLE news_sentiment 
            ADD COLUMN IF NOT EXISTS category VARCHAR(50),
            ADD COLUMN IF NOT EXISTS ai_score FLOAT,
            ADD COLUMN IF NOT EXISTS ai_explanation TEXT,
            ADD COLUMN IF NOT EXISTS content TEXT
            ''')
            logger.info("Added OpenAI analysis columns to news_sentiment table")
        except Exception as e:
            logger.warning(f"Could not alter news_sentiment table: {str(e)}")
        
        # Alter predictions table to include AI sentiment score
        try:
            cur.execute('''
            ALTER TABLE predictions 
            ADD COLUMN IF NOT EXISTS ai_sentiment_score FLOAT
            ''')
            logger.info("Added AI sentiment score column to predictions table")
        except Exception as e:
            logger.warning(f"Could not alter predictions table: {str(e)}")
        
        # Create tables if they don't exist
        cur.execute('''
        CREATE TABLE IF NOT EXISTS crypto_prices (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            price FLOAT NOT NULL,
            market_cap FLOAT,
            volume_24h FLOAT,
            timestamp TIMESTAMP NOT NULL,
            UNIQUE(symbol, timestamp)
        )
        ''')
        
        cur.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            current_price FLOAT NOT NULL,
            predicted_price FLOAT NOT NULL,
            prediction_date TIMESTAMP NOT NULL,
            target_date TIMESTAMP NOT NULL,
            sentiment_score FLOAT,
            ai_sentiment_score FLOAT,
            accuracy FLOAT
        )
        ''')
        
        cur.execute('''
        CREATE TABLE IF NOT EXISTS news_sentiment (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            source VARCHAR(100) NOT NULL,
            sentiment_score FLOAT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            category VARCHAR(50),
            ai_score FLOAT,
            ai_explanation TEXT,
            content TEXT
        )
        ''')
        
        cur.close()
        conn.close()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error(traceback.format_exc())

# Initialize the database on startup
init_db()

def get_coin_id(symbol):
    """Convert a cryptocurrency symbol to its CoinGecko ID"""
    return COIN_MAPPING.get(symbol.upper(), symbol.lower())

# Helper function to categorize news articles
def categorize_news(title, content=None):
    """
    Categorize news articles into predefined categories
    Returns: tuple of (category, weight)
    """
    title_lower = title.lower()
    content_lower = content.lower() if content else ""
    text = title_lower + " " + content_lower
    
    # Check each category's keywords
    for category, info in NEWS_CATEGORIES.items():
        for keyword in info['keywords']:
            if keyword.lower() in text:
                return category, info['weight']
    
    # Default to general news with lowest weight if no category matches
    return "general", 0.3

@app.route('/api/prices', methods=['GET'])
def get_prices():
    """Get current prices for BTC and ETH"""
    symbols = request.args.get('symbols', 'BTC,ETH').split(',')
    
    try:
        result = {}
        for symbol in symbols:
            coin_id = get_coin_id(symbol)
            # Call CoinGecko API
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            if COIN_API_KEY:
                url += f"?x_cg_demo_api_key={COIN_API_KEY}"
                
            logger.info(f"Calling CoinGecko API: {url}")
            response = requests.get(url)
            
            if response.status_code != 200:
                logger.error(f"CoinGecko API error: {response.status_code} - {response.text}")
                return jsonify({'error': f"CoinGecko API returned status {response.status_code}"}), 500
                
            data = response.json()
            logger.debug(f"CoinGecko response for {symbol}: {json.dumps(data)[:200]}...")
            
            # Extract relevant data
            result[symbol] = {
                'price': data['market_data']['current_price']['usd'],
                'market_cap': data['market_data']['market_cap']['usd'],
                'volume_24h': data['market_data']['total_volume']['usd'],
                'price_change_24h': data['market_data']['price_change_percentage_24h'],
                'last_updated': data['last_updated']
            }
            
            # Store in database
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO crypto_prices (symbol, price, market_cap, volume_24h, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (symbol, result[symbol]['price'], result[symbol]['market_cap'], 
                 result[symbol]['volume_24h'], datetime.now())
            )
            cur.close()
            conn.close()
            
        return jsonify(result)
    except KeyError as e:
        logger.error(f"KeyError while processing CoinGecko response: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f"Error parsing CoinGecko API response: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Error in get_prices: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/news', methods=['GET'])
def get_news():
    """Get recent news and analyze sentiment using Event Registry instead of NewsAPI"""
    try:
        logger.info("Using Event Registry API for news retrieval")
        
        from eventregistry import EventRegistry, QueryArticlesIter, QueryItems
        
        er = EventRegistry(apiKey=NEWS_API_KEY)
        news_items = []
        
        # Track titles to avoid duplicates
        seen_titles = set()
        
        # Instead of using all keywords at once, query by category
        # This works within the 15 keyword limit per query
        for category_name, category_info in NEWS_CATEGORIES.items():
            try:
                logger.info(f"Querying for {category_name} news")
                
                # Only use keywords for this category (within limits)
                query = QueryArticlesIter(
                    keywords=QueryItems.OR(category_info['keywords']),
                    lang=["eng"],  # English articles
                    dateStart=datetime.now() - timedelta(days=7),
                    dateEnd=datetime.now(),
                    dataType=["news"]
                )
                
                # Get a few articles per category
                count = 0
                max_per_category = 7  # Adjust to get a good mix
                
                for article in query.execQuery(er, maxItems=max_per_category * 2):  # Get more to account for duplicates
                    # Extract relevant information
                    title = article.get('title', '')
                    
                    # Skip if we've seen this or a very similar title
                    # Normalize the title to help with detecting near-duplicates
                    normalized_title = ' '.join(title.lower().split())
                    
                    # Check if we already have a similar title
                    # (Similarity = 80% of words are the same, simple approach)
                    is_duplicate = False
                    for seen_title in seen_titles:
                        if similarity_score(normalized_title, seen_title) > 0.8:
                            is_duplicate = True
                            logger.debug(f"Skipping duplicate: {title}")
                            break
                            
                    if is_duplicate:
                        continue
                        
                    # Add to seen titles
                    seen_titles.add(normalized_title)
                    
                    source = article.get('source', {}).get('title', 'Unknown Source')
                    url = article.get('url', '')
                    published_at = article.get('dateTime', datetime.now().isoformat())
                    content = article.get('body', '')[:500]  # Get first 500 chars of content if available
                    
                    # Use the category we're currently querying
                    weight = category_info['weight']
                    
                    # Analyze sentiment with NLTK
                    sentiment = sia.polarity_scores(title)
                    sentiment_score = sentiment['compound'] * weight  # Apply category weight
                    
                    # Analyze with OpenAI if available
                    ai_result = None
                    ai_score = None
                    ai_explanation = None
                    if openai_client:
                        ai_result = analyze_with_openai(title, content, source)
                        if ai_result:
                            ai_score = ai_result.get('score')
                            ai_explanation = ai_result.get('explanation')
                    
                    # Store in database
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO news_sentiment 
                        (title, source, sentiment_score, timestamp, category, ai_score, ai_explanation, content)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (title, source, sentiment_score, datetime.now(), category_name, ai_score, ai_explanation, content)
                    )
                    cur.close()
                    conn.close()
                    
                    # Add to results
                    news_items.append({
                        'title': title,
                        'source': source,
                        'sentiment_score': sentiment_score,
                        'url': url,
                        'published_at': published_at,
                        'category': category_name,
                        'ai_score': ai_score,
                        'ai_explanation': ai_explanation,
                    })
                    
                    count += 1
                    if count >= max_per_category:
                        break
                
                logger.info(f"Retrieved {count} articles for category {category_name}")
                
            except Exception as category_error:
                logger.warning(f"Error retrieving {category_name} news: {str(category_error)}")
        
        # Sort by absolute AI score (if available) or sentiment score
        news_items.sort(key=lambda x: abs(x.get('ai_score', 0)) if x.get('ai_score') is not None else abs(x['sentiment_score']), reverse=True)
        
        # Take top 10 most impactful articles
        news_items = news_items[:10]
        
        if news_items:
            logger.info(f"Successfully retrieved {len(news_items)} articles from Event Registry")
            return jsonify({'news': news_items})
        else:
            # Fall back to mock data if no news could be retrieved
            logger.warning("No articles retrieved from Event Registry, using mock data")
            return use_mock_news_data()
            
    except Exception as er_error:
        # If Event Registry fails, use mock data
        logger.warning(f"Event Registry API error: {str(er_error)}")
        logger.info("Using mock news data instead")
        return use_mock_news_data()

# Separate function for mock news data to avoid code duplication
def use_mock_news_data():
    # Mock news data with varied sentiments and categories
    mock_articles = [
        {"title": "Bitcoin surges to new all-time high amid positive market sentiment", "source": "Mock Financial News", "url": "https://example.com/news/1", "publishedAt": datetime.now().isoformat(), "category": "crypto", "content": "Bitcoin reached a new all-time high today as institutional investors continue to show interest in the cryptocurrency."},
        {"title": "Ethereum upgrade expected to improve network scalability", "source": "Mock Crypto Blog", "url": "https://example.com/news/2", "publishedAt": (datetime.now() - timedelta(hours=2)).isoformat(), "category": "crypto", "content": "The upcoming Ethereum upgrade will significantly improve transaction throughput and reduce gas fees."},
        {"title": "Federal Reserve announces interest rate hike, crypto markets react", "source": "Mock Economic Times", "url": "https://example.com/news/3", "publishedAt": (datetime.now() - timedelta(hours=4)).isoformat(), "category": "economic", "content": "The Federal Reserve increased interest rates by 0.5%, causing volatility in both traditional and cryptocurrency markets."},
        {"title": "Major nation announces new cryptocurrency regulations", "source": "Mock Regulatory News", "url": "https://example.com/news/4", "publishedAt": (datetime.now() - timedelta(hours=6)).isoformat(), "category": "geopolitical", "content": "New regulations will require cryptocurrency exchanges to implement stricter KYC procedures and report large transactions."},
        {"title": "Global inflation reaches 10-year high, investors turn to Bitcoin", "source": "Mock Investment Journal", "url": "https://example.com/news/5", "publishedAt": (datetime.now() - timedelta(hours=8)).isoformat(), "category": "economic", "content": "Rising inflation has prompted investors to seek alternative stores of value, with Bitcoin seeing increased adoption."},
        {"title": "Bitcoin crashes 10% as market reacts to negative economic data", "source": "Mock Economic Times", "url": "https://example.com/news/6", "publishedAt": (datetime.now() - timedelta(hours=10)).isoformat(), "category": "crypto", "content": "Cryptocurrency markets tumbled following the release of disappointing economic indicators."},
        {"title": "Peace talks in Ukraine show promise, global markets rally", "source": "Mock World News", "url": "https://example.com/news/7", "publishedAt": (datetime.now() - timedelta(hours=12)).isoformat(), "category": "geopolitical", "content": "Progress in peace negotiations has led to optimism in financial markets, with cryptocurrencies also seeing gains."},
        {"title": "Major tech company announces Bitcoin integration", "source": "Mock Tech Journal", "url": "https://example.com/news/8", "publishedAt": (datetime.now() - timedelta(hours=14)).isoformat(), "category": "crypto", "content": "A Fortune 500 tech company will begin accepting Bitcoin as payment for its services starting next month."},
        {"title": "Financial experts warn of bubble in cryptocurrency market", "source": "Mock Financial Post", "url": "https://example.com/news/9", "publishedAt": (datetime.now() - timedelta(hours=16)).isoformat(), "category": "economic", "content": "Leading economists are cautioning investors about unsustainable price growth in the cryptocurrency sector."},
        {"title": "New tariffs announced between major economies, markets uncertain", "source": "Mock Trade Weekly", "url": "https://example.com/news/10", "publishedAt": (datetime.now() - timedelta(hours=18)).isoformat(), "category": "geopolitical", "content": "The implementation of new trade tariffs has created uncertainty in global markets, affecting risk assets including cryptocurrencies."}
    ]
    
    news_items = []
    for article in mock_articles:
        title = article['title']
        source = article['source']
        url = article['url']
        published_at = article['publishedAt']
        category = article['category']
        content = article.get('content', '')
        
        # Get the weight for this category
        weight = NEWS_CATEGORIES.get(category, {'weight': 0.3})['weight']
        
        # Analyze sentiment with NLTK
        sentiment = sia.polarity_scores(title)
        sentiment_score = sentiment['compound'] * weight
        
        # Analyze with OpenAI if available
        ai_score = None
        ai_explanation = None
        if openai_client:
            ai_result = analyze_with_openai(title, content, source)
            if ai_result:
                ai_score = ai_result.get('score')
                ai_explanation = ai_result.get('explanation')
        
        # Store in database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO news_sentiment 
            (title, source, sentiment_score, timestamp, category, ai_score, ai_explanation, content)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (title, source, sentiment_score, datetime.now(), category, ai_score, ai_explanation, content)
        )
        cur.close()
        conn.close()
        
        news_items.append({
            'title': title,
            'source': source,
            'sentiment_score': sentiment_score,
            'url': url,
            'published_at': published_at,
            'category': category,
            'ai_score': ai_score,
            'ai_explanation': ai_explanation
        })
        
    return jsonify({'news': news_items})

# Function to calculate similarity between two texts
def similarity_score(text1, text2):
    """Calculate a simple similarity score between two texts based on word overlap"""
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
        
    # Jaccard similarity
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)

# Function to get historical price data
def get_historical_prices(symbol, days=90):
    """Get historical price data for a symbol"""
    try:
        coin_id = get_coin_id(symbol)
        
        # Query historical data from the database first
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
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
        
        db_data = cur.fetchall()
        cur.close()
        conn.close()
        
        if len(db_data) >= 30:  # We need at least 30 data points for good analysis
            logger.info(f"Using historical price data from database for {symbol}")
            # Convert to list of dictionaries
            return db_data
        
        # If not enough data in DB, fetch from API
        logger.info(f"Not enough historical data in DB, fetching from CoinGecko for {symbol}")
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days
        }
        
        if COIN_API_KEY:
            params["x_cg_demo_api_key"] = COIN_API_KEY
            
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Error fetching historical data: {response.status_code} - {response.text}")
            return []
            
        data = response.json()
        
        # Format data and store in DB
        formatted_data = []
        conn = get_db_connection()
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
        logger.error(f"Error getting historical prices: {str(e)}")
        logger.error(traceback.format_exc())
        return []

# Function to calculate technical indicators
def calculate_technical_indicators(price_data, symbol):
    """Calculate technical indicators from price data"""
    try:
        # Need at least 50 data points for meaningful indicators
        if len(price_data) < 50:
            logger.warning(f"Not enough price data for {symbol} to calculate technical indicators")
            return None
            
        # Convert to pandas DataFrame
        df = pd.DataFrame(price_data)
        
        # Make sure timestamp is a datetime object and sorted
        if isinstance(df['timestamp'][0], str):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        df = df.sort_values('timestamp')
        
        # Calculate indicators
        # Simple Moving Averages
        df['SMA20'] = df['price'].rolling(window=20).mean()
        df['SMA50'] = df['price'].rolling(window=50).mean()
        
        # MACD
        df['EMA12'] = df['price'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['price'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # RSI
        delta = df['price'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['BB_middle'] = df['price'].rolling(window=20).mean()
        std_dev = df['price'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (std_dev * 2)
        df['BB_lower'] = df['BB_middle'] - (std_dev * 2)
        
        # Get latest values
        latest = df.iloc[-1].to_dict()
        
        # Generate trend signals
        sma_trend = 'bullish' if latest['SMA20'] > latest['SMA50'] else 'bearish'
        
        # MACD signal
        macd_signal = 'bullish' if latest['MACD'] > latest['MACD_signal'] else 'bearish'
        
        # MACD histogram direction (last 3 periods)
        if len(df) >= 3:
            hist_direction = 'bullish' if df['MACD_hist'].iloc[-1] > df['MACD_hist'].iloc[-2] > df['MACD_hist'].iloc[-3] else \
                            'bearish' if df['MACD_hist'].iloc[-1] < df['MACD_hist'].iloc[-2] < df['MACD_hist'].iloc[-3] else \
                            'neutral'
        else:
            hist_direction = 'neutral'
        
        # RSI signal
        if latest['RSI'] > 70:
            rsi_signal = 'overbought'
        elif latest['RSI'] < 30:
            rsi_signal = 'oversold'
        else:
            rsi_signal = 'neutral'
            
        # Bollinger Bands
        current_price = latest['price']
        bb_position = (current_price - latest['BB_lower']) / (latest['BB_upper'] - latest['BB_lower'])
        if bb_position > 0.8:
            bb_signal = 'overbought'
        elif bb_position < 0.2:
            bb_signal = 'oversold'
        else:
            bb_signal = 'neutral'
        
        # Support and resistance
        support_level = latest['BB_lower']
        resistance_level = latest['BB_upper']
        
        # Overall signal strength calculation
        bullish_signals = 0
        bearish_signals = 0
        
        # SMA trend
        if sma_trend == 'bullish':
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        # MACD signal
        if macd_signal == 'bullish':
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        # MACD histogram direction
        if hist_direction == 'bullish':
            bullish_signals += 0.5
        elif hist_direction == 'bearish':
            bearish_signals += 0.5
            
        # RSI signal
        if rsi_signal == 'oversold':
            bullish_signals += 1
        elif rsi_signal == 'overbought':
            bearish_signals += 1
            
        # Bollinger Bands signal
        if bb_signal == 'oversold':
            bullish_signals += 1
        elif bb_signal == 'overbought':
            bearish_signals += 1
            
        # Calculate overall signal and strength
        if bullish_signals > bearish_signals:
            overall_signal = 'bullish'
            signal_strength = bullish_signals / (bullish_signals + bearish_signals)
        elif bearish_signals > bullish_signals:
            overall_signal = 'bearish'
            signal_strength = bearish_signals / (bullish_signals + bearish_signals)
        else:
            overall_signal = 'neutral'
            signal_strength = 0.5
            
        # Format the result
        tech_signals = {
            'trend': {
                'sma_trend': sma_trend,
                'macd': macd_signal,
                'macd_histogram': hist_direction
            },
            'oscillators': {
                'rsi': rsi_signal,
                'bollinger': bb_signal
            },
            'levels': {
                'support': round(support_level, 2),
                'resistance': round(resistance_level, 2)
            },
            'values': {
                'rsi': round(latest['RSI'], 2),
                'macd': round(latest['MACD'], 4),
                'macd_signal': round(latest['MACD_signal'], 4),
                'sma20': round(latest['SMA20'], 2),
                'sma50': round(latest['SMA50'], 2)
            },
            'overall': {
                'signal': overall_signal,
                'strength': round(signal_strength, 2),
                'bullish_signals': bullish_signals,
                'bearish_signals': bearish_signals
            }
        }
        
        return tech_signals
        
    except Exception as e:
        logger.error(f"Error calculating technical indicators: {str(e)}")
        logger.error(traceback.format_exc())
        return None

@app.route('/api/predictions', methods=['GET'])
def get_predictions():
    """Get price predictions for specified symbols"""
    symbols = request.args.get('symbols', 'BTC,ETH').split(',')
    
    try:
        result = {}
        current_time = datetime.now()
        
        for symbol in symbols:
            coin_id = get_coin_id(symbol)
            # Get current price
            price_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            if COIN_API_KEY:
                price_url += f"?x_cg_demo_api_key={COIN_API_KEY}"
                
            logger.info(f"Calling CoinGecko API for predictions: {price_url}")
            price_response = requests.get(price_url)
            
            if price_response.status_code != 200:
                logger.error(f"CoinGecko API error: {price_response.status_code} - {price_response.text}")
                return jsonify({'error': f"CoinGecko API returned status {price_response.status_code}"}), 500
                
            price_data = price_response.json()
            current_price = price_data['market_data']['current_price']['usd']
            
            # Get average sentiment from database - include AI sentiment if available
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get traditional sentiment
            cur.execute(
                """
                SELECT AVG(sentiment_score) as avg_sentiment 
                FROM news_sentiment 
                WHERE timestamp > %s
                """,
                (current_time - timedelta(days=1),)
            )
            
            sentiment_data = cur.fetchone()
            sentiment_score = sentiment_data['avg_sentiment'] if sentiment_data and sentiment_data['avg_sentiment'] else 0
            
            # Get AI sentiment if available
            cur.execute(
                """
                SELECT AVG(ai_score) as avg_ai_sentiment 
                FROM news_sentiment 
                WHERE timestamp > %s AND ai_score IS NOT NULL
                """,
                (current_time - timedelta(days=1),)
            )
            
            ai_sentiment_data = cur.fetchone()
            ai_sentiment_score = ai_sentiment_data['avg_ai_sentiment'] if ai_sentiment_data and ai_sentiment_data['avg_ai_sentiment'] else None
            
            # Get historical prices for technical analysis
            historical_prices = get_historical_prices(symbol)
            tech_signals = calculate_technical_indicators(historical_prices, symbol)
            
            # Simple prediction model with AI sentiment and technical analysis
            predictions = {}
            for days in PREDICTION_INTERVALS:
                # Base sentiment adjustment
                if ai_sentiment_score is not None:
                    # AI sentiment is on -10 to 10 scale, normalize to -1 to 1 for consistency
                    normalized_ai_sentiment = ai_sentiment_score / 10
                    # Use a stronger factor for AI sentiment since it's more accurate
                    sentiment_adjustment = normalized_ai_sentiment * 0.15 * days/10
                    sentiment_for_prediction = normalized_ai_sentiment
                else:
                    # Fall back to traditional sentiment
                    sentiment_adjustment = sentiment_score * 0.1 * days/10
                    sentiment_for_prediction = sentiment_score
                
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
                
                target_date = current_time + timedelta(days=days)
                
                # Store prediction with sentiment and tech signals
                cur.execute(
                    """
                    INSERT INTO predictions 
                    (symbol, current_price, predicted_price, prediction_date, target_date, sentiment_score, ai_sentiment_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (symbol, current_price, predicted_price, current_time, target_date, sentiment_score, ai_sentiment_score)
                )
                
                predictions[f"{days}_day"] = {
                    'predicted_price': predicted_price,
                    'target_date': target_date.isoformat(),
                    'sentiment_factor': sentiment_score,
                    'ai_sentiment_factor': ai_sentiment_score,
                    'technical_factor': tech_adjustment,
                    'direction': direction,
                    'confidence': confidence,
                    'using_ai': ai_sentiment_score is not None,
                    'using_technical': tech_signals is not None
                }
            
            cur.close()
            conn.close()
            
            result[symbol] = {
                'current_price': current_price,
                'predictions': predictions,
                'technical_signals': tech_signals
            }
            
        return jsonify(result)
    except KeyError as e:
        logger.error(f"KeyError while processing data for predictions: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f"Error processing prediction data: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Error in get_predictions: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/accuracy', methods=['GET'])
def get_accuracy():
    """Get historical prediction accuracy"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Find predictions where target_date has passed
        cur.execute(
            """
            SELECT p.symbol, p.current_price, p.predicted_price, p.prediction_date, p.target_date,
                   cp.price as actual_price,
                   ABS(p.predicted_price - cp.price) / cp.price as error_rate,
                   p.sentiment_score, p.ai_sentiment_score
            FROM predictions p
            JOIN crypto_prices cp ON p.symbol = cp.symbol
            WHERE p.target_date < %s
            AND cp.timestamp BETWEEN p.target_date - INTERVAL '1 hour' AND p.target_date + INTERVAL '1 hour'
            ORDER BY p.target_date DESC
            LIMIT 50
            """,
            (datetime.now(),)
        )
        
        accuracy_data = cur.fetchall()
        
        # Calculate average accuracy by symbol and prediction interval
        summary = {}
        for record in accuracy_data:
            symbol = record['symbol']
            days_diff = (record['target_date'] - record['prediction_date']).days
            
            if symbol not in summary:
                summary[symbol] = {}
                
            if days_diff not in summary[symbol]:
                summary[symbol][days_diff] = {
                    'count': 0,
                    'total_error': 0,
                    'avg_error': 0,
                    'count_ai': 0,
                    'total_error_ai': 0,
                    'avg_error_ai': 0
                }
                
            summary[symbol][days_diff]['count'] += 1
            summary[symbol][days_diff]['total_error'] += record['error_rate']
            summary[symbol][days_diff]['avg_error'] = (
                summary[symbol][days_diff]['total_error'] / summary[symbol][days_diff]['count']
            )
            
            # Track AI prediction accuracy separately
            if record['ai_sentiment_score'] is not None:
                summary[symbol][days_diff]['count_ai'] += 1
                summary[symbol][days_diff]['total_error_ai'] += record['error_rate']
                summary[symbol][days_diff]['avg_error_ai'] = (
                    summary[symbol][days_diff]['total_error_ai'] / summary[symbol][days_diff]['count_ai']
                )
            
        cur.close()
        conn.close()
        
        return jsonify({
            'raw_data': accuracy_data,
            'summary': summary
        })
    except Exception as e:
        logger.error(f"Error in get_accuracy: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Route to test external API connectivity
@app.route('/api/test-connectivity', methods=['GET'])
def test_connectivity():
    results = {}
    
    # Test CoinGecko
    try:
        coingecko_url = "https://api.coingecko.com/api/v3/ping"
        logger.info(f"Testing CoinGecko connectivity: {coingecko_url}")
        cg_response = requests.get(coingecko_url, timeout=5)
        results['coingecko'] = {
            'status': cg_response.status_code,
            'response': cg_response.text,
            'working': cg_response.status_code == 200
        }
    except Exception as e:
        results['coingecko'] = {
            'status': 'error',
            'response': str(e),
            'working': False
        }
    
    # Test NewsAPI
    try:
        # Just check the status without using the actual API
        newsapi_url = "https://newsapi.org/v2/top-headlines?country=us&apiKey=" + NEWS_API_KEY
        logger.info(f"Testing NewsAPI connectivity: {newsapi_url.replace(NEWS_API_KEY, 'REDACTED')}")
        news_response = requests.get(newsapi_url, timeout=5)
        results['newsapi'] = {
            'status': news_response.status_code,
            'response': news_response.text[:100] + "...",
            'working': news_response.status_code == 200
        }
    except Exception as e:
        results['newsapi'] = {
            'status': 'error',
            'response': str(e),
            'working': False
        }
    
    # Test database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        db_result = cur.fetchone()
        cur.close()
        conn.close()
        results['database'] = {
            'status': 'success',
            'response': "Database connection successful",
            'working': True
        }
    except Exception as e:
        results['database'] = {
            'status': 'error',
            'response': str(e),
            'working': False
        }
        
    return jsonify(results)

# Detailed NewsAPI test endpoint
@app.route('/api/test-newsapi', methods=['GET'])
def test_newsapi():
    """Detailed test for NewsAPI with multiple endpoints"""
    results = {}
    
    # Try various NewsAPI endpoints
    endpoints = [
        {
            "name": "everything_endpoint",
            "url": f"https://newsapi.org/v2/everything?q=bitcoin&apiKey={NEWS_API_KEY}",
            "description": "Search everything for 'bitcoin'"
        },
        {
            "name": "top_headlines_us",
            "url": f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}",
            "description": "Top headlines in US"
        },
        {
            "name": "top_headlines_business",
            "url": f"https://newsapi.org/v2/top-headlines?category=business&apiKey={NEWS_API_KEY}",
            "description": "Business category headlines"
        },
        {
            "name": "sources",
            "url": f"https://newsapi.org/v2/top-headlines/sources?apiKey={NEWS_API_KEY}",
            "description": "Available sources"
        }
    ]
    
    for endpoint in endpoints:
        try:
            logger.info(f"Testing NewsAPI endpoint: {endpoint['name']}")
            response = requests.get(endpoint['url'], timeout=10)
            
            # Get response headers
            headers = dict(response.headers)
            
            results[endpoint['name']] = {
                "status_code": response.status_code,
                "headers": headers,
                "content": response.text[:200] + "..." if len(response.text) > 200 else response.text,
                "description": endpoint['description']
            }
        except Exception as e:
            results[endpoint['name']] = {
                "status": "error",
                "error": str(e),
                "description": endpoint['description']
            }
    
    # Add API key info (redacted for security)
    key_info = {
        "key_provided": bool(NEWS_API_KEY),
        "key_length": len(NEWS_API_KEY) if NEWS_API_KEY else 0,
        "key_prefix": NEWS_API_KEY[:4] + "..." if NEWS_API_KEY and len(NEWS_API_KEY) > 4 else "None"
    }
    
    return jsonify({
        "api_key_info": key_info,
        "endpoints_tested": results
    })

# Route to test Event Registry connectivity
@app.route('/api/test-eventregistry', methods=['GET'])
def test_eventregistry():
    """Test Event Registry API connectivity"""
    try:
        from eventregistry import EventRegistry
        er = EventRegistry(apiKey=NEWS_API_KEY)
        
        # Test getting recent articles
        test_results = {}
        
        # Test 1: Get info about the API key
        try:
            info = er.getInfo()
            test_results["api_info"] = {
                "status": "success",
                "data": info
            }
        except Exception as e:
            test_results["api_info"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test 2: Try a simple recent articles query
        try:
            from eventregistry import QueryArticlesIter
            q = QueryArticlesIter(
                keywords="bitcoin",
                dateStart=datetime.now() - timedelta(days=3),
                dateEnd=datetime.now()
            )
            
            articles = []
            for article in q.execQuery(er, maxItems=2):
                articles.append({
                    "title": article.get("title"),
                    "source": article.get("source", {}).get("title"),
                    "date": article.get("dateTime")
                })
                
            test_results["recent_articles"] = {
                "status": "success",
                "count": len(articles),
                "sample": articles
            }
        except Exception as e:
            test_results["recent_articles"] = {
                "status": "error",
                "error": str(e)
            }
            
        # API key info (redacted for security)
        key_info = {
            "key_provided": bool(NEWS_API_KEY),
            "key_length": len(NEWS_API_KEY) if NEWS_API_KEY else 0,
            "key_prefix": NEWS_API_KEY[:4] + "..." if NEWS_API_KEY and len(NEWS_API_KEY) > 4 else "None"
        }
        
        return jsonify({
            "api_key_info": key_info,
            "test_results": test_results,
        })
        
    except ImportError:
        return jsonify({
            "status": "error",
            "error": "Event Registry package not installed. Run 'pip install eventregistry'."
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# Route to test OpenAI connectivity
@app.route('/api/test-openai', methods=['GET'])
def test_openai():
    """Test OpenAI API connectivity and sentiment analysis"""
    try:
        if not openai_client:
            return jsonify({
                "status": "error",
                "error": "OpenAI API key not provided. Add OPENAI_API_KEY to your .env file."
            }), 400
        
        # Test articles with different expected sentiments
        test_articles = [
            {
                "title": "Bitcoin surges to new all-time high as institutional adoption grows",
                "expected_sentiment": "positive"
            },
            {
                "title": "Major country announces complete ban on cryptocurrency trading",
                "expected_sentiment": "negative"
            },
            {
                "title": "Federal Reserve raises interest rates by 0.75%, crypto markets tumble",
                "expected_sentiment": "negative"
            },
            {
                "title": "Peace agreement reached in Ukraine conflict, global markets rally",
                "expected_sentiment": "positive"
            }
        ]
        
        results = []
        for article in test_articles:
            # Get traditional NLTK sentiment
            nltk_sentiment = sia.polarity_scores(article["title"])
            
            # Get OpenAI sentiment
            openai_result = analyze_with_openai(article["title"])
            
            results.append({
                "title": article["title"],
                "expected_sentiment": article["expected_sentiment"],
                "nltk_sentiment": nltk_sentiment["compound"],
                "openai_sentiment": openai_result
            })
        
        return jsonify({
            "status": "success",
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error testing OpenAI: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# Function for advanced news data extraction using OpenAI
def extract_market_insights(news_items, limit=3):
    """Extract deeper market insights from news articles using OpenAI"""
    if not openai_client or not news_items:
        return []
        
    try:
        # Get the most impactful news items
        top_news = sorted(news_items, key=lambda x: abs(x.get('ai_score', 0) if x.get('ai_score') is not None 
                                            else abs(x.get('sentiment_score', 0))), reverse=True)[:limit]
        
        insights = []
        for article in top_news:
            title = article.get('title', '')
            content = article.get('content', '')
            source = article.get('source', '')
            
            # Create a prompt for OpenAI
            system_prompt = """You are a cryptocurrency market analyst extracting key insights.
            From the news article provided, extract:
            1. Market-moving events (regulatory changes, investments, partnerships)
            2. Specific predictions or forecasts mentioned
            3. Key people or organizations involved
            4. Potential impact on Bitcoin and Ethereum prices
            
            Return a JSON object with these fields:
            {
                "key_event": "Brief description of the main market-moving event",
                "entities": ["List of key companies, people, or organizations"],
                "predictions": "Any price or market predictions mentioned",
                "btc_impact": "Likely impact on Bitcoin price (-3 to +3 scale)",
                "eth_impact": "Likely impact on Ethereum price (-3 to +3 scale)",
                "confidence": "Your confidence in this analysis (1-10 scale)"
            }"""
            
            user_content = f"Title: {title}\n\nContent: {content}\n\nSource: {source}"
            
            # Make the API call
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response and add original article info
            insight = json.loads(response.choices[0].message.content)
            insight['article_title'] = title
            insight['article_source'] = source
            insights.append(insight)
            
        return insights
    except Exception as e:
        logger.error(f"Error in market insights extraction: {str(e)}")
        return []

# Function for expert knowledge modeling
def generate_market_analysis(crypto_data):
    """Generate expert market analysis for cryptocurrencies using OpenAI"""
    if not openai_client or not crypto_data:
        return None
        
    try:
        # Prepare data for OpenAI
        btc_data = crypto_data.get('BTC', {})
        eth_data = crypto_data.get('ETH', {})
        
        system_prompt = """You are a senior cryptocurrency analyst with expertise in market dynamics.
        Based on the current price data, generate a concise expert analysis with these sections:
        1. Current Market Summary (2-3 sentences)
        2. Key Support/Resistance Levels for BTC and ETH
        3. Short-term outlook (1-7 days)
        4. One technical pattern to watch for each currency
        
        Return a JSON object with these fields:
        {
            "market_summary": "Current market analysis",
            "btc_support_resistance": {"support": [price levels], "resistance": [price levels]},
            "eth_support_resistance": {"support": [price levels], "resistance": [price levels]},
            "short_term_outlook": "Outlook for next 1-7 days",
            "btc_pattern": "One technical pattern to watch for Bitcoin",
            "eth_pattern": "One technical pattern to watch for Ethereum",
            "market_sentiment": "bullish, bearish, or neutral"
        }"""
        
        # Format current price data
        user_content = f"""Current Bitcoin price: ${btc_data.get('price', 0):,.2f}
24h Change: {btc_data.get('price_change_24h', 0):.2f}%
24h Volume: ${btc_data.get('volume_24h', 0):,.2f}
Market Cap: ${btc_data.get('market_cap', 0):,.2f}

Current Ethereum price: ${eth_data.get('price', 0):,.2f}
24h Change: {eth_data.get('price_change_24h', 0):.2f}%
24h Volume: ${eth_data.get('volume_24h', 0):,.2f}
Market Cap: ${eth_data.get('market_cap', 0):,.2f}"""
        
        # Make the API call
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        analysis = json.loads(response.choices[0].message.content)
        analysis['timestamp'] = datetime.now().isoformat()
        
        return analysis
    except Exception as e:
        logger.error(f"Error in market analysis generation: {str(e)}")
        return None

# Function to analyze on-chain data (simplified version)
def analyze_onchain_trends():
    """Generate synthetic on-chain analysis using OpenAI"""
    if not openai_client:
        return None
        
    try:
        # In a real implementation, we would fetch actual on-chain data
        # For this example, we'll simulate it
        system_prompt = """You are a blockchain data analyst.
        Generate a realistic analysis of current Bitcoin and Ethereum on-chain metrics.
        
        Return a JSON object with these fields:
        {
            "btc_active_addresses": {
                "value": "Number of active addresses in the last 24h",
                "change": "Percentage change from previous period",
                "insight": "What this means for the market"
            },
            "eth_active_addresses": {
                "value": "Number of active addresses in the last 24h",
                "change": "Percentage change from previous period",
                "insight": "What this means for the market"
            },
            "btc_transaction_volume": {
                "value": "USD value transferred in last 24h",
                "change": "Percentage change from previous period",
                "insight": "What this means for the market"
            },
            "eth_transaction_volume": {
                "value": "USD value transferred in last 24h",
                "change": "Percentage change from previous period",
                "insight": "What this means for the market"
            },
            "large_wallet_movements": [
                {
                    "currency": "BTC or ETH",
                    "amount": "Amount moved",
                    "usd_value": "USD equivalent",
                    "type": "exchange_inflow, exchange_outflow, or wallet_to_wallet",
                    "significance": "Potential market impact"
                }
            ],
            "summary": "Overall insight about on-chain activity"
        }"""
        
        # Make the API call
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate realistic on-chain data analysis for current market conditions"}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        analysis = json.loads(response.choices[0].message.content)
        analysis['timestamp'] = datetime.now().isoformat()
        
        return analysis
    except Exception as e:
        logger.error(f"Error in on-chain analysis: {str(e)}")
        return None

# New API endpoint for advanced insights
@app.route('/api/advanced-insights', methods=['GET'])
def get_advanced_insights():
    """Get advanced market insights using OpenAI"""
    try:
        # Get crypto price data
        crypto_prices = {}
        for symbol in ['BTC', 'ETH']:
            coin_id = get_coin_id(symbol)
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            if COIN_API_KEY:
                url += f"?x_cg_demo_api_key={COIN_API_KEY}"
                
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                crypto_prices[symbol] = {
                    'price': data['market_data']['current_price']['usd'],
                    'market_cap': data['market_data']['market_cap']['usd'],
                    'volume_24h': data['market_data']['total_volume']['usd'],
                    'price_change_24h': data['market_data']['price_change_percentage_24h'],
                }
        
        # Get recent news for market insights
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT title, source, sentiment_score, ai_score, content, category
            FROM news_sentiment
            WHERE timestamp > %s
            ORDER BY timestamp DESC
            LIMIT 10
            """,
            (datetime.now() - timedelta(days=1),)
        )
        
        recent_news = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert DB rows to list of dicts
        news_items = [{key: item[key] for key in item.keys()} for item in recent_news]
        
        # Generate all insights
        market_insights = extract_market_insights(news_items)
        expert_analysis = generate_market_analysis(crypto_prices)
        onchain_analysis = analyze_onchain_trends()
        
        return jsonify({
            'market_insights': market_insights,
            'expert_analysis': expert_analysis,
            'onchain_analysis': onchain_analysis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating advanced insights: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 