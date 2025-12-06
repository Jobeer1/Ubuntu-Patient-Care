import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Avatar,
  Button,
} from '@mui/material';
import {
  Assignment,
  Note,
  CheckCircle,
  Schedule,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import { useAuth } from '../contexts/AuthContext';
import { tasksAPI, notesAPI } from '../services/api';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const { data: tasksData } = useQuery('tasks', tasksAPI.getTasks);
  const { data: notesData } = useQuery('notes', notesAPI.getNotes);

  const tasks = tasksData?.data?.tasks || [];
  const notes = notesData?.data?.notes || [];
  
  const completedTasks = tasks.filter((task: any) => task.completed).length;
  const pendingTasks = tasks.filter((task: any) => !task.completed).length;

  const stats = [
    {
      title: 'Total Tasks',
      value: tasks.length.toString(),
      subtitle: `${pendingTasks} pending`,
      icon: <Assignment />,
      color: '#1976d2',
      onClick: () => navigate('/tasks'),
    },
    {
      title: 'Completed Tasks',
      value: completedTasks.toString(),
      subtitle: 'This month',
      icon: <CheckCircle />,
      color: '#2e7d32',
      onClick: () => navigate('/tasks'),
    },
    {
      title: 'Total Notes',
      value: notes.length.toString(),
      subtitle: 'Personal notes',
      icon: <Note />,
      color: '#ed6c02',
      onClick: () => navigate('/notes'),
    },
    {
      title: 'Recent Activity',
      value: '5',
      subtitle: 'Last 7 days',
      icon: <Schedule />,
      color: '#9c27b0',
      onClick: () => {},
    },
  ];

  return (
    <Box>
      <Box mb={4}>
        <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
          Welcome back, {user?.firstName}!
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Here's an overview of your tasks and notes.
        </Typography>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} mb={4}>
        {stats.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card 
              sx={{ 
                cursor: 'pointer',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  transition: 'transform 0.2s ease-in-out',
                  boxShadow: 3,
                }
              }}
              onClick={stat.onClick}
            >
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography variant="h4" component="div" fontWeight="bold">
                      {stat.value}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" gutterBottom>
                      {stat.title}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {stat.subtitle}
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: stat.color, width: 56, height: 56 }}>
                    {stat.icon}
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* Recent Tasks */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6" component="h2" fontWeight="bold">
                  Recent Tasks
                </Typography>
                <Button size="small" onClick={() => navigate('/tasks')}>
                  View All
                </Button>
              </Box>
              {tasks.slice(0, 5).map((task: any) => (
                <Box key={task.id} display="flex" alignItems="center" mb={2}>
                  <CheckCircle 
                    sx={{ 
                      mr: 2, 
                      color: task.completed ? 'success.main' : 'grey.400' 
                    }} 
                  />
                  <Box flexGrow={1}>
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        textDecoration: task.completed ? 'line-through' : 'none',
                        opacity: task.completed ? 0.7 : 1 
                      }}
                    >
                      {task.title}
                    </Typography>
                    {task.dueDate && (
                      <Typography variant="caption" color="textSecondary">
                        Due: {new Date(task.dueDate).toLocaleDateString()}
                      </Typography>
                    )}
                  </Box>
                </Box>
              ))}
              {tasks.length === 0 && (
                <Box textAlign="center" py={4}>
                  <Typography variant="body2" color="textSecondary">
                    No tasks yet. Create your first task!
                  </Typography>
                  <Button 
                    variant="outlined" 
                    sx={{ mt: 2 }}
                    onClick={() => navigate('/tasks')}
                  >
                    Add Task
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Notes */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6" component="h2" fontWeight="bold">
                  Recent Notes
                </Typography>
                <Button size="small" onClick={() => navigate('/notes')}>
                  View All
                </Button>
              </Box>
              {notes.slice(0, 5).map((note: any) => (
                <Box key={note.id} mb={2}>
                  <Typography variant="body2" fontWeight="medium">
                    {note.title}
                  </Typography>
                  <Typography 
                    variant="caption" 
                    color="textSecondary"
                    sx={{
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {note.content}
                  </Typography>
                </Box>
              ))}
              {notes.length === 0 && (
                <Box textAlign="center" py={4}>
                  <Typography variant="body2" color="textSecondary">
                    No notes yet. Create your first note!
                  </Typography>
                  <Button 
                    variant="outlined" 
                    sx={{ mt: 2 }}
                    onClick={() => navigate('/notes')}
                  >
                    Add Note
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;