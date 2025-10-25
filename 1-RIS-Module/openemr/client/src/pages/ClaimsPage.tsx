import React, { useState } from 'react';
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
  Tabs,
  Tab,
  LinearProgress,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Visibility,
  Send,
  CheckCircle,
  Error,
  Pending,
  AttachMoney,
  Description,
  Schedule,
} from '@mui/icons-material';
import LoadingSpinner from '../components/Common/LoadingSpinner';

interface Claim {
  id: string;
  claimNumber: string;
  patientName: string;
  medicalAid: string;
  memberNumber: string;
  serviceDate: string;
  submissionDate: string;
  amount: number;
  status: 'draft' | 'submitted' | 'processing' | 'approved' | 'rejected' | 'paid';
  serviceType: string;
  diagnosis: string;
  notes?: string;
  rejectionReason?: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const ClaimsPage: React.FC = () => {
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [formData, setFormData] = useState({
    patientName: '',
    medicalAid: '',
    memberNumber: '',
    serviceType: '',
    diagnosis: '',
    amount: '',
    notes: '',
  });

  // Mock data for claims
  const mockClaimsData: Claim[] = [
    {
      id: '1',
      claimNumber: 'CLM-2024-001',
      patientName: 'John Doe',
      medicalAid: 'Discovery Health',
      memberNumber: 'DH123456789',
      serviceDate: '2024-01-15',
      submissionDate: '2024-01-16',
      amount: 450.00,
      status: 'paid',
      serviceType: 'X-Ray Chest',
      diagnosis: 'Routine chest examination',
    },
    {
      id: '2',
      claimNumber: 'CLM-2024-002',
      patientName: 'Jane Smith',
      medicalAid: 'Momentum Health',
      memberNumber: 'MH987654321',
      serviceDate: '2024-01-16',
      submissionDate: '2024-01-17',
      amount: 1200.00,
      status: 'processing',
      serviceType: 'CT Scan Abdomen',
      diagnosis: 'Abdominal pain investigation',
    },
    {
      id: '3',
      claimNumber: 'CLM-2024-003',
      patientName: 'Mike Johnson',
      medicalAid: 'Bonitas',
      memberNumber: 'BN456789123',
      serviceDate: '2024-01-14',
      submissionDate: '2024-01-15',
      amount: 2500.00,
      status: 'rejected',
      serviceType: 'MRI Brain',
      diagnosis: 'Headache investigation',
      rejectionReason: 'Prior authorization required',
    },
    {
      id: '4',
      claimNumber: 'CLM-2024-004',
      patientName: 'Sarah Wilson',
      medicalAid: 'Medihelp',
      memberNumber: 'MH789123456',
      serviceDate: '2024-01-17',
      submissionDate: '2024-01-18',
      amount: 350.00,
      status: 'approved',
      serviceType: 'Ultrasound',
      diagnosis: 'Routine abdominal scan',
    },
    {
      id: '5',
      claimNumber: 'CLM-2024-005',
      patientName: 'David Brown',
      medicalAid: 'Discovery Health',
      memberNumber: 'DH321654987',
      serviceDate: '2024-01-18',
      submissionDate: '',
      amount: 800.00,
      status: 'draft',
      serviceType: 'CT Scan Chest',
      diagnosis: 'Follow-up scan',
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid': return 'success';
      case 'approved': return 'info';
      case 'processing': return 'warning';
      case 'submitted': return 'primary';
      case 'rejected': return 'error';
      case 'draft': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid': return <CheckCircle />;
      case 'approved': return <CheckCircle />;
      case 'processing': return <Schedule />;
      case 'submitted': return <Send />;
      case 'rejected': return <Error />;
      case 'draft': return <Description />;
      default: return <Pending />;
    }
  };

  const filterClaimsByStatus = (status?: string) => {
    if (!status) return mockClaimsData;
    return mockClaimsData.filter(claim => claim.status === status);
  };

  const handleAddClaim = () => {
    setSelectedClaim(null);
    setFormData({
      patientName: '',
      medicalAid: '',
      memberNumber: '',
      serviceType: '',
      diagnosis: '',
      amount: '',
      notes: '',
    });
    setOpenDialog(true);
  };

  const handleEditClaim = (claim: Claim) => {
    setSelectedClaim(claim);
    setFormData({
      patientName: claim.patientName,
      medicalAid: claim.medicalAid,
      memberNumber: claim.memberNumber,
      serviceType: claim.serviceType,
      diagnosis: claim.diagnosis,
      amount: claim.amount.toString(),
      notes: claim.notes || '',
    });
    setOpenDialog(true);
  };

  const handleSave = () => {
    // Validate required fields
    if (!formData.patientName || !formData.medicalAid || !formData.serviceType || !formData.amount) {
      alert('Please fill in all required fields');
      return;
    }
    
    console.log('Saving claim:', formData);
    
    if (selectedClaim) {
      alert(`Claim ${selectedClaim.claimNumber} updated successfully!`);
    } else {
      const newClaimNumber = `CLM-2024-${String(mockClaimsData.length + 1).padStart(3, '0')}`;
      alert(`New claim ${newClaimNumber} created successfully!`);
    }
    
    setOpenDialog(false);
  };

  const handleDeleteClaim = (claimId: string) => {
    if (window.confirm('Are you sure you want to delete this claim?')) {
      console.log('Deleting claim:', claimId);
      alert('Claim deleted successfully!');
    }
  };

  const handleSubmitClaim = (claimId: string) => {
    if (window.confirm('Are you sure you want to submit this claim?')) {
      console.log('Submitting claim:', claimId);
      alert('Claim submitted successfully!');
    }
  };

  const handleViewClaim = (claimId: string) => {
    console.log('Viewing claim:', claimId);
    alert('Opening claim details...');
  };

  const getTabData = () => {
    const all = mockClaimsData.length;
    const draft = filterClaimsByStatus('draft').length;
    const submitted = filterClaimsByStatus('submitted').length;
    const processing = filterClaimsByStatus('processing').length;
    const approved = filterClaimsByStatus('approved').length;
    const rejected = filterClaimsByStatus('rejected').length;
    const paid = filterClaimsByStatus('paid').length;

    return { all, draft, submitted, processing, approved, rejected, paid };
  };

  const tabData = getTabData();

  const totalClaimsValue = mockClaimsData.reduce((sum, claim) => sum + claim.amount, 0);
  const paidClaimsValue = mockClaimsData
    .filter(claim => claim.status === 'paid')
    .reduce((sum, claim) => sum + claim.amount, 0);
  const pendingClaimsValue = mockClaimsData
    .filter(claim => ['submitted', 'processing', 'approved'].includes(claim.status))
    .reduce((sum, claim) => sum + claim.amount, 0);

  const renderClaimsTable = (claims: Claim[]) => (
    <TableContainer component={Paper} elevation={0}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Claim #</TableCell>
            <TableCell>Patient</TableCell>
            <TableCell>Medical Aid</TableCell>
            <TableCell>Service</TableCell>
            <TableCell>Service Date</TableCell>
            <TableCell>Amount</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {claims.map((claim) => (
            <TableRow key={claim.id}>
              <TableCell>
                <Typography variant="subtitle2" fontWeight="bold">
                  {claim.claimNumber}
                </Typography>
                {claim.submissionDate && (
                  <Typography variant="caption" color="textSecondary">
                    Submitted: {new Date(claim.submissionDate).toLocaleDateString()}
                  </Typography>
                )}
              </TableCell>
              <TableCell>
                <Typography variant="body2">{claim.patientName}</Typography>
                <Typography variant="caption" color="textSecondary">
                  {claim.memberNumber}
                </Typography>
              </TableCell>
              <TableCell>{claim.medicalAid}</TableCell>
              <TableCell>
                <Typography variant="body2">{claim.serviceType}</Typography>
                <Typography variant="caption" color="textSecondary">
                  {claim.diagnosis}
                </Typography>
              </TableCell>
              <TableCell>
                {new Date(claim.serviceDate).toLocaleDateString()}
              </TableCell>
              <TableCell>
                <Typography variant="body2" fontWeight="bold">
                  R {claim.amount.toLocaleString()}
                </Typography>
              </TableCell>
              <TableCell>
                <Box display="flex" alignItems="center">
                  {getStatusIcon(claim.status)}
                  <Chip
                    label={claim.status.toUpperCase()}
                    color={getStatusColor(claim.status) as any}
                    size="small"
                    sx={{ ml: 1 }}
                  />
                </Box>
                {claim.rejectionReason && (
                  <Typography variant="caption" color="error" display="block">
                    {claim.rejectionReason}
                  </Typography>
                )}
              </TableCell>
              <TableCell>
                <IconButton size="small" onClick={() => handleEditClaim(claim)}>
                  <Edit />
                </IconButton>
                <IconButton size="small" onClick={() => handleViewClaim(claim.id)}>
                  <Visibility />
                </IconButton>
                {claim.status === 'draft' && (
                  <IconButton size="small" color="primary" onClick={() => handleSubmitClaim(claim.id)}>
                    <Send />
                  </IconButton>
                )}
                <IconButton size="small" color="error" onClick={() => handleDeleteClaim(claim.id)}>
                  <Delete />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          Claims Management
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleAddClaim}
        >
          New Claim
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
                    Total Claims Value
                  </Typography>
                  <Typography variant="h5">
                    R {totalClaimsValue.toLocaleString()}
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
                <CheckCircle color="success" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Paid Claims
                  </Typography>
                  <Typography variant="h5">
                    R {paidClaimsValue.toLocaleString()}
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
                <Schedule color="warning" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Pending Claims
                  </Typography>
                  <Typography variant="h5">
                    R {pendingClaimsValue.toLocaleString()}
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
                <Description color="info" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Claims
                  </Typography>
                  <Typography variant="h5">
                    {mockClaimsData.length}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Claims Processing Progress */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Claims Processing Overview
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Box>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Payment Success Rate</Typography>
                  <Typography variant="body2">
                    {Math.round((tabData.paid / tabData.all) * 100)}%
                  </Typography>
                </Box>
                <LinearProgress 
                  variant="determinate" 
                  value={(tabData.paid / tabData.all) * 100} 
                  color="success"
                />
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Processing Efficiency</Typography>
                  <Typography variant="body2">
                    {Math.round(((tabData.paid + tabData.approved) / tabData.all) * 100)}%
                  </Typography>
                </Box>
                <LinearProgress 
                  variant="determinate" 
                  value={((tabData.paid + tabData.approved) / tabData.all) * 100} 
                  color="info"
                />
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Claims Table with Tabs */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs 
            value={tabValue} 
            onChange={(e, newValue) => setTabValue(newValue)}
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab label={`All Claims (${tabData.all})`} />
            <Tab label={`Draft (${tabData.draft})`} />
            <Tab label={`Submitted (${tabData.submitted})`} />
            <Tab label={`Processing (${tabData.processing})`} />
            <Tab label={`Approved (${tabData.approved})`} />
            <Tab label={`Rejected (${tabData.rejected})`} />
            <Tab label={`Paid (${tabData.paid})`} />
          </Tabs>
        </Box>
        
        <TabPanel value={tabValue} index={0}>
          {renderClaimsTable(mockClaimsData)}
        </TabPanel>
        <TabPanel value={tabValue} index={1}>
          {renderClaimsTable(filterClaimsByStatus('draft'))}
        </TabPanel>
        <TabPanel value={tabValue} index={2}>
          {renderClaimsTable(filterClaimsByStatus('submitted'))}
        </TabPanel>
        <TabPanel value={tabValue} index={3}>
          {renderClaimsTable(filterClaimsByStatus('processing'))}
        </TabPanel>
        <TabPanel value={tabValue} index={4}>
          {renderClaimsTable(filterClaimsByStatus('approved'))}
        </TabPanel>
        <TabPanel value={tabValue} index={5}>
          {renderClaimsTable(filterClaimsByStatus('rejected'))}
        </TabPanel>
        <TabPanel value={tabValue} index={6}>
          {renderClaimsTable(filterClaimsByStatus('paid'))}
        </TabPanel>
      </Card>

      {/* Add/Edit Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {selectedClaim ? 'Edit Claim' : 'Create New Claim'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Patient Name"
                  value={formData.patientName}
                  onChange={(e) => setFormData({ ...formData, patientName: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Medical Aid</InputLabel>
                  <Select
                    value={formData.medicalAid}
                    label="Medical Aid"
                    onChange={(e) => setFormData({ ...formData, medicalAid: e.target.value })}
                  >
                    <MenuItem value="Discovery Health">Discovery Health</MenuItem>
                    <MenuItem value="Momentum Health">Momentum Health</MenuItem>
                    <MenuItem value="Bonitas">Bonitas</MenuItem>
                    <MenuItem value="Medihelp">Medihelp</MenuItem>
                    <MenuItem value="Bestmed">Bestmed</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Member Number"
                  value={formData.memberNumber}
                  onChange={(e) => setFormData({ ...formData, memberNumber: e.target.value })}
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
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Service Type"
                  value={formData.serviceType}
                  onChange={(e) => setFormData({ ...formData, serviceType: e.target.value })}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Diagnosis"
                  value={formData.diagnosis}
                  onChange={(e) => setFormData({ ...formData, diagnosis: e.target.value })}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Additional Notes"
                  multiline
                  rows={3}
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">
            {selectedClaim ? 'Update Claim' : 'Create Claim'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ClaimsPage;