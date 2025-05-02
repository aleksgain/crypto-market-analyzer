#!/bin/bash

# Crypto Market Analyzer Setup Script

# Set text colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Crypto Market Analyzer - Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if .env file exists
if [ -f .env ]; then
    echo -e "${YELLOW}Warning: .env file already exists. Overwrite? (y/n)${NC}"
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Setup canceled. Existing .env file will be kept.${NC}"
        exit 0
    fi
fi

# Default values
DEFAULT_POSTGRES_USER="postgres"
DEFAULT_POSTGRES_PASSWORD="postgres"
DEFAULT_POSTGRES_DB="crypto_predictor"
DEFAULT_POSTGRES_HOST="db"
DEFAULT_POSTGRES_PORT="5432"
DEFAULT_REDIS_PASSWORD=""
DEFAULT_REDIS_HOST="redis"
DEFAULT_REDIS_PORT="6379"
DEFAULT_LOG_LEVEL="INFO"
DEFAULT_FLASK_ENV="development"
DEFAULT_FLASK_DEBUG="1"
DEFAULT_GIN_MODE="debug"
DEFAULT_PREDICTION_INTERVALS="1,7,30"

echo -e "${BLUE}Please enter the following information (or press Enter for defaults):${NC}"
echo

# API Keys
echo -e "${GREEN}API Keys:${NC}"
echo -e "${YELLOW}Note: You can get a free CoinGecko API key from https://www.coingecko.com/en/api/pricing${NC}"
read -p "CoinGecko API Key: " COIN_API_KEY

echo -e "${YELLOW}Note: You can get a free Event Registry API key from https://eventregistry.org/register${NC}"
read -p "Event Registry API Key: " NEWS_API_KEY

echo -e "${YELLOW}Note: You need an OpenAI API key from https://platform.openai.com/api-keys${NC}"
read -p "OpenAI API Key: " OPENAI_API_KEY
echo

# Database settings
echo -e "${GREEN}Database Settings:${NC}"
read -p "PostgreSQL User [$DEFAULT_POSTGRES_USER]: " POSTGRES_USER
POSTGRES_USER=${POSTGRES_USER:-$DEFAULT_POSTGRES_USER}

read -p "PostgreSQL Password [$DEFAULT_POSTGRES_PASSWORD]: " POSTGRES_PASSWORD
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-$DEFAULT_POSTGRES_PASSWORD}

read -p "PostgreSQL Database [$DEFAULT_POSTGRES_DB]: " POSTGRES_DB
POSTGRES_DB=${POSTGRES_DB:-$DEFAULT_POSTGRES_DB}

read -p "PostgreSQL Host [$DEFAULT_POSTGRES_HOST]: " POSTGRES_HOST
POSTGRES_HOST=${POSTGRES_HOST:-$DEFAULT_POSTGRES_HOST}

read -p "PostgreSQL Port [$DEFAULT_POSTGRES_PORT]: " POSTGRES_PORT
POSTGRES_PORT=${POSTGRES_PORT:-$DEFAULT_POSTGRES_PORT}
echo

# Redis settings
echo -e "${GREEN}Redis Settings:${NC}"
read -p "Redis Password (leave blank for none) [$DEFAULT_REDIS_PASSWORD]: " REDIS_PASSWORD
REDIS_PASSWORD=${REDIS_PASSWORD:-$DEFAULT_REDIS_PASSWORD}

read -p "Redis Host [$DEFAULT_REDIS_HOST]: " REDIS_HOST
REDIS_HOST=${REDIS_HOST:-$DEFAULT_REDIS_HOST}

read -p "Redis Port [$DEFAULT_REDIS_PORT]: " REDIS_PORT
REDIS_PORT=${REDIS_PORT:-$DEFAULT_REDIS_PORT}
echo

# Application settings
echo -e "${GREEN}Application Settings:${NC}"
echo -e "${YELLOW}Log Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)${NC}"
read -p "Log Level [$DEFAULT_LOG_LEVEL]: " LOG_LEVEL
LOG_LEVEL=${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}

echo -e "${YELLOW}Flask Environment (development, production)${NC}"
read -p "Flask Environment [$DEFAULT_FLASK_ENV]: " FLASK_ENV
FLASK_ENV=${FLASK_ENV:-$DEFAULT_FLASK_ENV}

read -p "Flask Debug (1 for True, 0 for False) [$DEFAULT_FLASK_DEBUG]: " FLASK_DEBUG
FLASK_DEBUG=${FLASK_DEBUG:-$DEFAULT_FLASK_DEBUG}

echo -e "${YELLOW}Gin Mode (debug, release)${NC}"
read -p "Gin Mode [$DEFAULT_GIN_MODE]: " GIN_MODE
GIN_MODE=${GIN_MODE:-$DEFAULT_GIN_MODE}
echo

# Prediction settings
echo -e "${GREEN}Prediction Settings:${NC}"
read -p "Prediction Intervals (comma-separated days) [$DEFAULT_PREDICTION_INTERVALS]: " PREDICTION_INTERVALS
PREDICTION_INTERVALS=${PREDICTION_INTERVALS:-$DEFAULT_PREDICTION_INTERVALS}
echo

# Create .env file
cat > .env << EOF
# API Keys
COIN_API_KEY=$COIN_API_KEY
NEWS_API_KEY=$NEWS_API_KEY
OPENAI_API_KEY=$OPENAI_API_KEY

# Database Configuration
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=$POSTGRES_DB
POSTGRES_HOST=$POSTGRES_HOST
POSTGRES_PORT=$POSTGRES_PORT

# Redis Configuration
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_HOST=$REDIS_HOST
REDIS_PORT=$REDIS_PORT

# Application Settings
LOG_LEVEL=$LOG_LEVEL
FLASK_ENV=$FLASK_ENV
FLASK_DEBUG=$FLASK_DEBUG
GIN_MODE=$GIN_MODE

# Prediction Settings
PREDICTION_INTERVALS=$PREDICTION_INTERVALS
EOF

# Make setup script executable
chmod +x setup.sh

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}The .env file has been created with your settings.${NC}"
echo -e "${YELLOW}You can now run the application with:${NC}"
echo "docker-compose up -d"
echo

echo ".env file created. Please edit it to add your API keys."
echo "Then run 'docker-compose up --build' to start the application." 