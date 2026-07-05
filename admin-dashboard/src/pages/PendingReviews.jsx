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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
} from '@mui/material';
import { CheckCircle, Edit } from '@mui/icons-material';
import apiService from '../services/api';
import { toast } from 'react-toastify';
import { format } from 'date-fns';
import { useAuth } from '../context/AuthContext';

const PendingReviews = () => {
  const [loading, setLoading] = useState(true);
  const [emails, setEmails] = useState([]);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [response, setResponse] = useState('');
  const [sending, setSending] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    fetchEmails();
  }, []);

  const fetchEmails = async () => {
    try {
      setLoading(true);
      const res = await apiService.getPendingReviewEmails(50);
      setEmails(res.data.emails || []);
    } catch (error) {
      console.error('Error fetching pending emails:', error);
      toast.error('Failed to load pending emails');
    } finally {
      setLoading(false);
    }
  };

  const handleReviewClick = async (email) => {
    try {
      const detailsRes = await apiService.getEmailDetails(email.email_id);
      setSelectedEmail(detailsRes.data);

      if (detailsRes.data.responses && detailsRes.data.responses.length > 0) {
        setResponse(detailsRes.data.responses[0].response_text || '');
      } else {
        setResponse('');
      }

      setDialogOpen(true);
    } catch (error) {
      console.error('Error fetching email details:', error);
      toast.error('Failed to load email details');
    }
  };

  const handleSendResponse = async () => {
    if (!response.trim()) {
      toast.error('Please enter a response');
      return;
    }

    try {
      setSending(true);
      await apiService.approveAndSendResponse(selectedEmail.email.email_id, {
        response_text: response,
        custom_response: false,
      });

      toast.success('Response sent successfully');
      setDialogOpen(false);
      await fetchEmails();
    } catch (error) {
      console.error('Error sending response:', error);
      toast.error('Failed to send response');
    } finally {
      setSending(false);
    }
  };

  const handleGenerateCustomResponse = async () => {
    try {
      const instructions = prompt('Enter custom instructions for generating the response:');
      if (!instructions) return;

      const res = await apiService.generateCustomResponse(
        selectedEmail.email.email_id,
        instructions
      );
      setResponse(res.data.response || '');
      toast.success('Custom response generated');
    } catch (error) {
      console.error('Error generating custom response:', error);
      toast.error('Failed to generate custom response');
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
        Pending Reviews
      </Typography>
      <Typography variant="body2" color="textSecondary" gutterBottom>
        {emails.length} email(s) awaiting manual review
      </Typography>

      <TableContainer component={Paper} sx={{ mt: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Sender</TableCell>
              <TableCell>Subject</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Received</TableCell>
              <TableCell>Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {emails.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography variant="body2" color="textSecondary">
                    No emails pending review
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
                      label={email.confidence_score?.toFixed(3) || 'N/A'}
                      color={
                        email.confidence_score > 0.7
                          ? 'success'
                          : email.confidence_score > 0.4
                          ? 'warning'
                          : 'error'
                      }
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {email.processed_at
                      ? format(new Date(email.processed_at), 'MMM dd, yyyy HH:mm')
                      : 'N/A'}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="contained"
                      size="small"
                      startIcon={<Edit />}
                      onClick={() => handleReviewClick(email)}
                    >
                      Review
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Review and Send Response</DialogTitle>
        <DialogContent>
          {selectedEmail && (
            <Box>
              <Typography variant="subtitle2" color="textSecondary">
                From: {selectedEmail.email.sender}
              </Typography>
              <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                Subject: {selectedEmail.email.subject}
              </Typography>

              <Paper sx={{ p: 2, mt: 2, bgcolor: '#f5f5f5' }}>
                <Typography variant="body2" fontWeight="bold" gutterBottom>
                  Email Body:
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {selectedEmail.email.body}
                </Typography>
              </Paper>

              {selectedEmail.faq_matches && selectedEmail.faq_matches.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" fontWeight="bold" gutterBottom>
                    FAQ Matches:
                  </Typography>
                  {selectedEmail.faq_matches.map((match, index) => (
                    <Paper key={index} sx={{ p: 1, mt: 1, bgcolor: '#f9f9f9' }}>
                      <Typography variant="caption" color="textSecondary">
                        Similarity: {match.similarity_score?.toFixed(4)}
                      </Typography>
                      <Typography variant="body2">Q: {match.faq_question}</Typography>
                      <Typography variant="body2" color="textSecondary">
                        A: {match.faq_answer}
                      </Typography>
                    </Paper>
                  ))}
                </Box>
              )}

              <TextField
                label="Admin Email"
                value={user?.email || ''}
                fullWidth
                margin="normal"
                size="small"
                disabled
                helperText="Logged in as"
              />

              <TextField
                label="Response"
                value={response}
                onChange={(e) => setResponse(e.target.value)}
                multiline
                rows={6}
                fullWidth
                margin="normal"
              />

              <Button
                variant="outlined"
                size="small"
                onClick={handleGenerateCustomResponse}
                sx={{ mt: 1 }}
              >
                Generate Custom Response
              </Button>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSendResponse}
            disabled={sending}
            startIcon={sending ? <CircularProgress size={16} /> : <CheckCircle />}
          >
            {sending ? 'Sending...' : 'Approve & Send'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PendingReviews;
