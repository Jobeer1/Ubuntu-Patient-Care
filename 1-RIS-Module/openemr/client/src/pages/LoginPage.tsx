import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  InputAdornment,
  IconButton,
  Tabs,
  Tab,
  Divider,
} from '@mui/material';
import { Visibility, VisibilityOff, Dashboard, Person, PersonAdd } from '@mui/icons-material';
import { useForm } from 'react-hook-form';
import { useAuth } from '../contexts/AuthContext';

interface LoginFormData {
  email: string;
  password: string;
}

interface SignupFormData {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const LoginPage: React.FC = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const { login, register: registerUser } = useAuth();

  const loginForm = useForm<LoginFormData>();
  const signupForm = useForm<SignupFormData>();

  const onLoginSubmit = async (data: LoginFormData) => {
    try {
      setError(null);
      setSuccess(null);
      console.log('Attempting login with:', data.email);
      await login(data.email, data.password);
      console.log('Login successful!');
    } catch (err: any) {
      console.error('Login error:', err);
      
      let errorMessage = 'Login failed. Please check your credentials and try again.';
      
      if (err.code === 'ECONNREFUSED' || err.message?.includes('Network Error')) {
        errorMessage = 'Cannot connect to server. Please make sure the server is running on port 3001.';
      } else if (err.response?.data?.error?.message) {
        errorMessage = err.response.data.error.message;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
    }
  };

  const onSignupSubmit = async (data: SignupFormData) => {
    try {
      setError(null);
      setSuccess(null);
      
      if (data.password !== data.confirmPassword) {
        setError('Passwords do not match');
        return;
      }

      await registerUser({
        firstName: data.firstName,
        lastName: data.lastName,
        email: data.email,
        password: data.password,
      });
      
      setSuccess('Account created successfully! You can now sign in.');
      setActiveTab(0);
      signupForm.reset();
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Registration failed');
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        p: 2,
      }}
    >
      <Card sx={{ maxWidth: 450, width: '100%' }}>
        <CardContent sx={{ p: 4 }}>

          <Box textAlign="center" mb={4}>
            <Dashboard sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
            <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
              OpenEMR RIS
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Radiology Information System
            </Typography>
          </Box>

          <Tabs 
            value={activeTab} 
            onChange={(_, newValue) => setActiveTab(newValue)}
            variant="fullWidth"
            sx={{ mb: 3 }}
          >
            <Tab icon={<Person />} label="Sign In" />
            <Tab icon={<PersonAdd />} label="Sign Up" />
          </Tabs>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" sx={{ mb: 3 }}>
              {success}
            </Alert>
          )}

          {activeTab === 0 && (
            <form onSubmit={loginForm.handleSubmit(onLoginSubmit)}>
              <TextField
                fullWidth
                label="Email Address"
                type="email"
                margin="normal"
                {...loginForm.register('email', {
                  required: 'Email is required',
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Invalid email address',
                  },
                })}
                error={!!loginForm.formState.errors.email}
                helperText={loginForm.formState.errors.email?.message}
              />

              <TextField
                fullWidth
                label="Password"
                type={showPassword ? 'text' : 'password'}
                margin="normal"
                {...loginForm.register('password', {
                  required: 'Password is required',
                  minLength: {
                    value: 6,
                    message: 'Password must be at least 6 characters',
                  },
                })}
                error={!!loginForm.formState.errors.password}
                helperText={loginForm.formState.errors.password?.message}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loginForm.formState.isSubmitting}
                sx={{ mt: 3, mb: 2, py: 1.5 }}
              >
                {loginForm.formState.isSubmitting ? 'Signing In...' : 'Sign In'}
              </Button>
            </form>
          )}

          {activeTab === 1 && (
            <form onSubmit={signupForm.handleSubmit(onSignupSubmit)}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="First Name"
                  margin="normal"
                  {...signupForm.register('firstName', {
                    required: 'First name is required',
                    minLength: {
                      value: 2,
                      message: 'First name must be at least 2 characters',
                    },
                  })}
                  error={!!signupForm.formState.errors.firstName}
                  helperText={signupForm.formState.errors.firstName?.message}
                />

                <TextField
                  fullWidth
                  label="Last Name"
                  margin="normal"
                  {...signupForm.register('lastName', {
                    required: 'Last name is required',
                    minLength: {
                      value: 2,
                      message: 'Last name must be at least 2 characters',
                    },
                  })}
                  error={!!signupForm.formState.errors.lastName}
                  helperText={signupForm.formState.errors.lastName?.message}
                />
              </Box>

              <TextField
                fullWidth
                label="Email Address"
                type="email"
                margin="normal"
                {...signupForm.register('email', {
                  required: 'Email is required',
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Invalid email address',
                  },
                })}
                error={!!signupForm.formState.errors.email}
                helperText={signupForm.formState.errors.email?.message}
              />

              <TextField
                fullWidth
                label="Password"
                type={showPassword ? 'text' : 'password'}
                margin="normal"
                {...signupForm.register('password', {
                  required: 'Password is required',
                  minLength: {
                    value: 6,
                    message: 'Password must be at least 6 characters',
                  },
                })}
                error={!!signupForm.formState.errors.password}
                helperText={signupForm.formState.errors.password?.message}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <TextField
                fullWidth
                label="Confirm Password"
                type={showConfirmPassword ? 'text' : 'password'}
                margin="normal"
                {...signupForm.register('confirmPassword', {
                  required: 'Please confirm your password',
                })}
                error={!!signupForm.formState.errors.confirmPassword}
                helperText={signupForm.formState.errors.confirmPassword?.message}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        edge="end"
                      >
                        {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={signupForm.formState.isSubmitting}
                sx={{ mt: 3, mb: 2, py: 1.5 }}
              >
                {signupForm.formState.isSubmitting ? 'Creating Account...' : 'Create Account'}
              </Button>
            </form>
          )}

          <Divider sx={{ my: 3 }} />
          
          <Box textAlign="center">
            <Typography variant="body2" color="textSecondary">
              {activeTab === 0 
                ? "Don't have an account? Click Sign Up above" 
                : "Already have an account? Click Sign In above"
              }
            </Typography>
            
            {activeTab === 0 && (
              <Box mt={2} p={2} sx={{ backgroundColor: 'grey.50', borderRadius: 1 }}>
                <Typography variant="caption" color="textSecondary">
                  <strong>Demo Credentials:</strong><br />
                  Email: demo@example.com<br />
                  Password: demo123
                </Typography>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default LoginPage;