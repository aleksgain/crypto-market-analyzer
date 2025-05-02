import React, { useState, useEffect } from 'react';
import { 
  Grid, 
  Paper, 
  Typography, 
  Box, 
  CircularProgress,
  Tabs, 
  Tab,
  Card, 
  CardContent, 
  Divider,
  Chip,
  Link,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import EqualizerIcon from '@mui/icons-material/Equalizer';
import ArticleIcon from '@mui/icons-material/Article';
import NewReleasesIcon from '@mui/icons-material/NewReleases';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { 
  Chart, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  Title, 
  Tooltip, 
  Legend,
  ArcElement,
  BarElement 
} from 'chart.js';
import axios from 'axios';
import config from '../config';

// Register Chart.js components
Chart.register(
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  Title, 
  Tooltip, 
  Legend,
  ArcElement,
  BarElement
);

const Dashboard = () => {
  // State variables
  const [priceData, setPriceData] = useState(null);
  const [newsData, setNewsData] = useState(null);
  const [predictionsData, setPredictionsData] = useState(null);
  const [accuracyData, setAccuracyData] = useState(null);
  const [advancedInsights, setAdvancedInsights] = useState(null);
  const [loading, setLoading] = useState({
    prices: true,
    news: true,
    predictions: true,
    accuracy: true,
    insights: true
  });
  const [error, setError] = useState({
    prices: null,
    news: null,
    predictions: null,
    accuracy: null,
    insights: null
  });
  const [activeTab, setActiveTab] = useState(0);

  // Fetch all data on component mount
  useEffect(() => {
    const fetchAllData = async () => {
      // Fetch prices
      try {
        const priceResponse = await axios.get(`${config.apiBaseUrl}${config.endpoints.prices}?symbols=BTC,ETH`);
        setPriceData(priceResponse.data);
        setLoading(prev => ({ ...prev, prices: false }));
      } catch (err) {
        console.error('Error fetching price data:', err);
        setError(prev => ({ ...prev, prices: 'Failed to fetch price data.' }));
        setLoading(prev => ({ ...prev, prices: false }));
      }

      // Fetch news
      try {
        const newsResponse = await axios.get(`${config.apiBaseUrl}${config.endpoints.news}`);
        setNewsData(newsResponse.data);
        setLoading(prev => ({ ...prev, news: false }));
      } catch (err) {
        console.error('Error fetching news data:', err);
        setError(prev => ({ ...prev, news: 'Failed to fetch news data.' }));
        setLoading(prev => ({ ...prev, news: false }));
      }

      // Fetch predictions
      try {
        const predictionsResponse = await axios.get(`${config.apiBaseUrl}${config.endpoints.predictions}?symbols=BTC,ETH`);
        setPredictionsData(predictionsResponse.data);
        setLoading(prev => ({ ...prev, predictions: false }));
      } catch (err) {
        console.error('Error fetching prediction data:', err);
        setError(prev => ({ ...prev, predictions: 'Failed to fetch prediction data.' }));
        setLoading(prev => ({ ...prev, predictions: false }));
      }

      // Fetch accuracy
      try {
        const accuracyResponse = await axios.get(`${config.apiBaseUrl}${config.endpoints.accuracy}`);
        setAccuracyData(accuracyResponse.data);
        setLoading(prev => ({ ...prev, accuracy: false }));
      } catch (err) {
        console.error('Error fetching accuracy data:', err);
        setError(prev => ({ ...prev, accuracy: 'Failed to fetch accuracy data.' }));
        setLoading(prev => ({ ...prev, accuracy: false }));
      }

      // Fetch advanced insights
      try {
        const insightsResponse = await axios.get(`${config.apiBaseUrl}${config.endpoints.advancedInsights}`);
        setAdvancedInsights(insightsResponse.data);
        setLoading(prev => ({ ...prev, insights: false }));
      } catch (err) {
        console.error('Error fetching advanced insights:', err);
        setError(prev => ({ ...prev, insights: 'Failed to fetch advanced insights.' }));
        setLoading(prev => ({ ...prev, insights: false }));
      }
    };

    fetchAllData();
    
    // Set up refresh intervals (every 5 minutes)
    const interval = setInterval(fetchAllData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  // Format chart data for predictions
  const formatPredictionChartData = (symbol, data) => {
    if (!data || !data.predictions) return null;
    
    // Get timeframes and sort them by day count
    const timeframes = Object.keys(data.predictions)
      .sort((a, b) => {
        const daysA = parseInt(a.split('_')[0]);
        const daysB = parseInt(b.split('_')[0]);
        return daysA - daysB;
      });
    
    const labels = timeframes.map(key => key.replace('_day', '-Day'));
    
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

  // Format sentiment data for chart
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
      // Prefer AI score if available
      const score = item.ai_score ?? item.sentiment_score;
      
      if (score > 0.1) {
        positive++;
      } else if (score < -0.1) {
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

  // Format accuracy chart data
  const formatAccuracyChartData = (summaryData) => {
    if (!summaryData || Object.keys(summaryData).length === 0) {
      return {
        labels: [],
        datasets: []
      };
    }
    
    const labels = [];
    const datasets = [];
    const colors = ['rgba(75, 192, 192, 0.6)', 'rgba(153, 102, 255, 0.6)'];
    
    Object.entries(summaryData).forEach(([symbol, timespans], index) => {
      const dataPoints = [];
      
      Object.entries(timespans).forEach(([days, data]) => {
        if (!labels.includes(`${days}-Day`)) {
          labels.push(`${days}-Day`);
        }
        
        // Calculate accuracy percentage (1 - error)
        const accuracyPercentage = (1 - data.avg_error) * 100;
        dataPoints.push({
          x: `${days}-Day`,
          y: accuracyPercentage
        });
      });
      
      // Sort dataPoints to match labels
      const sortedDataPoints = labels.map(label => {
        const match = dataPoints.find(point => point.x === label);
        return match ? match.y : null;
      });
      
      datasets.push({
        label: symbol,
        data: sortedDataPoints,
        backgroundColor: colors[index % colors.length],
        borderColor: colors[index % colors.length].replace('0.6', '1'),
        borderWidth: 1
      });
    });
    
    return {
      labels,
      datasets
    };
  };

  // Chart options
  const chartOptions = {
    scales: {
      y: {
        beginAtZero: false,
      }
    },
    plugins: {
      legend: {
        position: 'top',
      }
    },
    responsive: true,
    maintainAspectRatio: false
  };

  // Determine if we should show accuracy section
  const showAccuracy = accuracyData && 
                      accuracyData.summary && 
                      Object.keys(accuracyData.summary).length > 0 &&
                      accuracyData.raw_data &&
                      accuracyData.raw_data.length > 0;

  // Helper functions for styling
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

  // Check if we're still loading all data
  if (loading.prices || loading.predictions) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress />
      </Box>
    );
  }

  // Check for critical errors
  if (error.prices || error.predictions) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <Typography color="error" variant="h6">
          {error.prices || error.predictions}
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Crypto Market Analysis Dashboard
      </Typography>

      {/* Market Overview Section */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {priceData && Object.entries(priceData).map(([symbol, data]) => (
          <Grid item xs={12} md={6} key={symbol}>
            <Paper sx={{ p: 3, height: '100%' }}>
              <Typography variant="h5" gutterBottom>
                {symbol} - ${data.price.toLocaleString()}
              </Typography>
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Market Cap
                  </Typography>
                  <Typography variant="body1">
                    ${data.market_cap.toLocaleString()}
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    24h Volume
                  </Typography>
                  <Typography variant="body1">
                    ${data.volume_24h.toLocaleString()}
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    24h Change
                  </Typography>
                  <Typography 
                    variant="body1" 
                    color={data.price_change_24h >= 0 ? 'success.main' : 'error.main'}
                  >
                    {data.price_change_24h > 0 ? '+' : ''}{data.price_change_24h.toFixed(2)}%
                  </Typography>
                </Box>
              </Box>
              
              {/* Price Chart */}
              {predictionsData && predictionsData[symbol] && (
                <Box sx={{ height: 200, mb: 2 }}>
                  <Line 
                    data={formatPredictionChartData(symbol, predictionsData[symbol])} 
                    options={chartOptions} 
                  />
                </Box>
              )}
              
              {/* Detailed Predictions */}
              {predictionsData && predictionsData[symbol] && predictionsData[symbol].predictions && (
                <Grid container spacing={1}>
                  {Object.entries(predictionsData[symbol].predictions)
                    .sort((a, b) => {
                      // Extract the number of days from the timeframe key
                      const daysA = parseInt(a[0].split('_')[0]);
                      const daysB = parseInt(b[0].split('_')[0]);
                      // Sort by days ascending
                      return daysA - daysB;
                    })
                    .map(([timeframe, prediction]) => (
                      <Grid item xs={4} key={timeframe}>
                        <Paper 
                          sx={{ 
                            p: 1, 
                            textAlign: 'center',
                            backgroundColor: prediction.sentiment_factor >= 0 ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)'
                          }}
                          elevation={1}
                        >
                          <Typography variant="caption">
                            {timeframe.replace('_', ' ')}
                          </Typography>
                          <Typography variant="body2" fontWeight="bold">
                            ${prediction.predicted_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                          </Typography>
                        </Paper>
                      </Grid>
                    ))}
                </Grid>
              )}
              
              <Typography variant="body2" color="text.secondary" align="right" sx={{ mt: 1 }}>
                Last updated: {new Date(data.last_updated).toLocaleString()}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Advanced Insights Section */}
      {advancedInsights && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" gutterBottom>
            AI-Powered Insights
          </Typography>
          
          <Grid container spacing={3}>
            {/* Expert Analysis */}
            {advancedInsights.expert_analysis && (
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Market Analysis
                    <Chip 
                      label={advancedInsights.expert_analysis.market_sentiment} 
                      color={
                        advancedInsights.expert_analysis.market_sentiment === 'bullish' ? 'success' : 
                        advancedInsights.expert_analysis.market_sentiment === 'bearish' ? 'error' : 'warning'
                      }
                      size="small"
                      sx={{ ml: 1 }}
                    />
                  </Typography>
                  
                  <Typography paragraph>
                    {advancedInsights.expert_analysis.market_summary}
                  </Typography>
                  
                  <Typography variant="subtitle2">Short-term Outlook:</Typography>
                  <Typography paragraph>
                    {advancedInsights.expert_analysis.short_term_outlook}
                  </Typography>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2">BTC Technical Pattern:</Typography>
                      <Typography paragraph>
                        {advancedInsights.expert_analysis.btc_pattern}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2">ETH Technical Pattern:</Typography>
                      <Typography paragraph>
                        {advancedInsights.expert_analysis.eth_pattern}
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>
            )}
            
            {/* On-chain Analysis */}
            {advancedInsights.onchain_analysis && (
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    On-chain Data Analysis
                  </Typography>
                  
                  <Typography paragraph>
                    {advancedInsights.onchain_analysis.summary}
                  </Typography>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 1, bgcolor: 'action.hover' }}>
                        <Typography variant="subtitle2">BTC Active Addresses:</Typography>
                        <Typography variant="body2">
                          {advancedInsights.onchain_analysis.btc_active_addresses.value}
                          <Chip
                            label={`${advancedInsights.onchain_analysis.btc_active_addresses.change}`}
                            color={parseFloat(advancedInsights.onchain_analysis.btc_active_addresses.change) > 0 ? 'success' : 'error'}
                            size="small"
                            sx={{ ml: 1 }}
                          />
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 1, bgcolor: 'action.hover' }}>
                        <Typography variant="subtitle2">ETH Active Addresses:</Typography>
                        <Typography variant="body2">
                          {advancedInsights.onchain_analysis.eth_active_addresses.value}
                          <Chip
                            label={`${advancedInsights.onchain_analysis.eth_active_addresses.change}`}
                            color={parseFloat(advancedInsights.onchain_analysis.eth_active_addresses.change) > 0 ? 'success' : 'error'}
                            size="small"
                            sx={{ ml: 1 }}
                          />
                        </Typography>
                      </Paper>
                    </Grid>
                  </Grid>
                  
                  <Typography variant="subtitle2" sx={{ mt: 2 }}>Large Wallet Movements:</Typography>
                  {advancedInsights.onchain_analysis.large_wallet_movements.map((movement, idx) => (
                    <Box key={idx} sx={{ mt: 1, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
                      <Typography variant="body2">
                        {movement.currency}: {movement.amount} (${movement.usd_value})
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {movement.type} - {movement.significance}
                      </Typography>
                    </Box>
                  ))}
                </Paper>
              </Grid>
            )}
          </Grid>
        </Box>
      )}

      {/* News and Accuracy Sections */}
      <Box sx={{ mb: 2 }}>
        <Tabs 
          value={activeTab} 
          onChange={handleTabChange} 
          centered
          sx={{ mb: 2 }}
        >
          <Tab icon={<ArticleIcon />} label="News" />
          {showAccuracy && <Tab icon={<EqualizerIcon />} label="Prediction Accuracy" />}
          {advancedInsights?.market_insights?.length > 0 && (
            <Tab icon={<NewReleasesIcon />} label="Key Market Events" />
          )}
        </Tabs>
        
        {/* News Panel */}
        {activeTab === 0 && (
          <Grid container spacing={3}>
            {/* Sentiment Chart */}
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 3, height: '100%' }}>
                <Typography variant="h6" gutterBottom>
                  News Sentiment
                </Typography>
                
                <Box sx={{ height: 250 }}>
                  {newsData && (
                    <Doughnut 
                      data={formatSentimentData(newsData.news)} 
                      options={{
                        plugins: {
                          legend: {
                            position: 'bottom',
                          }
                        },
                        responsive: true,
                        maintainAspectRatio: false
                      }} 
                    />
                  )}
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2, textAlign: 'center' }}>
                  Based on {newsData?.news?.length || 0} recent news articles
                </Typography>
              </Paper>
            </Grid>
            
            {/* News List */}
            <Grid item xs={12} md={8}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Recent News
                </Typography>
                
                {newsData?.news?.slice(0, 6).map((article, index) => (
                  <Card sx={{ mb: 2 }} key={index}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                        <Typography variant="subtitle1" component="div" sx={{ flex: 1 }}>
                          {article.title}
                        </Typography>
                        <Chip 
                          label={`${getSentimentLabel(article.ai_score || article.sentiment_score)} (${(article.ai_score || article.sentiment_score).toFixed(2)})`}
                          color={getSentimentColor(article.ai_score || article.sentiment_score)}
                          size="small"
                          sx={{ ml: 1 }}
                        />
                      </Box>
                      
                      {article.ai_explanation && (
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1, fontStyle: 'italic' }}>
                          "{article.ai_explanation}"
                        </Typography>
                      )}
                      
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Source: {article.source}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(article.published_at).toLocaleString()}
                        </Typography>
                      </Box>
                      
                      <Link href={article.url} target="_blank" rel="noopener" sx={{ display: 'block', mt: 1, fontSize: '0.75rem' }}>
                        Read full article
                      </Link>
                    </CardContent>
                  </Card>
                ))}
              </Paper>
            </Grid>
          </Grid>
        )}
        
        {/* Accuracy Panel */}
        {activeTab === 1 && showAccuracy && (
          <Box>
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Prediction Accuracy Overview
              </Typography>
              
              <Box sx={{ height: 300, mb: 4 }}>
                <Bar 
                  data={formatAccuracyChartData(accuracyData.summary)} 
                  options={{
                    ...chartOptions,
                    scales: {
                      y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                          display: true,
                          text: 'Accuracy (%)'
                        }
                      }
                    },
                    plugins: {
                      tooltip: {
                        callbacks: {
                          label: (context) => {
                            return `${context.dataset.label}: ${context.raw.toFixed(2)}% accuracy`;
                          }
                        }
                      }
                    }
                  }} 
                />
              </Box>
            </Paper>
            
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Recent Predictions Results
              </Typography>
              
              <Box sx={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '8px', borderBottom: '1px solid #ddd' }}>Symbol</th>
                      <th style={{ textAlign: 'left', padding: '8px', borderBottom: '1px solid #ddd' }}>Prediction Date</th>
                      <th style={{ textAlign: 'left', padding: '8px', borderBottom: '1px solid #ddd' }}>Target Date</th>
                      <th style={{ textAlign: 'right', padding: '8px', borderBottom: '1px solid #ddd' }}>Predicted Price</th>
                      <th style={{ textAlign: 'right', padding: '8px', borderBottom: '1px solid #ddd' }}>Actual Price</th>
                      <th style={{ textAlign: 'right', padding: '8px', borderBottom: '1px solid #ddd' }}>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accuracyData.raw_data.slice(0, 5).map((record, index) => (
                      <tr key={index}>
                        <td style={{ padding: '8px', borderBottom: '1px solid #ddd' }}>{record.symbol}</td>
                        <td style={{ padding: '8px', borderBottom: '1px solid #ddd' }}>{new Date(record.prediction_date).toLocaleDateString()}</td>
                        <td style={{ padding: '8px', borderBottom: '1px solid #ddd' }}>{new Date(record.target_date).toLocaleDateString()}</td>
                        <td style={{ textAlign: 'right', padding: '8px', borderBottom: '1px solid #ddd' }}>${record.predicted_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                        <td style={{ textAlign: 'right', padding: '8px', borderBottom: '1px solid #ddd' }}>${record.actual_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                        <td style={{ 
                          textAlign: 'right', 
                          padding: '8px', 
                          borderBottom: '1px solid #ddd',
                          color: record.error_rate < 0.05 ? 'green' : record.error_rate < 0.1 ? 'orange' : 'red'
                        }}>
                          {(record.error_rate * 100).toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Box>
            </Paper>
          </Box>
        )}
        
        {/* Market Insights Panel */}
        {activeTab === 2 && advancedInsights?.market_insights?.length > 0 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              AI-Extracted Market Events
            </Typography>
            
            {advancedInsights.market_insights.map((insight, index) => (
              <Accordion key={index} defaultExpanded={index === 0}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography fontWeight="bold">{insight.key_event}</Typography>
                  <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center' }}>
                    <Chip 
                      icon={parseInt(insight.btc_impact) > 0 ? <TrendingUpIcon /> : <TrendingDownIcon />} 
                      label={`BTC: ${insight.btc_impact}`}
                      color={parseInt(insight.btc_impact) > 0 ? 'success' : 'error'}
                      size="small"
                      sx={{ mr: 1 }}
                    />
                    <Chip 
                      icon={parseInt(insight.eth_impact) > 0 ? <TrendingUpIcon /> : <TrendingDownIcon />} 
                      label={`ETH: ${insight.eth_impact}`}
                      color={parseInt(insight.eth_impact) > 0 ? 'success' : 'error'}
                      size="small"
                    />
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box>
                    <Typography variant="subtitle2">From: {insight.article_title}</Typography>
                    <Typography variant="caption" color="text.secondary">Source: {insight.article_source}</Typography>
                    
                    <Divider sx={{ my: 1 }} />
                    
                    <Typography variant="subtitle2">Key Entities:</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
                      {insight.entities.map((entity, idx) => (
                        <Chip key={idx} label={entity} size="small" variant="outlined" />
                      ))}
                    </Box>
                    
                    {insight.predictions && (
                      <>
                        <Typography variant="subtitle2">Predictions Mentioned:</Typography>
                        <Typography variant="body2">{insight.predictions}</Typography>
                      </>
                    )}
                    
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Confidence: {insight.confidence}/10
                      </Typography>
                    </Box>
                  </Box>
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default Dashboard; 