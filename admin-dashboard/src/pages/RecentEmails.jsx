import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from '@mui/material';
import apiService from '../services/api';
import { toast } from 'react-toastify';
import { format } from 'date-fns';

const RecentEmails = () => {
  const [loading, setLoading] = useState(true);
  const [emails, setEmails] = useState([]);

  useEffect(() => {
    fetchEmails();
  }, []);

  const fetchEmails = async () => {
    try {
      setLoading(true);
      const res = await apiService.getRecentEmails(50);
      setEmails(res.data.emails);
    } catch (error) {
      console.error('Error fetching recent emails:', error);
      toast.error('Failed to load recent emails');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'pending_review':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
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
        Recent Emails
      </Typography>
      <Typography variant="body2" color="textSecondary" gutterBottom>
        {emails.length} recently processed email(s)
      </Typography>

      <TableContainer component={Paper} sx={{ mt: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Sender</TableCell>
              <TableCell>Subject</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Response Sent</TableCell>
              <TableCell>Processed At</TableCell>
              <TableCell>Processing Time</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {emails.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography variant="body2" color="textSecondary">
                    No emails found
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              emails.map((email) => (
                <TableRow key={email.id}>
                  <TableCell>{email.sender}</TableCell>
                  <TableCell>{email.subject}</TableCell>
                  <TableCell>
                    <Chip
                      label={email.status}
                      color={getStatusColor(email.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {email.confidence_score !== null
                      ? email.confidence_score.toFixed(3)
                      : 'N/A'}
                  </TableCell>
                  <TableCell>
                    {email.response_sent ? (
                      <Chip label="Yes" color="success" size="small" />
                    ) : (
                      <Chip label="No" color="default" size="small" />
                    )}
                  </TableCell>
                  <TableCell>
                    {email.processed_at
                      ? format(new Date(email.processed_at), 'MMM dd, yyyy HH:mm')
                      : 'N/A'}
                  </TableCell>
                  <TableCell>
                    {email.processing_time_ms
                      ? `${email.processing_time_ms}ms`
                      : 'N/A'}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default RecentEmails;
