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
  Avatar,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Visibility,
  LocalHospital,
  Schedule,
  Assignment,
  CheckCircle,
  Pending,
  Cancel,
} from '@mui/icons-material';


interface StudyOrder {
  id: string;
  orderNumber: string;
  patientName: string;
  patientId: string;
  studyType: string;
  priority: 'routine' | 'urgent' | 'stat';
  status: 'pending' | 'scheduled' | 'in-progress' | 'completed' | 'cancelled';
  orderDate: string;
  scheduledDate?: string;
  completedDate?: string;
  referringPhysician: string;
  notes?: string;
  bodyPart: string;
  contrast: boolean;
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

const StudyOrdersPage: React.FC = () => {
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<StudyOrder | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [formData, setFormData] = useState({
    patientName: '',
    studyType: '',
    priority: '',
    referringPhysician: '',
    bodyPart: '',
    contrast: false,
    notes: '',
  });

  // Mock data for study orders
  const mockStudyOrders: StudyOrder[] = [
    {
      id: '1',
      orderNumber: 'SO-2024-001',
      patientName: 'John Doe',
      patientId: 'P001',
      studyType: 'X-Ray',
      priority: 'routine',
      status: 'completed',
      orderDate: '2024-01-15',
      scheduledDate: '2024-01-16',
      completedDate: '2024-01-16',
      referringPhysician: 'Dr. Smith',
      bodyPart: 'Chest',
      contrast: false,
      notes: 'Follow-up chest X-ray',
    },
    {
      id: '2',
      orderNumber: 'SO-2024-002',
      patientName: 'Jane Smith',
      patientId: 'P002',
      studyType: 'CT Scan',
      priority: 'urgent',
      status: 'scheduled',
      orderDate: '2024-01-16',
      scheduledDate: '2024-01-17',
      referringPhysician: 'Dr. Johnson',
      bodyPart: 'Abdomen',
      contrast: true,
      notes: 'Abdominal pain investigation',
    },
    {
      id: '3',
      orderNumber: 'SO-2024-003',
      patientName: 'Mike Johnson',
      patientId: 'P003',
      studyType: 'MRI',
      priority: 'stat',
      status: 'in-progress',
      orderDate: '2024-01-17',
      scheduledDate: '2024-01-17',
      referringPhysician: 'Dr. Brown',
      bodyPart: 'Brain',
      contrast: true,
      notes: 'Emergency brain scan',
    },
    {
      id: '4',
      orderNumber: 'SO-2024-004',
      patientName: 'Sarah Wilson',
      patientId: 'P004',
      studyType: 'Ultrasound',
      priority: 'routine',
      status: 'pending',
      orderDate: '2024-01-17',
      referringPhysician: 'Dr. Davis',
      bodyPart: 'Abdomen',
      contrast: false,
      notes: 'Routine abdominal ultrasound',
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'in-progress': return 'info';
      case 'scheduled': return 'warning';
      case 'pending': return 'default';
      case 'cancelled': return 'error';
      default: return 'default';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'stat': return 'error';
      case 'urgent': return 'warning';
      case 'routine': return 'success';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle />;
      case 'in-progress': return <Schedule />;
      case 'scheduled': return <Assignment />;
      case 'pending': return <Pending />;
      case 'cancelled': return <Cancel />;
      default: return <Pending />;
    }
  };

  const filterOrdersByStatus = (status?: string) => {
    if (!status) return mockStudyOrders;
    return mockStudyOrders.filter(order => order.status === status);
  };

  const handleAddOrder = () => {
    setSelectedOrder(null);
    setFormData({
      patientName: '',
      studyType: '',
      priority: '',
      referringPhysician: '',
      bodyPart: '',
      contrast: false,
      notes: '',
    });
    setOpenDialog(true);
  };

  const handleEditOrder = (order: StudyOrder) => {
    setSelectedOrder(order);
    setFormData({
      patientName: order.patientName,
      studyType: order.studyType,
      priority: order.priority,
      referringPhysician: order.referringPhysician,
      bodyPart: order.bodyPart,
      contrast: order.contrast,
      notes: order.notes || '',
    });
    setOpenDialog(true);
  };

  const handleSave = () => {
    // Validate required fields
    if (!formData.patientName || !formData.studyType || !formData.priority || !formData.referringPhysician) {
      alert('Please fill in all required fields');
      return;
    }
    
    console.log('Saving study order:', formData);
    
    if (selectedOrder) {
      alert(`Study order ${selectedOrder.orderNumber} updated successfully!`);
    } else {
      const newOrderNumber = `SO-2024-${String(mockStudyOrders.length + 1).padStart(3, '0')}`;
      alert(`New study order ${newOrderNumber} created successfully!`);
    }
    
    setOpenDialog(false);
  };

  const handleDeleteOrder = (orderId: string) => {
    if (window.confirm('Are you sure you want to delete this study order?')) {
      console.log('Deleting study order:', orderId);
      alert('Study order deleted successfully!');
    }
  };

  const handleViewOrder = (orderId: string) => {
    console.log('Viewing study order:', orderId);
    alert('Opening study order details...');
  };

  const getTabData = () => {
    const all = mockStudyOrders.length;
    const pending = filterOrdersByStatus('pending').length;
    const scheduled = filterOrdersByStatus('scheduled').length;
    const inProgress = filterOrdersByStatus('in-progress').length;
    const completed = filterOrdersByStatus('completed').length;

    return { all, pending, scheduled, inProgress, completed };
  };

  const tabData = getTabData();

  const renderOrdersTable = (orders: StudyOrder[]) => (
    <TableContainer component={Paper} elevation={0}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Order #</TableCell>
            <TableCell>Patient</TableCell>
            <TableCell>Study Type</TableCell>
            <TableCell>Body Part</TableCell>
            <TableCell>Priority</TableCell>
            <TableCell>Physician</TableCell>
            <TableCell>Order Date</TableCell>
            <TableCell>Scheduled</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {orders.map((order) => (
            <TableRow key={order.id}>
              <TableCell>
                <Typography variant="subtitle2" fontWeight="bold">
                  {order.orderNumber}
                </Typography>
              </TableCell>
              <TableCell>
                <Box display="flex" alignItems="center">
                  <Avatar sx={{ mr: 2, bgcolor: 'primary.main', width: 32, height: 32 }}>
                    {order.patientName.split(' ').map(n => n[0]).join('')}
                  </Avatar>
                  <Box>
                    <Typography variant="body2">{order.patientName}</Typography>
                    <Typography variant="caption" color="textSecondary">
                      ID: {order.patientId}
                    </Typography>
                  </Box>
                </Box>
              </TableCell>
              <TableCell>
                <Typography variant="body2">{order.studyType}</Typography>
                {order.contrast && (
                  <Chip label="With Contrast" size="small" color="info" sx={{ mt: 0.5 }} />
                )}
              </TableCell>
              <TableCell>{order.bodyPart}</TableCell>
              <TableCell>
                <Chip
                  label={order.priority.toUpperCase()}
                  color={getPriorityColor(order.priority) as any}
                  size="small"
                />
              </TableCell>
              <TableCell>{order.referringPhysician}</TableCell>
              <TableCell>
                {new Date(order.orderDate).toLocaleDateString()}
              </TableCell>
              <TableCell>
                {order.scheduledDate ? (
                  new Date(order.scheduledDate).toLocaleDateString()
                ) : (
                  <Typography variant="body2" color="textSecondary">
                    Not scheduled
                  </Typography>
                )}
              </TableCell>
              <TableCell>
                <Box display="flex" alignItems="center">
                  {getStatusIcon(order.status)}
                  <Chip
                    label={order.status.replace('-', ' ').toUpperCase()}
                    color={getStatusColor(order.status) as any}
                    size="small"
                    sx={{ ml: 1 }}
                  />
                </Box>
              </TableCell>
              <TableCell>
                <IconButton size="small" onClick={() => handleEditOrder(order)}>
                  <Edit />
                </IconButton>
                <IconButton size="small" onClick={() => handleViewOrder(order.id)}>
                  <Visibility />
                </IconButton>
                <IconButton size="small" color="error" onClick={() => handleDeleteOrder(order.id)}>
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
          Study Orders Management
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleAddOrder}
        >
          New Study Order
        </Button>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Assignment color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Orders
                  </Typography>
                  <Typography variant="h5">
                    {tabData.all}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Pending sx={{ mr: 2, color: 'text.secondary' }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Pending
                  </Typography>
                  <Typography variant="h5">
                    {tabData.pending}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Schedule color="warning" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Scheduled
                  </Typography>
                  <Typography variant="h5">
                    {tabData.scheduled}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <LocalHospital color="info" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    In Progress
                  </Typography>
                  <Typography variant="h5">
                    {tabData.inProgress}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <CheckCircle color="success" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Completed
                  </Typography>
                  <Typography variant="h5">
                    {tabData.completed}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Orders Table with Tabs */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
            <Tab label={`All Orders (${tabData.all})`} />
            <Tab label={`Pending (${tabData.pending})`} />
            <Tab label={`Scheduled (${tabData.scheduled})`} />
            <Tab label={`In Progress (${tabData.inProgress})`} />
            <Tab label={`Completed (${tabData.completed})`} />
          </Tabs>
        </Box>
        
        <TabPanel value={tabValue} index={0}>
          {renderOrdersTable(mockStudyOrders)}
        </TabPanel>
        <TabPanel value={tabValue} index={1}>
          {renderOrdersTable(filterOrdersByStatus('pending'))}
        </TabPanel>
        <TabPanel value={tabValue} index={2}>
          {renderOrdersTable(filterOrdersByStatus('scheduled'))}
        </TabPanel>
        <TabPanel value={tabValue} index={3}>
          {renderOrdersTable(filterOrdersByStatus('in-progress'))}
        </TabPanel>
        <TabPanel value={tabValue} index={4}>
          {renderOrdersTable(filterOrdersByStatus('completed'))}
        </TabPanel>
      </Card>

      {/* Add/Edit Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {selectedOrder ? 'Edit Study Order' : 'Create New Study Order'}
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
                  <InputLabel>Study Type</InputLabel>
                  <Select
                    value={formData.studyType}
                    label="Study Type"
                    onChange={(e) => setFormData({ ...formData, studyType: e.target.value })}
                  >
                    <MenuItem value="X-Ray">X-Ray</MenuItem>
                    <MenuItem value="CT Scan">CT Scan</MenuItem>
                    <MenuItem value="MRI">MRI</MenuItem>
                    <MenuItem value="Ultrasound">Ultrasound</MenuItem>
                    <MenuItem value="Mammography">Mammography</MenuItem>
                    <MenuItem value="Nuclear Medicine">Nuclear Medicine</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Body Part"
                  value={formData.bodyPart}
                  onChange={(e) => setFormData({ ...formData, bodyPart: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Priority</InputLabel>
                  <Select
                    value={formData.priority}
                    label="Priority"
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                  >
                    <MenuItem value="routine">Routine</MenuItem>
                    <MenuItem value="urgent">Urgent</MenuItem>
                    <MenuItem value="stat">STAT</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Referring Physician"
                  value={formData.referringPhysician}
                  onChange={(e) => setFormData({ ...formData, referringPhysician: e.target.value })}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Clinical Notes"
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
            {selectedOrder ? 'Update Order' : 'Create Order'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default StudyOrdersPage;