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
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Avatar,
  Chip,
  InputAdornment,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Visibility,
  Search,
  Person,
  Phone,
  Email,
  LocationOn,
} from '@mui/icons-material';
import LoadingSpinner from '../components/Common/LoadingSpinner';

interface Patient {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  dateOfBirth: string;
  gender: 'male' | 'female' | 'other';
  address: string;
  medicalAid?: string;
  memberNumber?: string;
  status: 'active' | 'inactive';
  lastVisit?: string;
}

const PatientsPage: React.FC = () => {
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    dateOfBirth: '',
    gender: '',
    address: '',
    medicalAid: '',
    memberNumber: '',
  });

  // Mock data for now - replace with actual API calls
  const mockPatientsData: Patient[] = [
    {
      id: '1',
      firstName: 'John',
      lastName: 'Doe',
      email: 'john.doe@email.com',
      phone: '+27 11 123 4567',
      dateOfBirth: '1985-03-15',
      gender: 'male',
      address: '123 Main St, Johannesburg',
      medicalAid: 'Discovery Health',
      memberNumber: 'DH123456789',
      status: 'active',
      lastVisit: '2024-01-15',
    },
    {
      id: '2',
      firstName: 'Jane',
      lastName: 'Smith',
      email: 'jane.smith@email.com',
      phone: '+27 21 987 6543',
      dateOfBirth: '1990-07-22',
      gender: 'female',
      address: '456 Oak Ave, Cape Town',
      medicalAid: 'Momentum Health',
      memberNumber: 'MH987654321',
      status: 'active',
      lastVisit: '2024-01-16',
    },
    {
      id: '3',
      firstName: 'Mike',
      lastName: 'Johnson',
      email: 'mike.johnson@email.com',
      phone: '+27 31 555 0123',
      dateOfBirth: '1978-11-08',
      gender: 'male',
      address: '789 Pine Rd, Durban',
      status: 'inactive',
      lastVisit: '2023-12-10',
    },
  ];

  const filteredPatients = mockPatientsData.filter(patient =>
    `${patient.firstName} ${patient.lastName}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
    patient.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    patient.phone.includes(searchTerm)
  );

  const handleAddPatient = () => {
    setSelectedPatient(null);
    setFormData({
      firstName: '',
      lastName: '',
      email: '',
      phone: '',
      dateOfBirth: '',
      gender: '',
      address: '',
      medicalAid: '',
      memberNumber: '',
    });
    setOpenDialog(true);
  };

  const handleEditPatient = (patient: Patient) => {
    setSelectedPatient(patient);
    setFormData({
      firstName: patient.firstName,
      lastName: patient.lastName,
      email: patient.email,
      phone: patient.phone,
      dateOfBirth: patient.dateOfBirth,
      gender: patient.gender,
      address: patient.address,
      medicalAid: patient.medicalAid || '',
      memberNumber: patient.memberNumber || '',
    });
    setOpenDialog(true);
  };

  const handleSave = () => {
    // Validate required fields
    if (!formData.firstName || !formData.lastName || !formData.email || !formData.phone) {
      alert('Please fill in all required fields');
      return;
    }
    
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      alert('Please enter a valid email address');
      return;
    }
    
    console.log('Saving patient:', formData);
    
    if (selectedPatient) {
      alert(`Patient ${formData.firstName} ${formData.lastName} updated successfully!`);
    } else {
      alert(`New patient ${formData.firstName} ${formData.lastName} added successfully!`);
    }
    
    setOpenDialog(false);
  };

  const handleDeletePatient = (patientId: string) => {
    if (window.confirm('Are you sure you want to delete this patient? This action cannot be undone.')) {
      console.log('Deleting patient:', patientId);
      alert('Patient deleted successfully!');
    }
  };

  const handleViewPatient = (patientId: string) => {
    console.log('Viewing patient:', patientId);
    alert('Opening patient details...');
  };

  const getInitials = (firstName: string, lastName: string) => {
    return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
  };

  const calculateAge = (dateOfBirth: string) => {
    const today = new Date();
    const birthDate = new Date(dateOfBirth);
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          Patient Management
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleAddPatient}
        >
          Add Patient
        </Button>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Person color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Patients
                  </Typography>
                  <Typography variant="h5">
                    {mockPatientsData.length}
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
                <Person color="success" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Active Patients
                  </Typography>
                  <Typography variant="h5">
                    {mockPatientsData.filter(p => p.status === 'active').length}
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
                <Person color="warning" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    New This Month
                  </Typography>
                  <Typography variant="h5">
                    12
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
                <Person color="info" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Recent Visits
                  </Typography>
                  <Typography variant="h5">
                    {mockPatientsData.filter(p => p.lastVisit).length}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Search and Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <TextField
            fullWidth
            placeholder="Search patients by name, email, or phone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
        </CardContent>
      </Card>

      {/* Patients Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Patient Records ({filteredPatients.length})
          </Typography>
          <TableContainer component={Paper} elevation={0}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Patient</TableCell>
                  <TableCell>Contact</TableCell>
                  <TableCell>Age/Gender</TableCell>
                  <TableCell>Medical Aid</TableCell>
                  <TableCell>Last Visit</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredPatients.map((patient) => (
                  <TableRow key={patient.id}>
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
                          {getInitials(patient.firstName, patient.lastName)}
                        </Avatar>
                        <Box>
                          <Typography variant="subtitle2">
                            {patient.firstName} {patient.lastName}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            {patient.email}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box>
                        <Typography variant="body2" display="flex" alignItems="center">
                          <Phone sx={{ fontSize: 16, mr: 1 }} />
                          {patient.phone}
                        </Typography>
                        <Typography variant="body2" color="textSecondary" display="flex" alignItems="center">
                          <LocationOn sx={{ fontSize: 16, mr: 1 }} />
                          {patient.address}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {calculateAge(patient.dateOfBirth)} years
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        {patient.gender}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {patient.medicalAid ? (
                        <Box>
                          <Typography variant="body2">{patient.medicalAid}</Typography>
                          <Typography variant="body2" color="textSecondary">
                            {patient.memberNumber}
                          </Typography>
                        </Box>
                      ) : (
                        <Typography variant="body2" color="textSecondary">
                          Self Pay
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {patient.lastVisit ? (
                        new Date(patient.lastVisit).toLocaleDateString()
                      ) : (
                        <Typography variant="body2" color="textSecondary">
                          No visits
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={patient.status.toUpperCase()}
                        color={patient.status === 'active' ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <IconButton size="small" onClick={() => handleEditPatient(patient)}>
                        <Edit />
                      </IconButton>
                      <IconButton size="small" onClick={() => handleViewPatient(patient.id)}>
                        <Visibility />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => handleDeletePatient(patient.id)}>
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
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {selectedPatient ? 'Edit Patient' : 'Add New Patient'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="First Name"
                  value={formData.firstName}
                  onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Last Name"
                  value={formData.lastName}
                  onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Phone"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Date of Birth"
                  type="date"
                  value={formData.dateOfBirth}
                  onChange={(e) => setFormData({ ...formData, dateOfBirth: e.target.value })}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  label="Gender"
                  value={formData.gender}
                  onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                  SelectProps={{
                    native: true,
                  }}
                >
                  <option value="">Select Gender</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </TextField>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Address"
                  multiline
                  rows={2}
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
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
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Member Number"
                  value={formData.memberNumber}
                  onChange={(e) => setFormData({ ...formData, memberNumber: e.target.value })}
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">
            {selectedPatient ? 'Update' : 'Add Patient'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default PatientsPage;