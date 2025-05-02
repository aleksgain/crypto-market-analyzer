import React, { useState, useEffect } from 'react';
import { Grid, Paper, Typography, Box, CircularProgress, Card, CardContent, CardActionArea, Chip, Link } from '@mui/material';
import { Doughnut } from 'react-chartjs-2';
import { Chart, ArcElement, Tooltip, Legend } from 'chart.js';
import axios from 'axios';
import config from '../config';

// Register Chart.js components
Chart.register(ArcElement, Tooltip, Legend);

const NewsPage = () => {
  const [newsData, setNewsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${config.apiBaseUrl}${config.endpoints.news}`);
        setNewsData(response.data);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching news data:', error);
        setError('Failed to fetch news data. Please try again later.');
        setLoading(false);
      }
    };

    fetchNews();
  }, []);

  const formatSentimentData = (newsItems) => {
    if (!newsItems || newsItems.length === 0) {
      return {
        labels: ['Positive', 'Neutral', 'Negative'],
        datasets: [{
          data: [0, 0, 0],
          backgroundColor: ['rgba(75, 192, 192, 0.6)', 'rgba(255, 206, 86, 0.6)', 'rgba(255, 99, 132, 0.6)'],
          borderColor: ['rgba(75, 192, 192, 1)', 'rgba(255, 206, 86, 1)', 'rgba(255, 99, 132, 1)'],
          borderWidth: 1
        }]
      };
    }

    let positive = 0;
    let neutral = 0;
    let negative = 0;

    newsItems.forEach(item => {
      if (item.sentiment_score > 0.1) {
        positive++;
      } else if (item.sentiment_score < -0.1) {
        negative++;
      } else {
        neutral++;
      }
    });

    return {
      labels: ['Positive', 'Neutral', 'Negative'],
      datasets: [{
        data: [positive, neutral, negative],
        backgroundColor: ['rgba(75, 192, 192, 0.6)', 'rgba(255, 206, 86, 0.6)', 'rgba(255, 99, 132, 0.6)'],
        borderColor: ['rgba(75, 192, 192, 1)', 'rgba(255, 206, 86, 1)', 'rgba(255, 99, 132, 1)'],
        borderWidth: 1
      }]
    };
  };

  const chartOptions = {
    plugins: {
      legend: {
        position: 'right',
      },
      title: {
        display: true,
        text: 'News Sentiment Distribution'
      }
    },
    responsive: true,
    maintainAspectRatio: false
  };

  const getSentimentColor = (score) => {
    if (score > 0.1) return 'success';
    if (score < -0.1) return 'error';
    return 'warning';
  };

  const getSentimentLabel = (score) => {
    if (score > 0.1) return 'Positive';
    if (score < -0.1) return 'Negative';
    return 'Neutral';
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
        Crypto News & Sentiment Analysis
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Current Sentiment
            </Typography>
            
            <Box sx={{ height: 300 }}>
              <Doughnut 
                data={formatSentimentData(newsData.news)} 
                options={chartOptions} 
              />
            </Box>
            
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2, textAlign: 'center' }}>
              Based on analysis of {newsData.news.length} recent news articles
            </Typography>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent News
            </Typography>
            
            <Grid container spacing={2}>
              {newsData.news.map((article, index) => (
                <Grid item xs={12} key={index}>
                  <Card>
                    <CardActionArea component={Link} href={article.url} target="_blank" rel="noopener">
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                          <Typography variant="h6" component="div" sx={{ flex: 1 }}>
                            {article.title}
                          </Typography>
                          <Chip 
                            label={`${getSentimentLabel(article.sentiment_score)} (${article.sentiment_score.toFixed(2)})`}
                            color={getSentimentColor(article.sentiment_score)}
                            size="small"
                            sx={{ ml: 1 }}
                          />
                        </Box>
                        
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
                          <Typography variant="body2" color="text.secondary">
                            Source: {article.source}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {new Date(article.published_at).toLocaleString()}
                          </Typography>
                        </Box>
                      </CardContent>
                    </CardActionArea>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default NewsPage; 