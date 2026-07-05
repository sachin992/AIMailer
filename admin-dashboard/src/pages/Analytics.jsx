import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Paper,
  Grid,
  ToggleButtonGroup,
  ToggleButton,
  Button,
} from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import apiService from '../services/api';
import { toast } from 'react-toastify';

const Analytics = () => {
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('weekly');
  const [summary, setSummary] = useState(null);
  const [insights, setInsights] = useState(null);

  useEffect(() => {
    fetchAnalytics();
  }, [period]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const [summaryRes, insightsRes] = await Promise.all([
        apiService.getAnalyticsSummary(period),
        apiService.getPerformanceInsights(),
      ]);

      setSummary(summaryRes.data.summary);
      setInsights(insightsRes.data.insights);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const res = await apiService.exportAnalyticsReport();
      toast.success(`Report exported to ${res.data.file}`);
    } catch (error) {
      console.error('Error exporting report:', error);
      toast.error('Failed to export report');
    }
  };

  const handlePeriodChange = (event, newPeriod) => {
    if (newPeriod !== null) {
      setPeriod(newPeriod);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  const chartData = [
    {
      name: 'Email Processing',
      'Auto Replied': summary?.auto_replied || 0,
      'Pending Review': summary?.manual_review || 0,
      'Failed': summary?.failed || 0,
    },
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Analytics</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <ToggleButtonGroup
            value={period}
            exclusive
            onChange={handlePeriodChange}
            size="small"
          >
            <ToggleButton value="daily">Daily</ToggleButton>
            <ToggleButton value="weekly">Weekly</ToggleButton>
            <ToggleButton value="monthly">Monthly</ToggleButton>
          </ToggleButtonGroup>
          <Button variant="outlined" onClick={handleExport}>
            Export Report
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Summary Statistics
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Total Emails Processed
              </Typography>
              <Typography variant="h4">{summary?.total_emails || 0}</Typography>
            </Box>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Auto Replied
              </Typography>
              <Typography variant="h4" color="success.main">
                {summary?.auto_replied || 0}
              </Typography>
            </Box>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Pending Review
              </Typography>
              <Typography variant="h4" color="warning.main">
                {summary?.manual_review || 0}
              </Typography>
            </Box>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Failed
              </Typography>
              <Typography variant="h4" color="error.main">
                {summary?.failed || 0}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Performance Metrics
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Automation Rate
              </Typography>
              <Typography variant="h4">
                {insights?.automation_rate?.toFixed(1)}%
              </Typography>
            </Box>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Average Confidence
              </Typography>
              <Typography variant="h4">
                {summary?.avg_confidence?.toFixed(3) || 'N/A'}
              </Typography>
            </Box>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Average Processing Time
              </Typography>
              <Typography variant="h4">
                {summary?.avg_processing_time_ms
                  ? `${summary.avg_processing_time_ms.toFixed(0)}ms`
                  : 'N/A'}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Email Processing Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="Auto Replied" fill="#4CAF50" />
                <Bar dataKey="Pending Review" fill="#FF9800" />
                <Bar dataKey="Failed" fill="#F44336" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {insights?.recommendations && insights.recommendations.length > 0 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Recommendations
              </Typography>
              {insights.recommendations.map((rec, index) => (
                <Typography key={index} variant="body2" sx={{ mt: 1 }}>
                  • {rec}
                </Typography>
              ))}
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default Analytics;
