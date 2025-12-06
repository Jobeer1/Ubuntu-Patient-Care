import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Avatar,
  Divider,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';

const SettingsPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <Box>
      <Typography variant="h4" component="h1" fontWeight="bold" mb={3}>
        Settings
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Profile Information
              </Typography>
              <Divider sx={{ mb: 3 }} />
              
              <Box display="flex" alignItems="center" mb={3}>
                <Avatar 
                  sx={{ 
                    bgcolor: 'primary.main', 
                    width: 80, 
                    height: 80, 
                    fontSize: '2rem',
                    mr: 3 
                  }}
                >
                  {user?.firstName?.[0]}{user?.lastName?.[0]}
                </Avatar>
                <Box>
                  <Typography variant="h6">
                    {user?.firstName} {user?.lastName}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {user?.email}
                  </Typography>
                </Box>
              </Box>

              <Box>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  <strong>First Name:</strong> {user?.firstName}
                </Typography>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  <strong>Last Name:</strong> {user?.lastName}
                </Typography>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  <strong>Email:</strong> {user?.email}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Application Info
              </Typography>
              <Divider sx={{ mb: 3 }} />
              
              <Typography variant="body2" color="textSecondary" gutterBottom>
                <strong>Application:</strong> Web Dashboard
              </Typography>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                <strong>Version:</strong> 1.0.0
              </Typography>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                <strong>Environment:</strong> Development
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SettingsPage;