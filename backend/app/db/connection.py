"""Database connection handling."""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from ..config import DATABASE_URL

logger = logging.getLogger(__name__)

def get_connection():
    """Get a database connection.
    
    Returns:
        psycopg2.connection: A database connection
    
    Raises:
        Exception: If the connection fails
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def init_db():
    """Initialize database tables."""
    try:
        conn = get_connection()
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
        logger.exception("Database initialization error") 