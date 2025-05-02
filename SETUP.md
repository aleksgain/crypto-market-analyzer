# Setting Up Crypto Predictor

Follow these steps to get the Crypto Predictor application running:

## 1. Create the .env file

Run the setup script:

```bash
./setup.sh
```

This will create a `.env` file with placeholder API keys.

## 2. Get API Keys

1. **CoinGecko API Key**: 
   - Register at https://www.coingecko.com/en/api/pricing
   - A free tier is available but has rate limits

2. **NewsAPI Key**:
   - Register at https://newsapi.org/
   - The free tier allows 100 requests per day

## 3. Update .env file

Open the `.env` file and replace the placeholder values with your actual API keys:

```
COIN_API_KEY=your_actual_coingecko_key
NEWS_API_KEY=your_actual_newsapi_key
```

## 4. Build and run with Docker

```bash
docker-compose up --build
```

## 5. Access the application

Once the containers are running, you can access:

- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## Troubleshooting

### API Rate Limits

Both CoinGecko and NewsAPI have rate limits on their free tiers. If you see errors about too many requests, you'll need to wait before making more requests.

### Database Issues

If you encounter database connection issues, you can reset the database by removing the Docker volume:

```bash
docker-compose down
docker volume rm market_analyzer_postgres_data
docker-compose up
``` 