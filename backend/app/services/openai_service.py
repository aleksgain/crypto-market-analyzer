"""OpenAI service for sentiment analysis and insights."""

import json
import logging
import threading
import openai
import importlib
import httpx

from ..config import OPENAI_API_KEY, OPENAI_TOKEN_BUCKET_SIZE, OPENAI_TOKENS_PER_MINUTE, MIN_OPENAI_REQUEST_INTERVAL
from ..utils.rate_limiting import RateLimitedAPIClient, QueuedWorker

logger = logging.getLogger(__name__)

# OpenAI client instance
openai_client = None

# Rate limiter for OpenAI API
openai_rate_limiter = RateLimitedAPIClient(
    name="OpenAI",
    min_request_interval=MIN_OPENAI_REQUEST_INTERVAL,
    tokens_per_minute=OPENAI_TOKENS_PER_MINUTE,
    max_tokens=OPENAI_TOKEN_BUCKET_SIZE
)

# Worker for OpenAI requests
openai_worker = QueuedWorker(
    name="OpenAI",
    thread_count=1,
    rate_limiter=openai_rate_limiter
)

def init_openai_client():
    """Initialize the OpenAI client."""
    global openai_client
    
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key not provided")
        return None
        
    try:
        # Check OpenAI version
        openai_version = importlib.metadata.version('openai')
        logger.info(f"OpenAI version: {openai_version}")
        
        # Monkey patch to disable proxy and retry handling
        disable_openai_retries()
        
        # Create OpenAI client
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully")
        
        return openai_client
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        logger.exception("OpenAI initialization error")
        return None

def disable_openai_retries():
    """Disable OpenAI SDK's internal retry mechanism."""
    try:
        import openai._client
        if hasattr(openai._client, "DEFAULT_MAX_RETRIES"):
            openai._client.DEFAULT_MAX_RETRIES = 0
            logger.info("Disabled OpenAI internal retries")
        
        # Set the httpx client to not retry
        try:
            # For OpenAI v1.6.0+, we need a different approach
            # Simply disable the max_retries in the client
            from openai import OpenAI
            original_init = OpenAI.__init__
            
            def patched_init(self, *args, **kwargs):
                # Remove proxies keyword if it exists
                if 'proxies' in kwargs:
                    del kwargs['proxies']
                # Set max_retries to 0
                kwargs['max_retries'] = 0
                return original_init(self, *args, **kwargs)
                
            OpenAI.__init__ = patched_init
            logger.info("Patched OpenAI client to disable retries")
            
        except Exception as e:
            logger.warning(f"Could not patch OpenAI client: {str(e)}")
            
    except Exception as e:
        logger.warning(f"Could not disable OpenAI internal retries: {str(e)}")

def call_openai_async(
    messages, 
    model="gpt-3.5-turbo", 
    response_format={"type": "json_object"},
    callback=None
):
    """Queue an OpenAI request to be processed asynchronously.
    
    Args:
        messages: List of message objects
        model: Model to use
        response_format: Format for the response
        callback: Function to call with the result
    """
    if not openai_client:
        if callback:
            callback(None)
        return
    
    # Define the function to execute
    def execute_openai_request():
        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=messages,
                response_format=response_format
            )
            return response
        except Exception as e:
            logger.error(f"Error in OpenAI request: {str(e)}")
            return None
    
    # Enqueue the request
    openai_worker.enqueue(execute_openai_request, callback=callback)

def call_openai_sync(
    messages, 
    model="gpt-3.5-turbo", 
    response_format={"type": "json_object"},
    timeout=60.0
):
    """Make a synchronous OpenAI API call with rate limiting.
    
    Args:
        messages: List of message objects
        model: Model to use
        response_format: Format for the response
        timeout: Maximum time to wait for a response
        
    Returns:
        OpenAI response or None if it failed
    """
    if not openai_client:
        logger.warning("OpenAI client not available")
        return None
    
    # Create an event to wait for the result
    result_event = threading.Event()
    result_container = []
    
    def callback(response):
        result_container.append(response)
        result_event.set()
    
    # Call the async version
    call_openai_async(messages, model, response_format, callback)
    
    # Wait for the result
    if result_event.wait(timeout=timeout):
        return result_container[0] if result_container else None
    else:
        logger.error("Timeout waiting for OpenAI API response")
        return None

def analyze_sentiment(title, content=None, source=None):
    """Analyze sentiment of a news article using OpenAI.
    
    Args:
        title: Article title
        content: Optional article content
        source: Optional article source
        
    Returns:
        dict: Sentiment analysis result or None if it failed
    """
    if not openai_client:
        return None
    
    try:
        # Create the prompt
        article_text = f"Title: {title}"
        if content:
            article_text += f"\n\nContent: {content}"
        if source:
            article_text += f"\n\nSource: {source}"
            
        # System prompt
        system_prompt = """You are a financial analyst specializing in cryptocurrency markets.
        Analyze the news article and rate its likely impact on cryptocurrency prices on a scale from -10 (extremely negative) to +10 (extremely positive).
        Consider economic, regulatory, and technological factors in your analysis.
        Return a JSON object with two fields:
        1. 'score': A number between -10 and 10
        2. 'explanation': A brief (25 words max) explanation of your rating"""
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": article_text}
        ]
        
        # Make the API call
        response = call_openai_sync(messages)
        
        if not response:
            logger.warning("OpenAI sentiment analysis failed")
            return None
            
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        
        # Validate
        if 'score' not in result or 'explanation' not in result:
            logger.warning(f"Invalid OpenAI response format: {result}")
            return None
            
        return result
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        logger.exception("Sentiment analysis error")
        return None

def extract_market_insights(news_items, limit=3):
    """Extract deeper market insights from news articles.
    
    Args:
        news_items: List of news items
        limit: Maximum number of insights to extract
        
    Returns:
        list: List of market insights
    """
    if not openai_client or not news_items:
        return []
        
    try:
        # Get the most impactful news items
        top_news = sorted(
            news_items, 
            key=lambda x: abs(x.get('ai_score', 0) if x.get('ai_score') is not None 
                             else abs(x.get('sentiment_score', 0))), 
            reverse=True
        )[:limit]
        
        insights = []
        for article in top_news:
            title = article.get('title', '')
            content = article.get('content', '')
            source = article.get('source', '')
            
            # System prompt
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
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            # Make the API call
            response = call_openai_sync(messages)
            
            if not response:
                continue
                
            # Parse the response
            insight = json.loads(response.choices[0].message.content)
            insight['article_title'] = title
            insight['article_source'] = source
            insights.append(insight)
            
        return insights
    except Exception as e:
        logger.error(f"Error extracting market insights: {str(e)}")
        logger.exception("Market insights extraction error")
        return []

def generate_market_analysis(crypto_data):
    """Generate expert market analysis for cryptocurrencies.
    
    Args:
        crypto_data: Dictionary of cryptocurrency data
        
    Returns:
        dict: Market analysis or None if it failed
    """
    if not openai_client or not crypto_data:
        return None
        
    try:
        # Get data for BTC and ETH
        btc_data = crypto_data.get('BTC', {})
        eth_data = crypto_data.get('ETH', {})
        
        # System prompt
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

        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # Make the API call
        response = call_openai_sync(messages)
        
        if not response:
            return None
            
        # Parse the response
        analysis = json.loads(response.choices[0].message.content)
        
        return analysis
    except Exception as e:
        logger.error(f"Error generating market analysis: {str(e)}")
        logger.exception("Market analysis error")
        return None

# Initialize the OpenAI client
init_openai_client() 