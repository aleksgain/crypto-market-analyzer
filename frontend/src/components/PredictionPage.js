import React, { useState, useEffect } from 'react';
import { Grid, Paper, Typography, Box, CircularProgress, Divider, Chip, LinearProgress } from '@mui/material';
import { Line } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import axios from 'axios';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import SettingsEthernetIcon from '@mui/icons-material/SettingsEthernet';
import EqualizerIcon from '@mui/icons-material/Equalizer';
import config from '../config';

// Register Chart.js components
Chart.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const PredictionPage = () => {
  const [predictionData, setPredictionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(`${config.apiBaseUrl}${config.endpoints.predictions}?symbols=BTC,ETH`);
        setPredictionData(response.data.predictions);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching prediction data:', err);
        setError('Failed to fetch prediction data. Please try again later.');
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const formatChartData = (symbol, data) => {
    // Sort timeframes by day count (1-day, 7-day, 30-day)
    const timeframes = Object.keys(data.predictions)
      .sort((a, b) => {
        const daysA = parseInt(a.split('_')[0]);
        const daysB = parseInt(b.split('_')[0]);
        return daysA - daysB;
      });
    
    const labels = timeframes.map(key => 
      key.replace('_day', '-Day')
    );
    
    const currentPrice = data.current_price;
    const predictedPrices = timeframes.map(key => data.predictions[key].predicted_price);
    
    return {
      labels: ['Current', ...labels],
      datasets: [
        {
          label: 'Predicted Price',
          data: [currentPrice, ...predictedPrices],
          fill: false,
          backgroundColor: 'rgba(75, 192, 192, 0.6)',
          borderColor: 'rgba(75, 192, 192, 1)',
          tension: 0.1
        }
      ]
    };
  };

  const chartOptions = {
    scales: {
      y: {
        beginAtZero: false,
        title: {
          display: true,
          text: 'Price (USD)'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Prediction Timeframe'
        }
      }
    },
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Price Predictions'
      }
    }
  };

  // Component to display technical signals
  const TechnicalSignals = ({ signals }) => {
    if (!signals) return null;
    
    const { trend, oscillators, values, overall, levels } = signals;

    return (
      <Box sx={{ mt: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1, border: 1, borderColor: 'divider' }}>
        <Typography variant="h6" gutterBottom display="flex" alignItems="center">
          <ShowChartIcon sx={{ mr: 1 }} />
          Technical Analysis
        </Typography>
        
        <Grid container spacing={2}>
          {/* Trend Indicators */}
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom display="flex" alignItems="center">
              <TrendingUpIcon sx={{ mr: 0.5, fontSize: 'small' }} />
              Trend Indicators
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip 
                label={`SMA Trend: ${trend.sma_trend}`}
                color={trend.sma_trend === 'bullish' ? 'success' : 'error'}
                size="small"
                variant="outlined"
              />
              <Chip 
                label={`MACD: ${trend.macd}`}
                color={trend.macd === 'bullish' ? 'success' : 'error'}
                size="small"
                variant="outlined"
              />
              <Chip 
                label={`MACD Hist: ${trend.macd_histogram}`}
                color={
                  trend.macd_histogram === 'bullish' ? 'success' : 
                  trend.macd_histogram === 'bearish' ? 'error' : 'default'
                }
                size="small"
                variant="outlined"
              />
            </Box>
          </Grid>
          
          {/* Oscillators */}
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom display="flex" alignItems="center">
              <EqualizerIcon sx={{ mr: 0.5, fontSize: 'small' }} />
              Oscillators
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip 
                label={`RSI: ${values.rsi}`}
                color={
                  oscillators.rsi === 'overbought' ? 'error' : 
                  oscillators.rsi === 'oversold' ? 'success' : 'default'
                }
                size="small"
                variant="outlined"
              />
              <Chip 
                label={`Bollinger: ${oscillators.bollinger}`}
                color={
                  oscillators.bollinger === 'overbought' ? 'error' : 
                  oscillators.bollinger === 'oversold' ? 'success' : 'default'
                }
                size="small"
                variant="outlined"
              />
            </Box>
          </Grid>
          
          {/* Support/Resistance */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom display="flex" alignItems="center">
              <SettingsEthernetIcon sx={{ mr: 0.5, fontSize: 'small' }} />
              Key Levels
            </Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Typography variant="body2">Support: ${levels.support}</Typography>
              <Typography variant="body2">Resistance: ${levels.resistance}</Typography>
            </Box>
          </Grid>
          
          {/* Overall Signal */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>
              Overall Signal: 
              <Box component="span" sx={{ 
                ml: 1, 
                color: overall.signal === 'bullish' ? 'success.main' : 
                       overall.signal === 'bearish' ? 'error.main' : 'text.secondary',
                fontWeight: 'bold'
              }}>
                {overall.signal.toUpperCase()}
              </Box>
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={overall.strength * 100}
              color={overall.signal === 'bullish' ? 'success' : 'error'} 
              sx={{ height: 8, borderRadius: 4 }}
            />
            <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
              Signal Strength: {overall.strength * 100}%
            </Typography>
          </Grid>
        </Grid>
      </Box>
    );
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <Typography color="error" variant="h6">{error}</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Price Predictions
      </Typography>
      
      <Typography variant="body1" paragraph>
        Below are our price predictions based on market sentiment analysis and technical indicators.
        The predictions combine AI sentiment analysis with technical analysis patterns for a more comprehensive view.
      </Typography>
      
      <Grid container spacing={3}>
        {predictionData && Object.entries(predictionData).map(([symbol, data]) => (
          <Grid item xs={12} md={6} key={symbol}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom>
                {symbol} - Current Price: ${data && data.current_price ? data.current_price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "N/A"}
              </Typography>
              
              <Box sx={{ height: 300, mb: 3 }}>
                <Line 
                  data={formatChartData(symbol, data)} 
                  options={chartOptions} 
                />
              </Box>
              
              {/* Technical Analysis Section */}
              <TechnicalSignals signals={data.technical_signals} />
              
              <Divider sx={{ my: 2 }} />
              
              <Typography variant="h6" gutterBottom>
                Detailed Predictions
              </Typography>
              
              <Grid container spacing={2}>
                {data && data.predictions && Object.entries(data.predictions)
                  .sort((a, b) => {
                    // Extract the number of days from the timeframe key
                    const daysA = parseInt(a[0].split('_')[0]);
                    const daysB = parseInt(b[0].split('_')[0]);
                    // Sort by days ascending
                    return daysA - daysB;
                  })
                  .map(([timeframe, prediction]) => (
                  <Grid item xs={12} md={4} key={timeframe}>
                    <Paper 
                      sx={{ 
                        p: 2, 
                        textAlign: 'center',
                        backgroundColor: prediction.direction === 'up' ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)',
                        border: 1,
                        borderColor: 'divider',
                      }}
                      elevation={1}
                    >
                      <Typography variant="subtitle1">
                        {timeframe.replace('_', ' ')}
                      </Typography>
                      
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mt: 1 }}>
                        {prediction.direction === 'up' ? (
                          <TrendingUpIcon color="success" />
                        ) : (
                          <TrendingDownIcon color="error" />
                        )}
                        <Typography variant="h6" sx={{ ml: 1 }}>
                          ${prediction.predicted_price ? prediction.predicted_price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "N/A"}
                        </Typography>
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary">
                        Target date: {prediction.target_date ? new Date(prediction.target_date).toLocaleDateString() : "N/A"}
                      </Typography>
                      
                      <Box sx={{ mt: 1, mb: 1 }}>
                        <LinearProgress 
                          variant="determinate" 
                          value={prediction.confidence ? prediction.confidence * 100 : 0}
                          color={prediction.direction === 'up' ? 'success' : 'error'} 
                          sx={{ height: 6, borderRadius: 3 }}
                        />
                        <Typography variant="caption" display="block">
                          Confidence: {prediction.confidence ? Math.round(prediction.confidence * 100) : 0}%
                        </Typography>
                      </Box>
                      
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, justifyContent: 'center', mt: 1 }}>
                        {prediction.sentiment_factor !== 0 && prediction.sentiment_factor !== undefined && (
                          <Chip 
                            label={`Sentiment: ${prediction.sentiment_factor >= 0 ? '+' : ''}${prediction.sentiment_factor.toFixed(2)}`}
                            size="small"
                            color={prediction.sentiment_factor >= 0 ? 'success' : 'error'}
                            variant="outlined"
                          />
                        )}
                        
                        {prediction.technical_factor !== 0 && prediction.technical_factor !== undefined && (
                          <Chip 
                            label={`Technical: ${prediction.technical_factor >= 0 ? '+' : ''}${prediction.technical_factor.toFixed(2)}`}
                            size="small"
                            color={prediction.technical_factor >= 0 ? 'success' : 'error'}
                            variant="outlined"
                          />
                        )}
                      </Box>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default PredictionPage; 