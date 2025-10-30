import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  AppBar,
  Toolbar,
  Tab,
  Tabs,
  Chip,
  Button,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Badge,
  Divider,
} from '@mui/material';
import {
  LocalHospital,
  Psychology,
  Assessment,
  Security,
  CloudDone,
  Error,
  CheckCircle,
  Refresh,
  Settings,
  Dashboard,
} from '@mui/icons-material';
import toast from 'react-hot-toast';

// Import components
import MCPToolTester from './components/MCPToolTester';
import ClaudeAIBrain from './components/ClaudeAIBrain';
import SystemStatus from './components/SystemStatus';
import PatientWorkflow from './components/PatientWorkflow';
import PortalManagement from './components/PortalManagement';

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`medical-tabpanel-${index}`}
      aria-labelledby={`medical-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function App() {
  const [currentTab, setCurrentTab] = useState(0);
  const [serverStatus, setServerStatus] = useState({
    mcp_server: 'unknown',
    claude_ai: 'unknown',
    database: 'unknown',
    aws_bedrock: 'unknown'
  });
  const [statusLoading, setStatusLoading] = useState(false);

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  const checkServerStatus = async () => {
    setStatusLoading(true);
    try {
      // Check MCP Server status
      const mcpResponse = await fetch('/api/status');
      const mcpData = await mcpResponse.json();
      
      // Check Claude AI status  
      const claudeResponse = await fetch('/api/ai-brain/status');
      const claudeData = await claudeResponse.json();
      
      setServerStatus({
        mcp_server: mcpResponse.ok ? 'healthy' : 'error',
        claude_ai: claudeResponse.ok && claudeData.status === 'ready' ? 'healthy' : 'error',
        database: mcpData.database_status || 'unknown',
        aws_bedrock: claudeData.client_initialized ? 'healthy' : 'error'
      });
      
      if (mcpResponse.ok && claudeResponse.ok) {
        toast.success('All services are running properly!');
      } else {
        toast.error('Some services are experiencing issues');
      }
      
    } catch (error) {
      console.error('Status check failed:', error);
      toast.error('Failed to check server status');
      setServerStatus({
        mcp_server: 'error',
        claude_ai: 'error',
        database: 'error',
        aws_bedrock: 'error'
      });
    } finally {
      setStatusLoading(false);
    }
  };

  useEffect(() => {
    checkServerStatus();
    // Auto-refresh status every 30 seconds
    const interval = setInterval(checkServerStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'success';
      case 'error': return 'error';
      case 'warning': return 'warning';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircle />;
      case 'error': return <Error />;
      default: return <CloudDone />;
    }
  };

  return (
    <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Header */}
      <AppBar position="static" elevation={0} sx={{ bgcolor: 'primary.main' }}>
        <Toolbar>
          <LocalHospital sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            🏥 MCP Medical Server - Testing Interface
          </Typography>
          
          {/* Status Indicators */}
          <Box sx={{ display: 'flex', gap: 1, mr: 2 }}>
            <Chip
              icon={getStatusIcon(serverStatus.mcp_server)}
              label="MCP Server"
              color={getStatusColor(serverStatus.mcp_server)}
              size="small"
              variant="outlined"
              sx={{ color: 'white', borderColor: 'rgba(255,255,255,0.3)' }}
            />
            <Chip
              icon={getStatusIcon(serverStatus.claude_ai)}
              label="Claude AI"
              color={getStatusColor(serverStatus.claude_ai)}
              size="small"
              variant="outlined"
              sx={{ color: 'white', borderColor: 'rgba(255,255,255,0.3)' }}
            />
            <Chip
              icon={getStatusIcon(serverStatus.aws_bedrock)}
              label="AWS Bedrock"
              color={getStatusColor(serverStatus.aws_bedrock)}
              size="small"
              variant="outlined"
              sx={{ color: 'white', borderColor: 'rgba(255,255,255,0.3)' }}
            />
          </Box>
          
          <IconButton
            color="inherit"
            onClick={checkServerStatus}
            disabled={statusLoading}
            title="Refresh Status"
          >
            <Refresh className={statusLoading ? 'loading-spinner' : ''} />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Navigation Tabs */}
      <Paper elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Container maxWidth="xl">
          <Tabs
            value={currentTab}
            onChange={handleTabChange}
            aria-label="Medical server testing tabs"
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab 
              icon={<Dashboard />} 
              label="System Overview" 
              id="medical-tab-0"
              aria-controls="medical-tabpanel-0"
            />
            <Tab 
              icon={<Assessment />} 
              label="MCP Tools" 
              id="medical-tab-1"
              aria-controls="medical-tabpanel-1"
            />
            <Tab 
              icon={<Psychology />} 
              label="Claude AI Brain" 
              id="medical-tab-2"
              aria-controls="medical-tabpanel-2"
            />
            <Tab 
              icon={<LocalHospital />} 
              label="Patient Workflow" 
              id="medical-tab-3"
              aria-controls="medical-tabpanel-3"
            />
            <Tab 
              icon={<CloudDone />} 
              label="Portal Management" 
              id="medical-tab-4"
              aria-controls="medical-tabpanel-4"
            />
            <Tab 
              icon={<Security />} 
              label="System Status" 
              id="medical-tab-5"
              aria-controls="medical-tabpanel-5"
            />
          </Tabs>
        </Container>
      </Paper>

      {/* Tab Content */}
      <Container maxWidth="xl" sx={{ mt: 3, pb: 4 }}>
        <TabPanel value={currentTab} index={0}>
          {/* System Overview */}
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h4" gutterBottom>
                    🏥 Welcome to MCP Medical Server Testing Interface
                  </Typography>
                  <Typography variant="body1" color="text.secondary" paragraph>
                    This interface allows you to test all MCP server functions, interact with Claude 4 Sonnet AI brain,
                    and simulate complete patient workflows. Everything is designed to work offline and provide
                    instant medical aid authorization.
                  </Typography>
                  
                  <Divider sx={{ my: 2 }} />
                  
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6} lg={3}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            <Assessment sx={{ mr: 1, verticalAlign: 'middle' }} />
                            MCP Tools
                          </Typography>
                          <Typography variant="body2">
                            Test all 12 medical authorization tools including validation, pre-auth, and AI processing.
                          </Typography>
                        </CardContent>
                        <CardActions>
                          <Button size="small" onClick={() => setCurrentTab(1)}>
                            Test Tools
                          </Button>
                        </CardActions>
                      </Card>
                    </Grid>
                    
                    <Grid item xs={12} md={6} lg={3}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            <Psychology sx={{ mr: 1, verticalAlign: 'middle' }} />
                            Claude AI Brain
                          </Typography>
                          <Typography variant="body2">
                            Interact with Claude 4 Sonnet for medical analysis, decision support, and recommendations.
                          </Typography>
                        </CardContent>
                        <CardActions>
                          <Button size="small" onClick={() => setCurrentTab(2)}>
                            Ask Claude
                          </Button>
                        </CardActions>
                      </Card>
                    </Grid>
                    
                    <Grid item xs={12} md={6} lg={3}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            <LocalHospital sx={{ mr: 1, verticalAlign: 'middle' }} />
                            Patient Workflow
                          </Typography>
                          <Typography variant="body2">
                            Simulate complete patient journeys from arrival to pre-authorization approval.
                          </Typography>
                        </CardContent>
                        <CardActions>
                          <Button size="small" onClick={() => setCurrentTab(3)}>
                            Start Workflow
                          </Button>
                        </CardActions>
                      </Card>
                    </Grid>
                    
                    <Grid item xs={12} md={6} lg={3}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            <CloudDone sx={{ mr: 1, verticalAlign: 'middle' }} />
                            Portal Management
                          </Typography>
                          <Typography variant="body2">
                            Manage medical scheme portal credentials and automate registrations without APIs.
                          </Typography>
                        </CardContent>
                        <CardActions>
                          <Button size="small" onClick={() => setCurrentTab(4)}>
                            Manage Portals
                          </Button>
                        </CardActions>
                      </Card>
                    </Grid>
                    
                    <Grid item xs={12} md={6} lg={3}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            <Security sx={{ mr: 1, verticalAlign: 'middle' }} />
                            System Status
                          </Typography>
                          <Typography variant="body2">
                            Monitor server health, database connections, and AWS Bedrock integration.
                          </Typography>
                        </CardContent>
                        <CardActions>
                          <Button size="small" onClick={() => setCurrentTab(5)}>
                            View Status
                          </Button>
                        </CardActions>
                      </Card>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={currentTab} index={1}>
          <MCPToolTester />
        </TabPanel>

        <TabPanel value={currentTab} index={2}>
          <ClaudeAIBrain />
        </TabPanel>

        <TabPanel value={currentTab} index={3}>
          <PatientWorkflow />
        </TabPanel>

        <TabPanel value={currentTab} index={4}>
          <PortalManagement />
        </TabPanel>

        <TabPanel value={currentTab} index={5}>
          <SystemStatus serverStatus={serverStatus} onRefresh={checkServerStatus} />
        </TabPanel>
      </Container>
    </Box>
  );
}

export default App;