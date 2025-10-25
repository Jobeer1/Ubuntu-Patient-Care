import React from 'react';
import {
  Box,
  Container,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  AppBar,
  Toolbar,
} from '@mui/material';
import {
  Dashboard,
  Assignment,
  Note,
  CheckCircle,
  Speed,
  Security,
  Person,
  AttachMoney,
  LocalHospital,
  Assessment,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: <Person />,
      title: 'Patient Management',
      description: 'Comprehensive patient records, demographics, and medical history management.',
    },
    {
      icon: <LocalHospital />,
      title: 'Study Orders',
      description: 'Efficient radiology study ordering, scheduling, and tracking system.',
    },
    {
      icon: <AttachMoney />,
      title: 'Billing & Claims',
      description: 'Streamlined billing processes and medical aid claims management.',
    },
    {
      icon: <Assessment />,
      title: 'Reports & Analytics',
      description: 'Comprehensive reporting dashboard with business intelligence.',
    },
    {
      icon: <Security />,
      title: 'HIPAA Compliant',
      description: 'Secure patient data handling with full healthcare compliance.',
    },
    {
      icon: <Speed />,
      title: 'High Performance',
      description: 'Fast, reliable system built specifically for medical environments.',
    },
  ];

  return (
    <Box>
      {/* Header */}
      <AppBar position="static" elevation={0} sx={{ bgcolor: 'transparent', color: 'text.primary' }}>
        <Toolbar>
          <LocalHospital sx={{ mr: 2, color: 'primary.main' }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            OpenEMR RIS
          </Typography>
          <Button 
            color="inherit" 
            onClick={() => navigate('/login')}
            sx={{ mr: 1 }}
          >
            Sign In
          </Button>
          <Button 
            variant="contained" 
            onClick={() => navigate('/login')}
          >
            Get Started
          </Button>
        </Toolbar>
      </AppBar>

      {/* Hero Section */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)',
          color: 'white',
          py: 12,
          textAlign: 'center',
        }}
      >
        <Container maxWidth="md">
          <Typography variant="h2" component="h1" fontWeight="bold" gutterBottom>
            OpenEMR Radiology Information System
          </Typography>
          <Typography variant="h5" component="p" sx={{ mb: 4, opacity: 0.9 }}>
            Complete RIS solution for radiology practices, hospitals, and imaging centers
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              size="large"
              sx={{ 
                bgcolor: 'white', 
                color: 'primary.main',
                '&:hover': { bgcolor: 'grey.100' },
                px: 4,
                py: 1.5,
              }}
              onClick={() => navigate('/login')}
            >
              Start Free Trial
            </Button>
            <Button
              variant="outlined"
              size="large"
              sx={{ 
                borderColor: 'white', 
                color: 'white',
                '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,0.1)' },
                px: 4,
                py: 1.5,
              }}
              onClick={() => navigate('/login')}
            >
              Sign In
            </Button>
          </Box>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Box textAlign="center" mb={6}>
          <Typography variant="h3" component="h2" fontWeight="bold" gutterBottom>
            Complete RIS Solution
          </Typography>
          <Typography variant="h6" color="textSecondary">
            Everything you need to manage your radiology practice efficiently
          </Typography>
        </Box>

        <Grid container spacing={4}>
          {features.map((feature, index) => (
            <Grid item xs={12} sm={6} md={4} key={index}>
              <Card 
                sx={{ 
                  height: '100%',
                  textAlign: 'center',
                  p: 2,
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    transition: 'transform 0.2s ease-in-out',
                    boxShadow: 4,
                  }
                }}
              >
                <CardContent>
                  <Box
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 64,
                      height: 64,
                      borderRadius: '50%',
                      bgcolor: 'primary.main',
                      color: 'white',
                      mb: 2,
                    }}
                  >
                    {feature.icon}
                  </Box>
                  <Typography variant="h6" component="h3" fontWeight="bold" gutterBottom>
                    {feature.title}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* Benefits Section */}
      <Box sx={{ bgcolor: 'grey.50', py: 8 }}>
        <Container maxWidth="lg">
          <Grid container spacing={6} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography variant="h4" component="h2" fontWeight="bold" gutterBottom>
                Why Choose OpenEMR RIS?
              </Typography>
              <Typography variant="body1" paragraph>
                Our Radiology Information System is designed specifically for South African healthcare providers, 
                with built-in support for local medical aids and compliance requirements.
              </Typography>
              <Box sx={{ mt: 3 }}>
                <Box display="flex" alignItems="center" mb={2}>
                  <CheckCircle color="success" sx={{ mr: 2 }} />
                  <Typography>Full integration with medical aid systems</Typography>
                </Box>
                <Box display="flex" alignItems="center" mb={2}>
                  <CheckCircle color="success" sx={{ mr: 2 }} />
                  <Typography>POPIA and HIPAA compliant data handling</Typography>
                </Box>
                <Box display="flex" alignItems="center" mb={2}>
                  <CheckCircle color="success" sx={{ mr: 2 }} />
                  <Typography>Real-time billing and claims processing</Typography>
                </Box>
                <Box display="flex" alignItems="center" mb={2}>
                  <CheckCircle color="success" sx={{ mr: 2 }} />
                  <Typography>Comprehensive reporting and analytics</Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box
                sx={{
                  bgcolor: 'white',
                  p: 4,
                  borderRadius: 2,
                  boxShadow: 2,
                }}
              >
                <Typography variant="h6" gutterBottom>
                  Demo Credentials
                </Typography>
                <Typography variant="body2" color="textSecondary" paragraph>
                  Try our system with the demo account:
                </Typography>
                <Box sx={{ bgcolor: 'grey.100', p: 2, borderRadius: 1, fontFamily: 'monospace' }}>
                  <Typography variant="body2">Email: demo@example.com</Typography>
                  <Typography variant="body2">Password: demo123</Typography>
                </Box>
                <Button
                  variant="contained"
                  fullWidth
                  sx={{ mt: 2 }}
                  onClick={() => navigate('/login')}
                >
                  Try Demo Now
                </Button>
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* CTA Section */}
      <Box
        sx={{
          py: 8,
          textAlign: 'center',
        }}
      >
        <Container maxWidth="md">
          <Typography variant="h4" component="h2" fontWeight="bold" gutterBottom>
            Ready to Transform Your Practice?
          </Typography>
          <Typography variant="h6" color="textSecondary" sx={{ mb: 4 }}>
            Join healthcare providers across South Africa who trust OpenEMR RIS
          </Typography>
          <Button
            variant="contained"
            size="large"
            sx={{ px: 4, py: 1.5 }}
            onClick={() => navigate('/login')}
          >
            Start Your Free Trial
          </Button>
        </Container>
      </Box>

      {/* Footer */}
      <Box
        sx={{
          bgcolor: 'grey.900',
          color: 'white',
          py: 4,
          textAlign: 'center',
        }}
      >
        <Container>
          <Typography variant="body2">
            © 2024 OpenEMR RIS. Built for South African Healthcare Providers.
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

export default LandingPage;