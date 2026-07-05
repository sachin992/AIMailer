import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  CircularProgress,
  Card,
  CardContent,
} from '@mui/material';
import {
  Email as EmailIcon,
  CheckCircle as CheckIcon,
  RateReview as ReviewIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import apiService from '../services/api';
import { toast } from 'react-toastify';

const StatCard = ({ title, value, icon, color }) => (
  <Card>
    <CardContent>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography color="textSecondary" gutterBottom variant="body2">
            {title}
          </Typography>
          <Typography variant="h4">{value}</Typography>
        </Box>
        <Box sx={{ color, fontSize: 48 }}>{icon}</Box>
      </Box>
    </CardContent>
  </Card>
);

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [insights, setInsights] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [analyticsRes, insightsRes] = await Promise.all([
        apiService.getAnalyticsSummary('weekly'),
        apiService.getPerformanceInsights(),
      ]);

      setStats(analyticsRes.data.summary);
      setInsights(insightsRes.data.insights);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Emails"
            value={stats?.total_emails || 0}
            icon={<EmailIcon />}
            color="#2196F3"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Auto Replied"
            value={stats?.auto_replied || 0}
            icon={<CheckIcon />}
            color="#4CAF50"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Pending Review"
            value={stats?.manual_review || 0}
            icon={<ReviewIcon />}
            color="#FF9800"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Failed"
            value={stats?.failed || 0}
            icon={<ErrorIcon />}
            color="#F44336"
          />
        </Grid>
      </Grid>

      {insights && (
        <Grid container spacing={3} sx={{ mt: 2 }}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Performance Metrics
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="textSecondary">
                  Automation Rate
                </Typography>
                <Typography variant="h5">
                  {insights.automation_rate?.toFixed(1)}%
                </Typography>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="textSecondary">
                  Average Confidence
                </Typography>
                <Typography variant="h5">
                  {insights.avg_confidence?.toFixed(3)}
                </Typography>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="textSecondary">
                  Avg Processing Time
                </Typography>
                <Typography variant="h5">
                  {insights.avg_processing_time_seconds?.toFixed(2)}s
                </Typography>
              </Box>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Recommendations
              </Typography>
              {insights.recommendations && insights.recommendations.length > 0 ? (
                insights.recommendations.map((rec, index) => (
                  <Typography key={index} variant="body2" sx={{ mt: 1 }}>
                    • {rec}
                  </Typography>
                ))
              ) : (
                <Typography variant="body2" color="textSecondary">
                  No recommendations at this time. System is performing optimally.
                </Typography>
              )}
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default Dashboard;
