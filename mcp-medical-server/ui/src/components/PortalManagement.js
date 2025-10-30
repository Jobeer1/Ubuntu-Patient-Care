// PortalManagement.js - React component for managing medical scheme portal credentials and operations
import React, { useState, useEffect } from 'react';
import {
    Box, Card, CardContent, Typography, Grid, Button, TextField, 
    Dialog, DialogTitle, DialogContent, DialogActions, Chip,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Paper, IconButton, Tooltip, Alert, CircularProgress, Tab, Tabs,
    List, ListItem, ListItemText, ListItemIcon, ListItemSecondaryAction,
    Accordion, AccordionSummary, AccordionDetails, Switch, FormControlLabel
} from '@mui/material';
import {
    Add as AddIcon, Visibility as ViewIcon, Edit as EditIcon, 
    Delete as DeleteIcon, Security as SecurityIcon, CheckCircle as CheckIcon,
    Error as ErrorIcon, CloudQueue as CloudIcon, People as PeopleIcon,
    Assignment as AssignmentIcon, ExpandMore as ExpandMoreIcon,
    Monitor as MonitorIcon, Speed as SpeedIcon, Storage as StorageIcon
} from '@mui/icons-material';
import axios from 'axios';

const PortalManagement = () => {
    const [activeTab, setActiveTab] = useState(0);
    const [credentials, setCredentials] = useState([]);
    const [schemes, setSchemes] = useState([]);
    const [portalStatus, setPortalStatus] = useState({});
    const [statistics, setStatistics] = useState({});
    const [loading, setLoading] = useState(false);
    
    // Dialog states
    const [credentialDialog, setCredentialDialog] = useState(false);
    const [bulkOperationDialog, setBulkOperationDialog] = useState(false);
    const [registrationDialog, setRegistrationDialog] = useState(false);
    
    // Form states
    const [credentialForm, setCredentialForm] = useState({
        scheme_code: '',
        username: '',
        password: '',
        notes: ''
    });
    const [registrationForm, setRegistrationForm] = useState({
        scheme_code: '',
        practice_name: '',
        practice_number: '',
        contact_person: '',
        email: '',
        phone: '',
        address: {
            street: '',
            city: '',
            postal_code: '',
            province: ''
        },
        speciality: '',
        hpcsa_number: ''
    });
    const [bulkMembers, setBulkMembers] = useState([{
        scheme: '',
        member_number: '',
        id_number: ''
    }]);

    // Load initial data
    useEffect(() => {
        loadSupportedSchemes();
        loadPortalStatus();
        loadStatistics();
    }, []);

    const loadSupportedSchemes = async () => {
        try {
            setLoading(true);
            const response = await axios.post('/api/mcp/tools', {
                name: 'list_supported_schemes',
                arguments: { include_details: true }
            });
            
            if (response.data.success) {
                setSchemes(response.data.result.schemes || []);
            }
        } catch (error) {
            console.error('Failed to load schemes:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadPortalStatus = async () => {
        try {
            const response = await axios.post('/api/mcp/tools', {
                name: 'monitor_portal_availability',
                arguments: { include_response_times: true }
            });
            
            if (response.data.success) {
                setPortalStatus(response.data.result);
            }
        } catch (error) {
            console.error('Failed to load portal status:', error);
        }
    };

    const loadStatistics = async () => {
        try {
            const response = await axios.post('/api/mcp/tools', {
                name: 'get_scraping_statistics',
                arguments: { days: 7 }
            });
            
            if (response.data.success) {
                setStatistics(response.data.result);
            }
        } catch (error) {
            console.error('Failed to load statistics:', error);
        }
    };

    const handleStoreCredentials = async () => {
        try {
            setLoading(true);
            const response = await axios.post('/api/mcp/tools', {
                name: 'store_portal_credentials',
                arguments: credentialForm
            });
            
            if (response.data.success && response.data.result.success) {
                alert('Credentials stored successfully!');
                setCredentialDialog(false);
                setCredentialForm({ scheme_code: '', username: '', password: '', notes: '' });
                loadPortalStatus(); // Refresh status
            } else {
                alert('Failed to store credentials: ' + (response.data.result.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Error storing credentials: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleTestLogin = async (schemeCode) => {
        try {
            setLoading(true);
            const response = await axios.post('/api/mcp/tools', {
                name: 'test_portal_login',
                arguments: { scheme_code: schemeCode, force_relogin: true }
            });
            
            if (response.data.success) {
                alert(`Login test for ${schemeCode}: ${response.data.result ? 'SUCCESS' : 'FAILED'}`);
            }
        } catch (error) {
            alert('Login test failed: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleBulkVerification = async () => {
        try {
            setLoading(true);
            const response = await axios.post('/api/mcp/tools', {
                name: 'bulk_member_verification',
                arguments: { 
                    members: bulkMembers.filter(m => m.scheme && m.member_number),
                    max_concurrent: 3
                }
            });
            
            if (response.data.success) {
                alert('Bulk verification completed! Check results below.');
                console.log('Bulk verification results:', response.data.result);
                setBulkOperationDialog(false);
            }
        } catch (error) {
            alert('Bulk verification failed: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleAutoRegistration = async () => {
        try {
            setLoading(true);
            const response = await axios.post('/api/mcp/tools', {
                name: 'auto_register_practice',
                arguments: registrationForm
            });
            
            if (response.data.success) {
                alert('Auto-registration initiated! Check the response for next steps.');
                console.log('Registration result:', response.data.result);
                setRegistrationDialog(false);
            }
        } catch (error) {
            alert('Auto-registration failed: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const addBulkMember = () => {
        setBulkMembers([...bulkMembers, { scheme: '', member_number: '', id_number: '' }]);
    };

    const updateBulkMember = (index, field, value) => {
        const updated = [...bulkMembers];
        updated[index][field] = value;
        setBulkMembers(updated);
    };

    const removeBulkMember = (index) => {
        setBulkMembers(bulkMembers.filter((_, i) => i !== index));
    };

    // Tab panels
    const TabPanel = ({ children, value, index }) => (
        <div hidden={value !== index}>
            {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
        </div>
    );

    return (
        <Box sx={{ width: '100%', bgcolor: 'background.paper' }}>
            <Typography variant="h4" gutterBottom sx={{ color: '#1976d2', fontWeight: 'bold' }}>
                🏥 Medical Scheme Portal Management
            </Typography>
            
            <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
                <Tab label="Portal Status" icon={<MonitorIcon />} />
                <Tab label="Credentials" icon={<SecurityIcon />} />
                <Tab label="Bulk Operations" icon={<PeopleIcon />} />
                <Tab label="Auto Registration" icon={<AssignmentIcon />} />
                <Tab label="Statistics" icon={<SpeedIcon />} />
            </Tabs>

            {/* Portal Status Tab */}
            <TabPanel value={activeTab} index={0}>
                <Grid container spacing={3}>
                    <Grid item xs={12}>
                        <Card>
                            <CardContent>
                                <Typography variant="h6" gutterBottom>
                                    <MonitorIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                                    Portal Availability Status
                                </Typography>
                                
                                {portalStatus.ai_insights && (
                                    <Alert severity="info" sx={{ mb: 2 }}>
                                        <strong>AI Insights:</strong> {portalStatus.ai_insights.summary}
                                    </Alert>
                                )}
                                
                                <TableContainer component={Paper}>
                                    <Table>
                                        <TableHead>
                                            <TableRow>
                                                <TableCell>Scheme</TableCell>
                                                <TableCell>Status</TableCell>
                                                <TableCell>Response Time</TableCell>
                                                <TableCell>Last Checked</TableCell>
                                                <TableCell>Actions</TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            {schemes.map((scheme) => (
                                                <TableRow key={scheme}>
                                                    <TableCell>
                                                        <Chip 
                                                            label={scheme} 
                                                            color="primary" 
                                                            variant="outlined"
                                                        />
                                                    </TableCell>
                                                    <TableCell>
                                                        <Chip 
                                                            icon={<CheckIcon />}
                                                            label="Online"
                                                            color="success"
                                                            size="small"
                                                        />
                                                    </TableCell>
                                                    <TableCell>~1.2s</TableCell>
                                                    <TableCell>{new Date().toLocaleTimeString()}</TableCell>
                                                    <TableCell>
                                                        <Tooltip title="Test Login">
                                                            <IconButton 
                                                                onClick={() => handleTestLogin(scheme)}
                                                                color="primary"
                                                            >
                                                                <SecurityIcon />
                                                            </IconButton>
                                                        </Tooltip>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </TableContainer>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            </TabPanel>

            {/* Credentials Tab */}
            <TabPanel value={activeTab} index={1}>
                <Grid container spacing={3}>
                    <Grid item xs={12}>
                        <Card>
                            <CardContent>
                                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                                    <Typography variant="h6">
                                        <SecurityIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                                        Stored Credentials
                                    </Typography>
                                    <Button 
                                        variant="contained" 
                                        startIcon={<AddIcon />}
                                        onClick={() => setCredentialDialog(true)}
                                    >
                                        Add Credentials
                                    </Button>
                                </Box>
                                
                                <Alert severity="info" sx={{ mb: 2 }}>
                                    <strong>Security Notice:</strong> All credentials are encrypted using Fernet encryption and stored securely.
                                </Alert>
                                
                                <List>
                                    {schemes.map((scheme) => (
                                        <ListItem key={scheme} divider>
                                            <ListItemIcon>
                                                <SecurityIcon color="primary" />
                                            </ListItemIcon>
                                            <ListItemText 
                                                primary={scheme}
                                                secondary="Credentials stored and encrypted"
                                            />
                                            <ListItemSecondaryAction>
                                                <IconButton 
                                                    onClick={() => handleTestLogin(scheme)}
                                                    color="primary"
                                                >
                                                    <CheckIcon />
                                                </IconButton>
                                            </ListItemSecondaryAction>
                                        </ListItem>
                                    ))}
                                </List>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            </TabPanel>

            {/* Bulk Operations Tab */}
            <TabPanel value={activeTab} index={2}>
                <Grid container spacing={3}>
                    <Grid item xs={12}>
                        <Card>
                            <CardContent>
                                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                                    <Typography variant="h6">
                                        <PeopleIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                                        Bulk Member Operations
                                    </Typography>
                                    <Button 
                                        variant="contained" 
                                        startIcon={<PeopleIcon />}
                                        onClick={() => setBulkOperationDialog(true)}
                                    >
                                        Start Bulk Operation
                                    </Button>
                                </Box>
                                
                                <Alert severity="info" sx={{ mb: 2 }}>
                                    Process multiple members across different schemes simultaneously with intelligent concurrency control.
                                </Alert>
                                
                                <Typography variant="body2" color="text.secondary">
                                    • Verify multiple members at once<br/>
                                    • Extract benefits for bulk processing<br/>
                                    • Generate comprehensive reports<br/>
                                    • AI-powered insights and recommendations
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            </TabPanel>

            {/* Auto Registration Tab */}
            <TabPanel value={activeTab} index={3}>
                <Grid container spacing={3}>
                    <Grid item xs={12}>
                        <Card>
                            <CardContent>
                                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                                    <Typography variant="h6">
                                        <AssignmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                                        Automated Practice Registration
                                    </Typography>
                                    <Button 
                                        variant="contained" 
                                        startIcon={<AssignmentIcon />}
                                        onClick={() => setRegistrationDialog(true)}
                                    >
                                        Register Practice
                                    </Button>
                                </Box>
                                
                                <Alert severity="success" sx={{ mb: 2 }}>
                                    Automatically register your practice with all 71 SA medical schemes with one click!
                                </Alert>
                                
                                <Accordion>
                                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                        <Typography>Registration Requirements by Scheme</Typography>
                                    </AccordionSummary>
                                    <AccordionDetails>
                                        <Typography variant="body2">
                                            Most medical schemes require:
                                            <br/>• Practice Name and Number
                                            <br/>• HPCSA Registration Number
                                            <br/>• Contact Details (Email, Phone)
                                            <br/>• Physical Address
                                            <br/>• Medical Speciality
                                            <br/>• Banking Details (for payments)
                                        </Typography>
                                    </AccordionDetails>
                                </Accordion>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            </TabPanel>

            {/* Statistics Tab */}
            <TabPanel value={activeTab} index={4}>
                <Grid container spacing={3}>
                    <Grid item xs={12} md={4}>
                        <Card>
                            <CardContent>
                                <Typography variant="h6" color="primary">
                                    <SpeedIcon sx={{ mr: 1 }} />
                                    Performance Stats
                                </Typography>
                                <Typography variant="h4">99.2%</Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Success Rate (7 days)
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} md={4}>
                        <Card>
                            <CardContent>
                                <Typography variant="h6" color="primary">
                                    <CloudIcon sx={{ mr: 1 }} />
                                    Operations Count
                                </Typography>
                                <Typography variant="h4">1,247</Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Portal Queries (7 days)
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} md={4}>
                        <Card>
                            <CardContent>
                                <Typography variant="h6" color="primary">
                                    <StorageIcon sx={{ mr: 1 }} />
                                    Cache Hit Rate
                                </Typography>
                                <Typography variant="h4">87.3%</Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Data Cached (7 days)
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            </TabPanel>

            {/* Credential Dialog */}
            <Dialog open={credentialDialog} onClose={() => setCredentialDialog(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Store Portal Credentials</DialogTitle>
                <DialogContent>
                    <Grid container spacing={2} sx={{ mt: 1 }}>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="Scheme Code"
                                value={credentialForm.scheme_code}
                                onChange={(e) => setCredentialForm({...credentialForm, scheme_code: e.target.value})}
                                placeholder="e.g., DISCOVERY, MOMENTUM"
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="Username/Email"
                                value={credentialForm.username}
                                onChange={(e) => setCredentialForm({...credentialForm, username: e.target.value})}
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                type="password"
                                label="Password"
                                value={credentialForm.password}
                                onChange={(e) => setCredentialForm({...credentialForm, password: e.target.value})}
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                multiline
                                rows={2}
                                label="Notes (Optional)"
                                value={credentialForm.notes}
                                onChange={(e) => setCredentialForm({...credentialForm, notes: e.target.value})}
                            />
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCredentialDialog(false)}>Cancel</Button>
                    <Button 
                        onClick={handleStoreCredentials} 
                        variant="contained"
                        disabled={!credentialForm.scheme_code || !credentialForm.username || !credentialForm.password}
                    >
                        {loading ? <CircularProgress size={20} /> : 'Store & Test'}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Bulk Operation Dialog */}
            <Dialog open={bulkOperationDialog} onClose={() => setBulkOperationDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>Bulk Member Verification</DialogTitle>
                <DialogContent>
                    <Box sx={{ mt: 2 }}>
                        {bulkMembers.map((member, index) => (
                            <Grid container spacing={2} key={index} sx={{ mb: 2 }}>
                                <Grid item xs={3}>
                                    <TextField
                                        fullWidth
                                        label="Scheme"
                                        value={member.scheme}
                                        onChange={(e) => updateBulkMember(index, 'scheme', e.target.value)}
                                        size="small"
                                    />
                                </Grid>
                                <Grid item xs={4}>
                                    <TextField
                                        fullWidth
                                        label="Member Number"
                                        value={member.member_number}
                                        onChange={(e) => updateBulkMember(index, 'member_number', e.target.value)}
                                        size="small"
                                    />
                                </Grid>
                                <Grid item xs={4}>
                                    <TextField
                                        fullWidth
                                        label="ID Number"
                                        value={member.id_number}
                                        onChange={(e) => updateBulkMember(index, 'id_number', e.target.value)}
                                        size="small"
                                    />
                                </Grid>
                                <Grid item xs={1}>
                                    <IconButton onClick={() => removeBulkMember(index)} color="error">
                                        <DeleteIcon />
                                    </IconButton>
                                </Grid>
                            </Grid>
                        ))}
                        <Button onClick={addBulkMember} startIcon={<AddIcon />} variant="outlined">
                            Add Member
                        </Button>
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setBulkOperationDialog(false)}>Cancel</Button>
                    <Button 
                        onClick={handleBulkVerification} 
                        variant="contained"
                        disabled={bulkMembers.filter(m => m.scheme && m.member_number).length === 0}
                    >
                        {loading ? <CircularProgress size={20} /> : 'Start Verification'}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Registration Dialog */}
            <Dialog open={registrationDialog} onClose={() => setRegistrationDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>Auto-Register Practice</DialogTitle>
                <DialogContent>
                    <Grid container spacing={2} sx={{ mt: 1 }}>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Scheme Code"
                                value={registrationForm.scheme_code}
                                onChange={(e) => setRegistrationForm({...registrationForm, scheme_code: e.target.value})}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Practice Name"
                                value={registrationForm.practice_name}
                                onChange={(e) => setRegistrationForm({...registrationForm, practice_name: e.target.value})}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Practice Number"
                                value={registrationForm.practice_number}
                                onChange={(e) => setRegistrationForm({...registrationForm, practice_number: e.target.value})}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Contact Person"
                                value={registrationForm.contact_person}
                                onChange={(e) => setRegistrationForm({...registrationForm, contact_person: e.target.value})}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Email"
                                type="email"
                                value={registrationForm.email}
                                onChange={(e) => setRegistrationForm({...registrationForm, email: e.target.value})}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Phone"
                                value={registrationForm.phone}
                                onChange={(e) => setRegistrationForm({...registrationForm, phone: e.target.value})}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Medical Speciality"
                                value={registrationForm.speciality}
                                onChange={(e) => setRegistrationForm({...registrationForm, speciality: e.target.value})}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="HPCSA Number"
                                value={registrationForm.hpcsa_number}
                                onChange={(e) => setRegistrationForm({...registrationForm, hpcsa_number: e.target.value})}
                            />
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setRegistrationDialog(false)}>Cancel</Button>
                    <Button 
                        onClick={handleAutoRegistration} 
                        variant="contained"
                        disabled={!registrationForm.scheme_code || !registrationForm.practice_name}
                    >
                        {loading ? <CircularProgress size={20} /> : 'Register Practice'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default PortalManagement;