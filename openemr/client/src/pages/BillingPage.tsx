import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Visibility,
  Receipt,
  AttachMoney,
  TrendingUp,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import LoadingSpinner from '../components/Common/LoadingSpinner';

interface BillingRecord {
  id: string;
  patientName: string;
  serviceDate: string;
  serviceType: string;
  amount: number;
  status: 'pending' | 'paid' | 'overdue' | 'cancelled';
  invoiceNumber: string;
  medicalAid?: string;
}

const BillingPage: React.FC = () => {
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedBilling, setSelectedBilling] = useState<BillingRecord | null>(null);
  const [formData, setFormData] = useState({
    patientName: '',
    serviceType: '',
    amount: '',
    medicalAid: '',
  });

  // Mock data for now - replace with actual API calls
  const mockBillingData: BillingRecord[] = [
    {
      id: '1',
      patientName: 'John Doe',
      serviceDate: '2024-01-15',
      serviceType: 'X-Ray Chest',
      amount: 450.00,
      status: 'paid',
      invoiceNumber: 'INV-2024-001',
      medicalAid: 'Discovery Health',
    },
    {
      id: '2',
      patientName: 'Jane Smith',
      serviceDate: '2024-01-16',
      serviceType: 'CT Scan',
      amount: 1200.00,
      status: 'pending',
      invoiceNumber: 'INV-2024-002',
      medicalAid: 'Momentum Health',
    },
    {
      id: '3',
      patientName: 'Mike Johnson',
      serviceDate: '2024-01-14',
      serviceType: 'MRI Brain',
      amount: 2500.00,
      status: 'overdue',
      invoiceNumber: 'INV-2024-003',
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid': return 'success';
      case 'pending': return 'warning';
      case 'overdue': return 'error';
      case 'cancelled': return 'default';
      default: return 'default';
    }
  };

  const handleAddBilling = () => {
    setSelectedBilling(null);
    setFormData({
      patientName: '',
      serviceType: '',
      amount: '',
      medicalAid: '',
    });
    setOpenDialog(true);
  };

  const handleEditBilling = (billing: BillingRecord) => {
    setSelectedBilling(billing);
    setFormData({
      patientName: billing.patientName,
      serviceType: billing.serviceType,
      amount: billing.amount.toString(),
      medicalAid: billing.medicalAid || '',
    });
    setOpenDialog(true);
  };

  const handleSave = () => {
    // Validate required fields
    if (!formData.patientName || !formData.serviceType || !formData.amount) {
      alert('Please fill in all required fields');
      return;
    }
    
    console.log('Saving billing record:', formData);
    
    if (selectedBilling) {
      alert(`Invoice ${selectedBilling.invoiceNumber} updated successfully!`);
    } else {
      const newInvoiceNumber = `INV-2024-${String(mockBillingData.length + 1).padStart(3, '0')}`;
      alert(`New invoice ${newInvoiceNumber} created successfully!`);
    }
    
    setOpenDialog(false);
  };

  const handleDeleteBilling = (billingId: string) => {
    if (window.confirm('Are you sure you want to delete this invoice?')) {
      console.log('Deleting billing record:', billingId);
      alert('Invoice deleted successfully!');
    }
  };

  const handleViewBilling = (billingId: string) => {
    console.log('Viewing billing record:', billingId);
    alert('Opening invoice details...');
  };

  const totalRevenue = mockBillingData.reduce((sum, record) => sum + record.amount, 0);
  const paidAmount = mockBillingData
    .filter(record => record.status === 'paid')
    .reduce((sum, record) => sum + record.amount, 0);
  const pendingAmount = mockBillingData
    .filter(record => record.status === 'pending')
    .reduce((sum, record) => sum + record.amount, 0);

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          Billing Management
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleAddBilling}
        >
          New Invoice
        </Button>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <AttachMoney color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Revenue
                  </Typography>
                  <Typography variant="h5">
                    R {totalRevenue.toLocaleString()}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <TrendingUp color="success" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Paid Amount
                  </Typography>
                  <Typography variant="h5">
                    R {paidAmount.toLocaleString()}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Receipt color="warning" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Pending Amount
                  </Typography>
                  <Typography variant="h5">
                    R {pendingAmount.toLocaleString()}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Receipt color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Invoices
                  </Typography>
                  <Typography variant="h5">
                    {mockBillingData.length}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Billing Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Invoices
          </Typography>
          <TableContainer component={Paper} elevation={0}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Invoice #</TableCell>
                  <TableCell>Patient</TableCell>
                  <TableCell>Service</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell>Medical Aid</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {mockBillingData.map((record) => (
                  <TableRow key={record.id}>
                    <TableCell>{record.invoiceNumber}</TableCell>
                    <TableCell>{record.patientName}</TableCell>
                    <TableCell>{record.serviceType}</TableCell>
                    <TableCell>{new Date(record.serviceDate).toLocaleDateString()}</TableCell>
                    <TableCell>{record.medicalAid || 'Self Pay'}</TableCell>
                    <TableCell>R {record.amount.toLocaleString()}</TableCell>
                    <TableCell>
                      <Chip
                        label={record.status.toUpperCase()}
                        color={getStatusColor(record.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <IconButton size="small" onClick={() => handleEditBilling(record)}>
                        <Edit />
                      </IconButton>
                      <IconButton size="small" onClick={() => handleViewBilling(record.id)}>
                        <Visibility />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => handleDeleteBilling(record.id)}>
                        <Delete />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Add/Edit Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {selectedBilling ? 'Edit Invoice' : 'Create New Invoice'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Patient Name"
                  value={formData.patientName}
                  onChange={(e) => setFormData({ ...formData, patientName: e.target.value })}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Service Type"
                  value={formData.serviceType}
                  onChange={(e) => setFormData({ ...formData, serviceType: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Amount"
                  type="number"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Medical Aid"
                  value={formData.medicalAid}
                  onChange={(e) => setFormData({ ...formData, medicalAid: e.target.value })}
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">
            {selectedBilling ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default BillingPage;