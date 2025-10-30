import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Button,
  Divider,
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Info,
  Refresh,
  Storage,
  Cloud,
  Psychology,
  Security,
  NetworkCheck,
  Speed,
  Memory,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import toast from 'react-hot-toast';

function SystemStatus({ serverStatus, onRefresh }) {
  const [loading, setLoading] = useState(false);
  const [detailedStatus, setDetailedStatus] = useState(null);
  const [performanceData, setPerformanceData] = useState([]);
  const [mcpStats, setMcpStats] = useState(null);

  useEffect(() => {
    fetchDetailedStatus();
    fetchPerformanceData();
    fetchMCPStats();
  }, []);

  const fetchDetailedStatus = async () => {
    try {
      const response = await fetch('/api/system/detailed-status');
      if (response.ok) {
        const data = await response.json();
        setDetailedStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch detailed status:', error);
    }
  };

  const fetchPerformanceData = async () => {
    try {
      const response = await fetch('/api/system/performance');
      if (response.ok) {
        const data = await response.json();
        setPerformanceData(data.history || []);
      }
    } catch (error) {
      console.error('Failed to fetch performance data:', error);
    }
  };

  const fetchMCPStats = async () => {
    try {
      const response = await fetch('/api/mcp/stats');
      if (response.ok) {
        const data = await response.json();
        setMcpStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch MCP stats:', error);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await onRefresh();
      await fetchDetailedStatus();
      await fetchPerformanceData();
      await fetchMCPStats();
      toast.success('System status refreshed!');
    } catch (error) {
      toast.error('Failed to refresh status');
    } finally {
      setLoading(false);
    }
  };

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
      case 'healthy': return <CheckCircle color="success" />;
      case 'error': return <Error color="error" />;
      case 'warning': return <Warning color="warning" />;
      default: return <Info color="info" />;
    }
  };

  const getHealthScore = () => {
    const statuses = Object.values(serverStatus);
    const healthyCount = statuses.filter(status => status === 'healthy').length;
    return Math.round((healthyCount / statuses.length) * 100);
  };

  const healthScore = getHealthScore();

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4">
          🔍 System Status & Monitoring
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={handleRefresh}
          disabled={loading}
        >
          Refresh Status
        </Button>
      </Box>

      <Grid container spacing={3}>
        {/* Overall Health Score */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Overall Health
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                  <LinearProgress 
                    variant="determinate" 
                    value={healthScore} 
                    sx={{ 
                      height: 10, 
                      borderRadius: 5,
                      width: 100,
                      backgroundColor: 'grey.300'
                    }}
                    color={healthScore >= 80 ? 'success' : healthScore >= 60 ? 'warning' : 'error'}
                  />
                </Box>
                <Typography variant="h5" color={healthScore >= 80 ? 'success.main' : healthScore >= 60 ? 'warning.main' : 'error.main'}>
                  {healthScore}%
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Service Status Cards */}
        {[
          { key: 'mcp_server', label: 'MCP Server', icon: <Storage /> },
          { key: 'claude_ai', label: 'Claude AI', icon: <Psychology /> },
          { key: 'database', label: 'Database', icon: <Storage /> },
          { key: 'aws_bedrock', label: 'AWS Bedrock', icon: <Cloud /> }
        ].map(service => (
          <Grid item xs={12} md={6} lg={3} key={service.key}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} sx={{ mb: 1 }}>
                  {service.icon}
                  <Typography variant="h6">
                    {service.label}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  {getStatusIcon(serverStatus[service.key])}
                  <Chip
                    label={serverStatus[service.key] || 'unknown'}
                    color={getStatusColor(serverStatus[service.key])}
                    size="small"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}

        {/* MCP Tools Statistics */}
        {mcpStats && (
          <Grid item xs={12} lg={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                <Speed sx={{ mr: 1, verticalAlign: 'middle' }} />
                MCP Tools Usage
              </Typography>
              
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={mcpStats.tool_usage || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tool" angle={-45} textAnchor="end" height={80} />
                  <YAxis />
                  <RechartsTooltip />
                  <Bar dataKey="count" fill="#1976d2" />
                </BarChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        )}

        {/* Performance Chart */}
        <Grid item xs={12} lg={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              <NetworkCheck sx={{ mr: 1, verticalAlign: 'middle' }} />
              Response Time Trends
            </Typography>
            
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <RechartsTooltip />
                <Line type="monotone" dataKey="response_time" stroke="#1976d2" strokeWidth={2} />
                <Line type="monotone" dataKey="cpu_usage" stroke="#dc004e" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* System Information */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              <Memory sx={{ mr: 1, verticalAlign: 'middle' }} />
              System Information
            </Typography>
            
            {detailedStatus ? (
              <TableContainer>
                <Table size="small">
                  <TableBody>
                    <TableRow>
                      <TableCell><strong>Server Uptime</strong></TableCell>
                      <TableCell>{detailedStatus.uptime || 'Unknown'}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell><strong>Memory Usage</strong></TableCell>
                      <TableCell>{detailedStatus.memory_usage || 'Unknown'}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell><strong>CPU Usage</strong></TableCell>
                      <TableCell>{detailedStatus.cpu_usage || 'Unknown'}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell><strong>Database Size</strong></TableCell>
                      <TableCell>{detailedStatus.database_size || 'Unknown'}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell><strong>Active Connections</strong></TableCell>
                      <TableCell>{detailedStatus.active_connections || 'Unknown'}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Alert severity="info">Loading system information...</Alert>
            )}
          </Paper>
        </Grid>

        {/* Recent Activities */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              <Security sx={{ mr: 1, verticalAlign: 'middle' }} />
              Recent Activities
            </Typography>
            
            {mcpStats?.recent_activities ? (
              <Box>
                {mcpStats.recent_activities.map((activity, index) => (
                  <Box key={index} sx={{ mb: 2, pb: 1, borderBottom: '1px solid', borderColor: 'grey.200' }}>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(activity.timestamp).toLocaleString()}
                    </Typography>
                    <Typography variant="body1">
                      {activity.action}
                    </Typography>
                    <Chip
                      label={activity.status}
                      color={getStatusColor(activity.status)}
                      size="small"
                    />
                  </Box>
                ))}
              </Box>
            ) : (
              <Alert severity="info">No recent activities available</Alert>
            )}
          </Paper>
        </Grid>

        {/* Health Alerts */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Health Alerts & Recommendations
            </Typography>
            
            <Grid container spacing={2}>
              {serverStatus.mcp_server === 'error' && (
                <Grid item xs={12}>
                  <Alert severity="error">
                    MCP Server is not responding. Check server logs and restart if necessary.
                  </Alert>
                </Grid>
              )}
              
              {serverStatus.claude_ai === 'error' && (
                <Grid item xs={12}>
                  <Alert severity="error">
                    Claude AI service is unavailable. Verify AWS Bedrock configuration and credentials.
                  </Alert>
                </Grid>
              )}
              
              {serverStatus.database === 'error' && (
                <Grid item xs={12}>
                  <Alert severity="error">
                    Database connection failed. Check database server status and connection settings.
                  </Alert>
                </Grid>
              )}
              
              {serverStatus.aws_bedrock === 'error' && (
                <Grid item xs={12}>
                  <Alert severity="error">
                    AWS Bedrock connection failed. Check AWS credentials and region settings.
                  </Alert>
                </Grid>
              )}
              
              {healthScore === 100 && (
                <Grid item xs={12}>
                  <Alert severity="success">
                    All systems are running optimally! 🎉
                  </Alert>
                </Grid>
              )}
              
              {healthScore < 100 && healthScore >= 80 && (
                <Grid item xs={12}>
                  <Alert severity="warning">
                    System is mostly healthy but some components need attention.
                  </Alert>
                </Grid>
              )}
              
              {healthScore < 80 && (
                <Grid item xs={12}>
                  <Alert severity="error">
                    Multiple system components are experiencing issues. Immediate attention required.
                  </Alert>
                </Grid>
              )}
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default SystemStatus;