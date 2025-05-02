# Crypto Market Analyzer

A platform for cryptocurrency market analysis leveraging AI technologies to predict price movements, analyze market sentiments, and provide real-time insights.

## Features

- **Real-time Price Tracking**: Monitor Bitcoin and Ethereum prices with live data from CoinGecko
- **AI-Powered Price Predictions**: Advanced price forecasting for different timeframes
- **Technical Analysis Indicators**: MACD, RSI, Moving Averages, and Bollinger Bands for improved prediction accuracy
- **News Sentiment Analysis**: Analyses of news articles using both NLTK and OpenAI
- **Advanced Market Insights**: AI-extracted market events, expert analysis, and on-chain trends
- **Prediction Accuracy Tracking**: Historical accuracy metrics for model evaluation
- **Interactive Dashboard**: Unified interface for all data and insights

## Architecture

This project uses a modern microservices architecture with:

- **Frontend**: React with Material UI
- **API Gateway**: Go-based service with Redis caching
- **Backend**: Flask API server with AI processing
- **Database**: PostgreSQL for data storage
- **Cache**: Redis for performance optimization

All components are containerized using Docker for easy deployment.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- API keys for:
  - CoinGecko API (for price data)
  - Event Registry API (for news)
  - OpenAI API (for AI-powered analysis)

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/aleksgain/crypto-market-analyzer.git
   cd crypto-market-analyzer
   ```

2. Run the setup script to configure your environment:
   ```
   ./setup.sh
   ```
   This will create a `.env` file with your configuration.

3. Start the application:
   ```
   docker-compose up -d
   ```

4. Access the application at http://localhost:3000

### Configuration

All sensitive configuration is stored in the `.env` file. You can use the `.env-example` as a reference.

Key configuration options:

- `LOG_LEVEL`: Controls the verbosity of logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `PREDICTION_INTERVALS`: Days for which to generate predictions (comma-separated list)
- `FLASK_ENV` and `GIN_MODE`: Controls development/production modes

#### Frontend API Configuration

The frontend uses a configuration file (`src/config.js`) to determine where to send API requests:

- In development: API requests are sent to `http://localhost:8080` (where the API Gateway runs)
- In production: API requests use relative URLs (e.g., `/api/prices`), allowing a reverse proxy to route them correctly

This ensures that the application works both in development (with separate servers) and production (behind a reverse proxy).

## API Endpoints

The system exposes several API endpoints through the API gateway:

- `/api/prices` - Current cryptocurrency prices
- `/api/news` - Latest news with sentiment analysis
- `/api/predictions` - Price predictions with technical indicators for different timeframes
- `/api/accuracy` - Historical prediction accuracy
- `/api/advanced-insights` - AI-generated market analysis

## Development

### Project Structure

```
.
├── api-gateway/        # Go API gateway with caching
├── backend/            # Python Flask backend
├── frontend/           # React frontend
├── docker-compose.yml  # Docker configuration
├── .env                # Environment variables (created by setup.sh)
└── setup.sh            # Setup script
```

### Adding Support for New Cryptocurrencies

Edit the `COIN_MAPPING` dictionary in `backend/app.py` to add new cryptocurrencies.

### Extending AI Features

The OpenAI integration can be modified by editing the prompt templates in the AI analysis functions in `backend/app.py`.

## Deploying to Production

When deploying to production, consider these important steps:

1. **CORS Configuration**: Set the `ALLOWED_ORIGINS` environment variable in your `.env` file to include your production domains:
   ```
   ALLOWED_ORIGINS=https://your-production-domain.com,https://subdomain.your-domain.com
   ```
   This will restrict API access to only the specified domains.

2. **Reverse Proxy Setup**: Configure a reverse proxy (like Nginx) in front of your services to:
   - Serve the frontend statically
   - Route API requests to the API gateway
   - Enable SSL/TLS for HTTPS

3. **Environment Variables**: Use appropriate production values in your `.env` file:
   - Set `LOG_LEVEL=INFO` or `ERROR` for production
   - Set `FLASK_ENV=production`
   - Set `GIN_MODE=release`

4. **Security**: 
   - Use strong, unique passwords for database and Redis
   - Consider using environment-specific API keys
   - Implement rate limiting for API endpoints

5. **Scaling**:
   - Increase Redis cache TTLs for better performance
   - Consider setting up database replication for high availability
   - Implement monitoring for all services

Example Nginx configuration for production:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Frontend static files
    location / {
        root /path/to/frontend/build;
        try_files $uri /index.html;
    }

    # API requests proxied to API gateway
    location /api/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- CoinGecko for cryptocurrency price data
- Event Registry for news data
- OpenAI for AI capabilities 