# Market Analyzer Backend

This is the backend API for the Market Analyzer project. It provides cryptocurrency price data, news, predictions, and technical analysis.

## Project Structure

The codebase is organized into a modular structure:

```
backend/
├── app.py                   # Legacy entry point (will be removed)
├── run.py                   # Main application entry point
├── app/                     # Main package
│   ├── __init__.py
│   ├── config.py            # Configuration handling
│   ├── api/                 # API endpoints
│   │   ├── __init__.py
│   │   ├── routes.py        # Route registration
│   │   ├── endpoints/       # Individual endpoint definitions
│   │   │   ├── __init__.py
│   │   │   ├── prices.py
│   │   │   ├── news.py
│   │   │   ├── predictions.py
│   │   │   ├── accuracy.py
│   │   │   ├── insights.py
│   │   │   └── test.py
│   ├── services/            # Business logic and external services
│   │   ├── __init__.py
│   │   ├── coin_service.py  # CoinGecko API service
│   │   ├── news_service.py  # Event Registry API service
│   │   ├── openai_service.py # OpenAI integration
│   │   └── technical_analysis.py # Technical analysis
│   ├── db/                  # Database operations
│   │   ├── __init__.py
│   │   └── connection.py    # Database connection handling
│   └── utils/               # Utility functions
│       ├── __init__.py
│       ├── datetime_utils.py # DateTime utilities
│       └── rate_limiting.py  # Rate limiting utilities
```

## Features

- Cryptocurrency price data from CoinGecko API
- News sentiment analysis using EventRegistry API and OpenAI
- Price predictions based on machine learning, sentiment, and technical analysis
- Historical accuracy tracking
- Advanced market insights using OpenAI

## Rate Limiting

The application implements sophisticated rate limiting for all external APIs:

- Token bucket algorithm for limiting request rates
- Queued worker system for managing API requests
- Automatic retry with exponential backoff
- Configurable limits for each API

## Technical Notes

- Written in Python/Flask
- PostgreSQL database for data storage
- OpenAI API for sentiment analysis and market insights
- Event Registry API for news data
- CoinGecko API for cryptocurrency price data

## Environment Variables

- `COIN_API_KEY`: API key for CoinGecko API
- `NEWS_API_KEY`: API key for Event Registry API
- `OPENAI_API_KEY`: API key for OpenAI API
- `DATABASE_URL`: PostgreSQL connection string
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `PREDICTION_INTERVALS`: Comma-separated list of prediction intervals in days

## Running the Application

1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables (or create a `.env` file)
3. Run the application: `python run.py` 