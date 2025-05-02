"""News service for Event Registry API integration."""

import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ..config import NEWS_API_KEY, NEWS_CATEGORIES, EVENTREGISTRY_MIN_REQUEST_INTERVAL
from ..utils.rate_limiting import RateLimitedAPIClient
from ..utils.datetime_utils import get_utc_now, ensure_timezone
from ..db.connection import get_connection
from ..services.openai_service import analyze_sentiment

logger = logging.getLogger(__name__)

# Rate limiter for Event Registry API
eventregistry_rate_limiter = RateLimitedAPIClient(
    name="EventRegistry",
    min_request_interval=EVENTREGISTRY_MIN_REQUEST_INTERVAL,
    tokens_per_minute=30,  # Adjusted to be conservative
    max_tokens=5
)

def get_recent_news(limit: int = 10) -> Dict[str, Any]:
    """Get recent news articles with sentiment analysis.
    
    Args:
        limit: Maximum number of articles to return
        
    Returns:
        dict: Dictionary with news articles
    """
    try:
        logger.info("Using Event Registry API for news retrieval")
        
        # Lazy import to avoid loading Event Registry module if not used
        try:
            from eventregistry import EventRegistry, QueryArticlesIter, QueryItems
        except ImportError:
            logger.error("EventRegistry package not installed")
            return use_mock_news_data()
        
        # Initialize Event Registry client
        er = EventRegistry(apiKey=NEWS_API_KEY)
        news_items = []
        
        # Track titles to avoid duplicates
        seen_titles = set()
        
        # Keep track of any errors to determine if we should fall back to mock data
        category_errors = 0
        
        # Process each news category
        categories = list(NEWS_CATEGORIES.items())
        for i, (category_name, category_info) in enumerate(categories):
            try:
                logger.info(f"Querying for {category_name} news")
                
                # Make sure both dates are timezone-aware to avoid the offset error
                now = get_utc_now()
                two_days_ago = now - timedelta(days=2)
                
                # Only use keywords for this category (within limits)
                query = QueryArticlesIter(
                    keywords=QueryItems.OR(category_info['keywords']),
                    lang=["eng"],  # English articles
                    dateStart=two_days_ago,
                    dateEnd=now,
                    dataType=["news"]
                )
                
                # Add rate limiting between category queries
                if i > 0:  
                    # Sleep between categories to avoid rate limiting
                    sleep_time = random.uniform(3, 6)  # Longer sleep between categories
                    logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds between category queries")
                    time.sleep(sleep_time)
                
                # Execute query with rate limiting
                articles = execute_event_registry_query(er, query)
                
                if not articles:
                    logger.warning(f"No articles found for category {category_name} after retries")
                    category_errors += 1
                    continue
                
                # Process retrieved articles
                count = 0
                max_per_category = 7
                
                for article in articles:
                    # Extract relevant information
                    title = article.get('title', '')
                    
                    # Skip if empty title
                    if not title:
                        continue
                    
                    # Skip if we've seen this or a very similar title
                    # Normalize the title to help with detecting near-duplicates
                    normalized_title = ' '.join(title.lower().split())
                    
                    # Check if we already have a similar title
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
                    
                    # Handle published_at datetime to ensure it's properly formatted
                    published_at = format_article_datetime(article.get('dateTime'))
                    
                    # Get article content, limited to 500 chars
                    content = article.get('body', '')[:500]
                    
                    # Use the category weight
                    weight = category_info['weight']
                    
                    # Get sentiment scores
                    sentiment_data = analyze_article_sentiment(title, content, source, weight)
                    sentiment_score = sentiment_data['sentiment_score']
                    ai_score = sentiment_data['ai_score']
                    ai_explanation = sentiment_data['ai_explanation']
                    
                    # Store in database
                    store_article_in_db(
                        title, source, sentiment_score, category_name, 
                        ai_score, ai_explanation, content
                    )
                    
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
                logger.exception(f"Category error: {category_name}")
                category_errors += 1
        
        # Only fall back to mock data if we've had errors for ALL categories or no news items
        if category_errors >= len(categories) or not news_items:
            logger.warning("All categories failed or no news items retrieved, using mock data")
            return use_mock_news_data()
        
        # Sort news items by relevance and recency
        sorted_news = sort_news_by_relevance(news_items)
        
        # Take top N most impactful articles
        limited_news = sorted_news[:limit]
        
        logger.info(f"Successfully retrieved {len(limited_news)} articles from Event Registry")
        return {'news': limited_news}
            
    except Exception as er_error:
        # If Event Registry fails completely, use mock data
        logger.warning(f"Complete Event Registry API failure: {str(er_error)}")
        logger.exception("Event Registry failure")
        return use_mock_news_data()

def execute_event_registry_query(er, query, max_items=15):
    """Execute Event Registry query with rate limiting.
    
    Args:
        er: EventRegistry client
        query: Query to execute
        max_items: Maximum number of items to retrieve
        
    Returns:
        list: List of articles or None if failed
    """
    def execute_query():
        # Get articles
        articles = []
        for article in query.execQuery(er, maxItems=max_items):
            articles.append(article)
        return articles
    
    # Execute with rate limiting
    return eventregistry_rate_limiter.execute(
        execute_query,
        max_retries=3,
        initial_backoff=2.0
    )

def format_article_datetime(article_datetime) -> str:
    """Format article datetime for consistent usage.
    
    Args:
        article_datetime: Datetime from article
        
    Returns:
        str: Formatted datetime string
    """
    try:
        if article_datetime:
            # If it's a string, ensure it has timezone info before parsing
            if isinstance(article_datetime, str):
                if 'Z' not in article_datetime and '+' not in article_datetime and '-' not in article_datetime[-6:]:
                    article_datetime = f"{article_datetime}Z"  # Assume UTC if no timezone
                return article_datetime
            else:
                # Already a datetime, ensure it has timezone
                return article_datetime.isoformat() if hasattr(article_datetime, 'isoformat') else get_utc_now().isoformat()
        else:
            # Default to current time with timezone
            return get_utc_now().isoformat()
    except Exception as e:
        logger.error(f"Error formatting article datetime: {str(e)}")
        return get_utc_now().isoformat()

def analyze_article_sentiment(title, content, source, weight):
    """Analyze article sentiment using NLTK and OpenAI.
    
    Args:
        title: Article title
        content: Article content
        source: Article source
        weight: Category weight
        
    Returns:
        dict: Sentiment scores
    """
    try:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        
        # Analyze sentiment with NLTK
        sentiment = sia.polarity_scores(title)
        sentiment_score = sentiment['compound'] * weight
        
        # Analyze with OpenAI if available - but continue even if it fails
        ai_score = None
        ai_explanation = None
        
        ai_result = analyze_sentiment(title, content, source)
        if ai_result:
            ai_score = ai_result.get('score')
            ai_explanation = ai_result.get('explanation')
            
        return {
            'sentiment_score': sentiment_score,
            'ai_score': ai_score,
            'ai_explanation': ai_explanation,
        }
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        logger.exception("Sentiment analysis error")
        return {
            'sentiment_score': 0,
            'ai_score': None,
            'ai_explanation': None,
        }

def store_article_in_db(title, source, sentiment_score, category, ai_score, ai_explanation, content):
    """Store article in database.
    
    Args:
        title: Article title
        source: Article source
        sentiment_score: NLTK sentiment score
        category: Article category
        ai_score: OpenAI sentiment score
        ai_explanation: OpenAI sentiment explanation
        content: Article content
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO news_sentiment 
            (title, source, sentiment_score, timestamp, category, ai_score, ai_explanation, content)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (title, source, sentiment_score, get_utc_now(), category, ai_score, ai_explanation, content)
        )
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error storing article in database: {str(e)}")
        logger.exception("Database storage error")

def sort_news_by_relevance(news_items):
    """Sort news items by relevance and recency.
    
    Args:
        news_items: List of news items
        
    Returns:
        list: Sorted news items
    """
    try:
        # Sort by recency and sentiment impact
        def sort_key(item):
            # Parse published date - convert to datetime if it's a string
            if isinstance(item.get('published_at'), str):
                try:
                    # Ensure the string has timezone info before parsing
                    pub_date_str = item.get('published_at')
                    if 'Z' not in pub_date_str and '+' not in pub_date_str and '-' not in pub_date_str[-6:]:
                        pub_date_str = f"{pub_date_str}Z"  # Assume UTC if no timezone
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                except ValueError:
                    # Fallback if date parsing fails
                    pub_date = get_utc_now() - timedelta(days=7)
            else:
                pub_date = get_utc_now() - timedelta(days=7)
                
            # Ensure both datetimes have timezone information
            pub_date = ensure_timezone(pub_date)
            now = get_utc_now()
                
            # Calculate recency score (0-1) where 1 is most recent
            # Maps a 2-day range to 0-1 value
            time_diff = now - pub_date
            recency_score = max(0, 1 - (time_diff.total_seconds() / (2 * 24 * 60 * 60)))
            
            # Weight recency at 70%, sentiment at 30%
            if item.get('ai_score') is not None:
                sentiment_magnitude = abs(item.get('ai_score', 0))
            else:
                sentiment_magnitude = abs(item['sentiment_score'])
            
            # Combined score = 70% recency + 30% sentiment magnitude
            combined_score = (recency_score * 0.7) + (sentiment_magnitude * 0.3 / 10)  # Normalize sentiment to 0-1 range
            
            return combined_score
            
        return sorted(news_items, key=sort_key, reverse=True)
    except Exception as e:
        logger.error(f"Error sorting news: {str(e)}")
        logger.exception("News sorting error")
        return news_items

def similarity_score(text1, text2):
    """Calculate a simple similarity score between two texts based on word overlap.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        float: Similarity score (0-1)
    """
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
        
    # Jaccard similarity
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)

def use_mock_news_data():
    """Generate mock news data when real API fails.
    
    Returns:
        dict: Dictionary with mock news articles
    """
    try:
        # Current time for recent mock dates
        now = get_utc_now()
        
        # Mock news data with varied sentiments and categories - using recent timestamps
        mock_articles = [
            {"title": "Bitcoin surges to new all-time high amid positive market sentiment", "source": "Mock Financial News", "url": "https://example.com/news/1", "publishedAt": now.isoformat(), "category": "crypto", "content": "Bitcoin reached a new all-time high today as institutional investors continue to show interest in the cryptocurrency."},
            {"title": "Ethereum upgrade expected to improve network scalability", "source": "Mock Crypto Blog", "url": "https://example.com/news/2", "publishedAt": (now - timedelta(hours=2)).isoformat(), "category": "crypto", "content": "The upcoming Ethereum upgrade will significantly improve transaction throughput and reduce gas fees."},
            {"title": "Federal Reserve announces interest rate hike, crypto markets react", "source": "Mock Economic Times", "url": "https://example.com/news/3", "publishedAt": (now - timedelta(hours=4)).isoformat(), "category": "economic", "content": "The Federal Reserve increased interest rates by 0.5%, causing volatility in both traditional and cryptocurrency markets."},
            {"title": "Major nation announces new cryptocurrency regulations", "source": "Mock Regulatory News", "url": "https://example.com/news/4", "publishedAt": (now - timedelta(hours=6)).isoformat(), "category": "geopolitical", "content": "New regulations will require cryptocurrency exchanges to implement stricter KYC procedures and report large transactions."},
            {"title": "Global inflation reaches 10-year high, investors turn to Bitcoin", "source": "Mock Investment Journal", "url": "https://example.com/news/5", "publishedAt": (now - timedelta(hours=8)).isoformat(), "category": "economic", "content": "Rising inflation has prompted investors to seek alternative stores of value, with Bitcoin seeing increased adoption."},
            {"title": "Bitcoin crashes 10% as market reacts to negative economic data", "source": "Mock Economic Times", "url": "https://example.com/news/6", "publishedAt": (now - timedelta(hours=10)).isoformat(), "category": "crypto", "content": "Cryptocurrency markets tumbled following the release of disappointing economic indicators."},
            {"title": "Peace talks in Ukraine show promise, global markets rally", "source": "Mock World News", "url": "https://example.com/news/7", "publishedAt": (now - timedelta(hours=12)).isoformat(), "category": "geopolitical", "content": "Progress in peace negotiations has led to optimism in financial markets, with cryptocurrencies also seeing gains."},
            {"title": "Major tech company announces Bitcoin integration", "source": "Mock Tech Journal", "url": "https://example.com/news/8", "publishedAt": (now - timedelta(hours=14)).isoformat(), "category": "crypto", "content": "A Fortune 500 tech company will begin accepting Bitcoin as payment for its services starting next month."},
            {"title": "Financial experts warn of bubble in cryptocurrency market", "source": "Mock Financial Post", "url": "https://example.com/news/9", "publishedAt": (now - timedelta(hours=16)).isoformat(), "category": "economic", "content": "Leading economists are cautioning investors about unsustainable price growth in the cryptocurrency sector."},
            {"title": "New tariffs announced between major economies, markets uncertain", "source": "Mock Trade Weekly", "url": "https://example.com/news/10", "publishedAt": (now - timedelta(hours=18)).isoformat(), "category": "geopolitical", "content": "The implementation of new trade tariffs has created uncertainty in global markets, affecting risk assets including cryptocurrencies."}
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
            
            # Get sentiment scores
            sentiment_data = analyze_article_sentiment(title, content, source, weight)
            sentiment_score = sentiment_data['sentiment_score']
            ai_score = sentiment_data['ai_score']
            ai_explanation = sentiment_data['ai_explanation']
            
            # Store in database
            store_article_in_db(
                title, source, sentiment_score, category, 
                ai_score, ai_explanation, content
            )
            
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
            
        return {'news': news_items}
    except Exception as e:
        logger.error(f"Error creating mock news data: {str(e)}")
        logger.exception("Mock news error")
        return {'news': []} 