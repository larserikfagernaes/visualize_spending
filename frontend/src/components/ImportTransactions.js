import React, { useState } from 'react';
import { 
  Button, 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  CircularProgress, 
  Alert, 
  Snackbar 
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const ImportTransactions = ({ onImport }) => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ open: false, text: '', severity: 'success' });

  const handleImport = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/import/`);
      setMessage({
        open: true,
        text: `Successfully imported ${response.data.count} transactions`,
        severity: 'success'
      });
      if (onImport) onImport();
    } catch (error) {
      console.error('Error importing transactions:', error);
      setMessage({
        open: true,
        text: error.response?.data?.error || 'Failed to import transactions',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCloseMessage = () => {
    setMessage({ ...message, open: false });
  };

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Import Transactions
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Import transactions from JSON files in the data directory
        </Typography>
        <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
          <Button
            variant="contained"
            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <CloudUploadIcon />}
            onClick={handleImport}
            disabled={loading}
          >
            {loading ? 'Importing...' : 'Import Transactions'}
          </Button>
        </Box>
        <Snackbar 
          open={message.open} 
          autoHideDuration={6000} 
          onClose={handleCloseMessage}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
          <Alert onClose={handleCloseMessage} severity={message.severity}>
            {message.text}
          </Alert>
        </Snackbar>
      </CardContent>
    </Card>
  );
};

export default ImportTransactions; 