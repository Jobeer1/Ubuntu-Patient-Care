import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from '@mui/material';
import {
  Assessment,
  TrendingUp,
  PieChart,
  BarChart,
  Download,
  Print,
  DateRange,
  AttachMoney,
  Person,
  Receipt,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

interface ReportData {
  id: string;
  type: string;
  period: string;
  generatedDate: string;
  status: 'completed' | 'pending' | 'failed';
  size: string;
}

const ReportsPage: React.FC = () => {
  const [reportType, setReportType] = useState('');
  const [dateRange, setDateRange] = useState('thisMonth');
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);

  // Mock data for reports
  const mockReportsData: ReportData[] = [
    {
      id: '1',
      type: 'Financial Summary',
      period: 'January 2024',
      generatedDate: '2024-02-01',
      status: 'completed',
      size: '2.3 MB',
    },
    {
      id: '2',
      type: 'Patient Demographics',
      period: 'Q4 2023',
      generatedDate: '2024-01-15',
      status: 'completed',
      size: '1.8 MB',
    },
    {
      id: '3',
      type: 'Service Utilization',
      period: 'December 2023',
      generatedDate: '2024-01-10',
      status: 'pending',
      size: '-',
    },
  ];

  // Mock summary data
  const summaryData = {
    totalRevenue: 125000,
    totalPatients: 342,
    totalServices: 1250,
    averageServiceValue: 850,
    monthlyGrowth: 12.5,
    patientGrowth: 8.3,
  };

  const handleGenerateReport = () => {
    if (!reportType) {
      alert('Please select a report type');
      return;
    }
    
    console.log('Generating report:', {
      type: reportType,
      dateRange,
      startDate,
      endDate,
    });
    
    // Simulate report generation
    alert(`Generating ${reportType} report for ${dateRange}...`);
    
    // Add to recent reports (mock)
    const newReport = {
      id: Date.now().toString(),
      type: reportType.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase()),
      period: dateRange === 'custom' ? 
        `${startDate?.toLocaleDateString()} - ${endDate?.toLocaleDateString()}` : 
        dateRange.replace(/([A-Z])/g, ' $1').trim(),
      generatedDate: new Date().toISOString(),
      status: 'completed' as const,
      size: '1.2 MB',
    };
    
    console.log('Report generated:', newReport);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'pending': return 'warning';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
          <Typography variant="h4" component="h1" fontWeight="bold">
            Reports & Analytics
          </Typography>
          <Button
            variant="contained"
            startIcon={<Assessment />}
            onClick={handleGenerateReport}
            disabled={!reportType}
          >
            Generate Report
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
                      R {summaryData.totalRevenue.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="success.main">
                      +{summaryData.monthlyGrowth}% this month
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
                      Total Patients
                    </Typography>
                    <Typography variant="h5">
                      {summaryData.totalPatients}
                    </Typography>
                    <Typography variant="body2" color="success.main">
                      +{summaryData.patientGrowth}% this month
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
                  <Receipt color="success" sx={{ mr: 2 }} />
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      Services Rendered
                    </Typography>
                    <Typography variant="h5">
                      {summaryData.totalServices}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      This month
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
                  <TrendingUp color="warning" sx={{ mr: 2 }} />
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      Avg Service Value
                    </Typography>
                    <Typography variant="h5">
                      R {summaryData.averageServiceValue}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Per service
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Grid container spacing={3}>
          {/* Report Generation */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Generate New Report
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Report Type</InputLabel>
                    <Select
                      value={reportType}
                      label="Report Type"
                      onChange={(e) => setReportType(e.target.value)}
                    >
                      <MenuItem value="financial">Financial Summary</MenuItem>
                      <MenuItem value="patient-demographics">Patient Demographics</MenuItem>
                      <MenuItem value="service-utilization">Service Utilization</MenuItem>
                      <MenuItem value="medical-aid">Medical Aid Analysis</MenuItem>
                      <MenuItem value="revenue-trends">Revenue Trends</MenuItem>
                      <MenuItem value="operational">Operational Metrics</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Date Range</InputLabel>
                    <Select
                      value={dateRange}
                      label="Date Range"
                      onChange={(e) => setDateRange(e.target.value)}
                    >
                      <MenuItem value="thisMonth">This Month</MenuItem>
                      <MenuItem value="lastMonth">Last Month</MenuItem>
                      <MenuItem value="thisQuarter">This Quarter</MenuItem>
                      <MenuItem value="lastQuarter">Last Quarter</MenuItem>
                      <MenuItem value="thisYear">This Year</MenuItem>
                      <MenuItem value="lastYear">Last Year</MenuItem>
                      <MenuItem value="custom">Custom Range</MenuItem>
                    </Select>
                  </FormControl>

                  {dateRange === 'custom' && (
                    <Grid container spacing={2} sx={{ mb: 2 }}>
                      <Grid item xs={6}>
                        <DatePicker
                          label="Start Date"
                          value={startDate}
                          onChange={(newValue) => setStartDate(newValue)}
                          slotProps={{ textField: { fullWidth: true } }}
                        />
                      </Grid>
                      <Grid item xs={6}>
                        <DatePicker
                          label="End Date"
                          value={endDate}
                          onChange={(newValue) => setEndDate(newValue)}
                          slotProps={{ textField: { fullWidth: true } }}
                        />
                      </Grid>
                    </Grid>
                  )}

                  <Box display="flex" gap={2}>
                    <Button
                      variant="contained"
                      startIcon={<Assessment />}
                      onClick={handleGenerateReport}
                      disabled={!reportType}
                      fullWidth
                    >
                      Generate Report
                    </Button>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Quick Stats */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quick Analytics
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Box textAlign="center" p={2} bgcolor="primary.light" borderRadius={1}>
                        <PieChart sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
                        <Typography variant="h6">Revenue</Typography>
                        <Typography variant="body2">By Service Type</Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box textAlign="center" p={2} bgcolor="success.light" borderRadius={1}>
                        <BarChart sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
                        <Typography variant="h6">Trends</Typography>
                        <Typography variant="body2">Monthly Growth</Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box textAlign="center" p={2} bgcolor="info.light" borderRadius={1}>
                        <Person sx={{ fontSize: 40, color: 'info.main', mb: 1 }} />
                        <Typography variant="h6">Patients</Typography>
                        <Typography variant="body2">Demographics</Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box textAlign="center" p={2} bgcolor="warning.light" borderRadius={1}>
                        <DateRange sx={{ fontSize: 40, color: 'warning.main', mb: 1 }} />
                        <Typography variant="h6">Schedule</Typography>
                        <Typography variant="body2">Utilization</Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Recent Reports */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Recent Reports
                </Typography>
                <TableContainer component={Paper} elevation={0}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Report Type</TableCell>
                        <TableCell>Period</TableCell>
                        <TableCell>Generated Date</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Size</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {mockReportsData.map((report) => (
                        <TableRow key={report.id}>
                          <TableCell>{report.type}</TableCell>
                          <TableCell>{report.period}</TableCell>
                          <TableCell>
                            {new Date(report.generatedDate).toLocaleDateString()}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={report.status.toUpperCase()}
                              color={getStatusColor(report.status) as any}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>{report.size}</TableCell>
                          <TableCell>
                            <Button
                              size="small"
                              startIcon={<Download />}
                              disabled={report.status !== 'completed'}
                              sx={{ mr: 1 }}
                              onClick={() => {
                                console.log('Downloading report:', report.id);
                                alert(`Downloading ${report.type} report...`);
                              }}
                            >
                              Download
                            </Button>
                            <Button
                              size="small"
                              startIcon={<Print />}
                              disabled={report.status !== 'completed'}
                              onClick={() => {
                                console.log('Printing report:', report.id);
                                alert(`Printing ${report.type} report...`);
                                window.print();
                              }}
                            >
                              Print
                            </Button>
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
      </Container>
    </LocalizationProvider>
  );
};

export default ReportsPage;