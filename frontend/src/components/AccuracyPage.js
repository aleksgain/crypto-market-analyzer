import React, { useState, useEffect } from 'react';
import { Grid, Paper, Typography, Box, CircularProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import { Bar } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import axios from 'axios';

// Register Chart.js components
Chart.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const AccuracyPage = () => {
  const [accuracyData, setAccuracyData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('http://localhost:8080/api/accuracy');
        setAccuracyData(response.data);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching accuracy data:', err);
        setError('Failed to fetch accuracy data. Please try again later.');
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const formatChartData = (summaryData) => {
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

  const chartOptions = {
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        title: {
          display: true,
          text: 'Accuracy (%)'
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
        text: 'Prediction Accuracy by Timeframe'
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            return `${context.dataset.label}: ${context.raw.toFixed(2)}% accuracy`;
          }
        }
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

  // Check if we have any accuracy data yet
  const noDataAvailable = !accuracyData || 
                         !accuracyData.summary || 
                         Object.keys(accuracyData.summary).length === 0 ||
                         !accuracyData.raw_data ||
                         accuracyData.raw_data.length === 0;

  if (noDataAvailable) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          Prediction Accuracy
        </Typography>
        
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No accuracy data available yet
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
            As predictions reach their target dates, accuracy metrics will be displayed here.
          </Typography>
        </Paper>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Prediction Accuracy
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Accuracy Overview
            </Typography>
            
            <Box sx={{ height: 400, mb: 4 }}>
              <Bar 
                data={formatChartData(accuracyData.summary)} 
                options={chartOptions} 
              />
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Predictions Results
            </Typography>
            
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Symbol</TableCell>
                    <TableCell>Prediction Date</TableCell>
                    <TableCell>Target Date</TableCell>
                    <TableCell>Predicted Price</TableCell>
                    <TableCell>Actual Price</TableCell>
                    <TableCell>Error</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {accuracyData.raw_data.slice(0, 10).map((record, index) => (
                    <TableRow key={index}>
                      <TableCell>{record.symbol}</TableCell>
                      <TableCell>{new Date(record.prediction_date).toLocaleDateString()}</TableCell>
                      <TableCell>{new Date(record.target_date).toLocaleDateString()}</TableCell>
                      <TableCell>${record.predicted_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</TableCell>
                      <TableCell>${record.actual_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</TableCell>
                      <TableCell>
                        <Typography 
                          color={record.error_rate < 0.05 ? 'success.main' : record.error_rate < 0.1 ? 'warning.main' : 'error.main'}
                        >
                          {(record.error_rate * 100).toFixed(2)}%
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default AccuracyPage; 