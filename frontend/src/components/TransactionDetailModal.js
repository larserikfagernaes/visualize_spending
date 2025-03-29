import React, { useState } from 'react';
import {
  Modal,
  Box,
  Typography,
  Button,
  Tabs,
  Tab,
  Paper,
  Divider,
  IconButton,
  Chip,
  CircularProgress
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

const TabPanel = (props) => {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 2 }}>
          {children}
        </Box>
      )}
    </div>
  );
};

const TransactionDetailModal = ({ open, onClose, transaction }) => {
  const [tabValue, setTabValue] = useState(0);
  const [copySuccess, setCopySuccess] = useState('');

  if (!transaction) {
    return null;
  }

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleCopyJson = (data) => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopySuccess('Copied!');
    setTimeout(() => setCopySuccess(''), 2000);
  };

  // Format amount with Norwegian locale
  const formatAmount = (amount) => {
    if (amount === undefined || amount === null) return '0.00';
    try {
      return new Intl.NumberFormat('nb-NO', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount);
    } catch (error) {
      console.error('Error formatting amount:', error);
      return '0.00';
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('nb-NO').format(date);
    } catch (error) {
      console.error('Error formatting date:', error);
      return '';
    }
  };

  // Check if transaction is in loading state
  const isLoading = transaction._loading === true;
  const hasError = transaction._error !== undefined;

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="transaction-detail-modal"
    >
      <Box sx={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: { xs: '90%', sm: '80%', md: '70%' },
        maxWidth: 900,
        maxHeight: '90vh',
        overflow: 'auto',
        bgcolor: 'background.paper',
        borderRadius: 1,
        boxShadow: 24,
        p: 0,
      }}>
        <Box sx={{ 
          p: 2, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          bgcolor: 'primary.main',
          color: 'primary.contrastText'
        }}>
          <Typography variant="h6" component="h2">
            Transaction Details
          </Typography>
          <IconButton onClick={onClose} color="inherit" size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        <Box sx={{ p: 3 }}>
          <Box sx={{ mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              {transaction.description}
            </Typography>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2 }}>
              <Chip 
                label={`Amount: ${formatAmount(transaction.amount)} kr`} 
                color={transaction.amount < 0 ? "error" : "success"}
                variant="outlined"
              />
              <Chip label={`Date: ${formatDate(transaction.date)}`} variant="outlined" />
              <Chip label={`Bank Account: ${transaction.bank_account_id || 'Unknown'}`} variant="outlined" />
              {transaction.is_internal_transfer && <Chip label="Internal Transfer" color="warning" />}
              {transaction.is_wage_transfer && <Chip label="Wage Transfer" color="info" />}
              {transaction.is_tax_transfer && <Chip label="Tax Transfer" color="secondary" />}
            </Box>
          </Box>

          <Divider sx={{ mb: 2 }} />

          {isLoading && (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', my: 4 }}>
              <CircularProgress size={40} />
              <Typography variant="body1" sx={{ mt: 2 }}>
                Loading transaction details...
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                This may take a moment as we retrieve the transaction data.
              </Typography>
            </Box>
          )}

          {hasError && (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', my: 4, color: 'error.main' }}>
              <ErrorOutlineIcon sx={{ fontSize: 40 }} />
              <Typography variant="body1" sx={{ mt: 2, textAlign: 'center', maxWidth: '80%' }}>
                {transaction._error}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center', maxWidth: '80%' }}>
                The transaction data might not be available in the database. 
                This can happen for older transactions imported before raw data collection was implemented.
              </Typography>
              <Button 
                variant="outlined" 
                color="primary" 
                sx={{ mt: 2 }}
                onClick={onClose}
              >
                Close
              </Button>
            </Box>
          )}

          {!isLoading && !hasError && (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="subtitle1">
                  Raw Transaction Data
                </Typography>
                <Box>
                  {copySuccess && <Chip label={copySuccess} color="success" size="small" sx={{ mr: 1 }} />}
                  <Button 
                    startIcon={<ContentCopyIcon />}
                    size="small"
                    onClick={() => handleCopyJson(transaction.raw_data)}
                    variant="outlined"
                    disabled={!transaction.raw_data}
                  >
                    Copy JSON
                  </Button>
                </Box>
              </Box>

              {transaction.raw_data ? (
                <Paper variant="outlined" sx={{ mb: 3 }}>
                  <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <Tabs value={tabValue} onChange={handleTabChange} aria-label="transaction data tabs">
                      <Tab label="Overview" />
                      <Tab label="Transaction" />
                      <Tab label="Detailed Data" />
                      <Tab label="Processed Data" />
                    </Tabs>
                  </Box>

                  <TabPanel value={tabValue} index={0}>
                    <Box sx={{ 
                      '& pre': { 
                        overflow: 'auto', 
                        maxHeight: '50vh',
                        bgcolor: '#f5f5f5', 
                        p: 2, 
                        borderRadius: 1,
                        fontSize: '0.85rem'
                      } 
                    }}>
                      <pre>{JSON.stringify(transaction.raw_data, null, 2)}</pre>
                    </Box>
                  </TabPanel>

                  <TabPanel value={tabValue} index={1}>
                    {transaction.raw_data?.transaction ? (
                      <Box sx={{ 
                        '& pre': { 
                          overflow: 'auto', 
                          maxHeight: '50vh',
                          bgcolor: '#f5f5f5', 
                          p: 2, 
                          borderRadius: 1,
                          fontSize: '0.85rem'
                        } 
                      }}>
                        <pre>{JSON.stringify(transaction.raw_data.transaction, null, 2)}</pre>
                      </Box>
                    ) : (
                      <Typography color="text.secondary">No transaction data available.</Typography>
                    )}
                  </TabPanel>

                  <TabPanel value={tabValue} index={2}>
                    {transaction.raw_data?.detailed_data ? (
                      <Box sx={{ 
                        '& pre': { 
                          overflow: 'auto', 
                          maxHeight: '50vh',
                          bgcolor: '#f5f5f5', 
                          p: 2, 
                          borderRadius: 1,
                          fontSize: '0.85rem'
                        } 
                      }}>
                        <pre>{JSON.stringify(transaction.raw_data.detailed_data, null, 2)}</pre>
                      </Box>
                    ) : (
                      <Typography color="text.secondary">No detailed data available.</Typography>
                    )}
                  </TabPanel>

                  <TabPanel value={tabValue} index={3}>
                    {transaction.raw_data?.processed_data ? (
                      <Box sx={{ 
                        '& pre': { 
                          overflow: 'auto', 
                          maxHeight: '50vh',
                          bgcolor: '#f5f5f5', 
                          p: 2, 
                          borderRadius: 1,
                          fontSize: '0.85rem'
                        } 
                      }}>
                        <pre>{JSON.stringify(transaction.raw_data.processed_data, null, 2)}</pre>
                      </Box>
                    ) : (
                      <Typography color="text.secondary">No processed data available.</Typography>
                    )}
                  </TabPanel>
                </Paper>
              ) : (
                <Box sx={{ p: 3, textAlign: 'center', bgcolor: '#f5f5f5', borderRadius: 1, mb: 3 }}>
                  <Typography color="text.secondary" gutterBottom>
                    No raw transaction data is available for this transaction.
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    This transaction was imported without the detailed data or the data could not be found in the cache.
                  </Typography>
                </Box>
              )}

              <Button onClick={onClose} variant="contained">
                Close
              </Button>
            </>
          )}
        </Box>
      </Box>
    </Modal>
  );
};

export default TransactionDetailModal; 