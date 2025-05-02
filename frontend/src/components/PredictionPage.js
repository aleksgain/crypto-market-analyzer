import React, { useState, useEffect } from 'react';
import { Grid, Paper, Typography, Box, CircularProgress, Divider } from '@mui/material';
import { Line } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import axios from 'axios';

// Register Chart.js components
Chart.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const PredictionPage = () => {
  const [predictionData, setPredictionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('http://localhost:8080/api/predictions?symbols=BTC,ETH');
        setPredictionData(response.data);
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
    const labels = Object.keys(data.predictions).map(key => 
      key.replace('_day', '-Day')
    );
    
    const currentPrice = data.current_price;
    const predictedPrices = Object.values(data.predictions).map(p => p.predicted_price);
    
    return {
      labels,
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
        Below are our price predictions based on current market trends and sentiment analysis.
        Please note that these are speculative projections and should not be used for financial advice.
      </Typography>
      
      <Grid container spacing={3}>
        {predictionData && Object.entries(predictionData).map(([symbol, data]) => (
          <Grid item xs={12} md={6} key={symbol}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom>
                {symbol} - Current Price: ${data.current_price.toLocaleString()}
              </Typography>
              
              <Box sx={{ height: 300, mb: 3 }}>
                <Line 
                  data={formatChartData(symbol, data)} 
                  options={chartOptions} 
                />
              </Box>
              
              <Divider sx={{ my: 2 }} />
              
              <Typography variant="h6" gutterBottom>
                Detailed Predictions
              </Typography>
              
              <Grid container spacing={2}>
                {Object.entries(data.predictions).map(([timeframe, prediction]) => (
                  <Grid item xs={12} md={4} key={timeframe}>
                    <Paper 
                      sx={{ 
                        p: 2, 
                        textAlign: 'center',
                        backgroundColor: prediction.sentiment_factor >= 0 ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)'
                      }}
                      elevation={1}
                    >
                      <Typography variant="subtitle1">
                        {timeframe.replace('_', ' ')}
                      </Typography>
                      <Typography variant="h6">
                        ${prediction.predicted_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Target date: {new Date(prediction.target_date).toLocaleDateString()}
                      </Typography>
                      <Typography 
                        variant="body2" 
                        color={prediction.sentiment_factor >= 0 ? 'success.main' : 'error.main'}
                      >
                        Sentiment: {prediction.sentiment_factor.toFixed(2)}
                      </Typography>
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