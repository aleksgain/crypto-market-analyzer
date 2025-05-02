/**
 * Application configuration
 */
const config = {
  // Base URL for API requests
  // In development, API is on port 8080
  // In production with a reverse proxy, this would be empty
  apiBaseUrl: process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8080',
  
  // API endpoints
  endpoints: {
    prices: '/api/prices',
    news: '/api/news',
    predictions: '/api/predictions',
    accuracy: '/api/accuracy',
    advancedInsights: '/api/advanced-insights'
  }
};

export default config; 