import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Checkbox,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  CheckCircle,
  RadioButtonUnchecked,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useForm, Controller } from 'react-hook-form';
import toast from 'react-hot-toast';
import { tasksAPI } from '../services/api';
import LoadingSpinner from '../components/Common/LoadingSpinner';

interface TaskFormData {
  title: string;
  description: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
  dueDate: string;
}

const TasksPage: React.FC = () => {
  const [openDialog, setOpenDialog] = useState(false);
  const [editingTask, setEditingTask] = useState<any>(null);
  const queryClient = useQueryClient();

  const { data: tasksData, isLoading } = useQuery('tasks', tasksAPI.getTasks);

  const { control, handleSubmit, reset, formState: { errors } } = useForm<TaskFormData>({
    defaultValues: {
      title: '',
      description: '',
      priority: 'MEDIUM',
      dueDate: '',
    },
  });

  const createTaskMutation = useMutation(tasksAPI.createTask, {
    onSuccess: () => {
      queryClient.invalidateQueries('tasks');
      toast.success('Task created successfully!');
      handleCloseDialog();
    },
    onError: () => {
      toast.error('Failed to create task');
    },
  });

  const updateTaskMutation = useMutation(
    ({ id, data }: { id: string; data: any }) => tasksAPI.updateTask(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('tasks');
        toast.success('Task updated successfully!');
      },
      onError: () => {
        toast.error('Failed to update task');
      },
    }
  );

  const deleteTaskMutation = useMutation(tasksAPI.deleteTask, {
    onSuccess: () => {
      queryClient.invalidateQueries('tasks');
      toast.success('Task deleted successfully!');
    },
    onError: () => {
      toast.error('Failed to delete task');
    },
  });

  const handleOpenDialog = (task?: any) => {
    if (task) {
      setEditingTask(task);
      reset({
        title: task.title,
        description: task.description || '',
        priority: task.priority,
        dueDate: task.dueDate ? new Date(task.dueDate).toISOString().split('T')[0] : '',
      });
    } else {
      setEditingTask(null);
      reset({
        title: '',
        description: '',
        priority: 'MEDIUM',
        dueDate: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingTask(null);
    reset();
  };

  const onSubmit = (data: TaskFormData) => {
    const taskData = {
      ...data,
      dueDate: data.dueDate ? new Date(data.dueDate).toISOString() : null,
    };

    if (editingTask) {
      updateTaskMutation.mutate({ id: editingTask.id, data: taskData });
    } else {
      createTaskMutation.mutate(taskData);
    }
  };

  const handleToggleComplete = (task: any) => {
    updateTaskMutation.mutate({
      id: task.id,
      data: { completed: !task.completed },
    });
  };

  const handleDeleteTask = (taskId: string) => {
    if (window.confirm('Are you sure you want to delete this task?')) {
      deleteTaskMutation.mutate(taskId);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'HIGH': return 'error';
      case 'MEDIUM': return 'warning';
      case 'LOW': return 'success';
      default: return 'default';
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LoadingSpinner message="Loading tasks..." />
      </Box>
    );
  }

  const tasks = tasksData?.data?.tasks || [];
  const completedTasks = tasks.filter((task: any) => task.completed);
  const pendingTasks = tasks.filter((task: any) => !task.completed);

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          My Tasks
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => handleOpenDialog()}
        >
          Add Task
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Pending Tasks ({pendingTasks.length})
              </Typography>
              <List>
                {pendingTasks.map((task: any) => (
                  <ListItem key={task.id} divider>
                    <Checkbox
                      checked={false}
                      onChange={() => handleToggleComplete(task)}
                      icon={<RadioButtonUnchecked />}
                      checkedIcon={<CheckCircle />}
                    />
                    <ListItemText
                      primary={task.title}
                      secondary={
                        <Box>
                          {task.description && (
                            <Typography variant="body2" color="textSecondary">
                              {task.description}
                            </Typography>
                          )}
                          <Box display="flex" gap={1} mt={1}>
                            <Chip
                              label={task.priority}
                              size="small"
                              color={getPriorityColor(task.priority)}
                            />
                            {task.dueDate && (
                              <Chip
                                label={`Due: ${new Date(task.dueDate).toLocaleDateString()}`}
                                size="small"
                                variant="outlined"
                              />
                            )}
                          </Box>
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDialog(task)}
                      >
                        <Edit />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteTask(task.id)}
                      >
                        <Delete />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
                {pendingTasks.length === 0 && (
                  <Box textAlign="center" py={4}>
                    <Typography variant="body2" color="textSecondary">
                      No pending tasks
                    </Typography>
                  </Box>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Completed Tasks ({completedTasks.length})
              </Typography>
              <List>
                {completedTasks.map((task: any) => (
                  <ListItem key={task.id} divider>
                    <Checkbox
                      checked={true}
                      onChange={() => handleToggleComplete(task)}
                      icon={<RadioButtonUnchecked />}
                      checkedIcon={<CheckCircle />}
                    />
                    <ListItemText
                      primary={
                        <Typography
                          variant="body1"
                          sx={{ textDecoration: 'line-through', opacity: 0.7 }}
                        >
                          {task.title}
                        </Typography>
                      }
                      secondary={task.description}
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteTask(task.id)}
                      >
                        <Delete />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
                {completedTasks.length === 0 && (
                  <Box textAlign="center" py={4}>
                    <Typography variant="body2" color="textSecondary">
                      No completed tasks
                    </Typography>
                  </Box>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Task Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>
            {editingTask ? 'Edit Task' : 'Add New Task'}
          </DialogTitle>
          <DialogContent>
            <Box display="flex" flexDirection="column" gap={2} mt={1}>
              <Controller
                name="title"
                control={control}
                rules={{ required: 'Title is required' }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Task Title"
                    fullWidth
                    error={!!errors.title}
                    helperText={errors.title?.message}
                  />
                )}
              />

              <Controller
                name="description"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Description"
                    fullWidth
                    multiline
                    rows={3}
                  />
                )}
              />

              <Controller
                name="priority"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth>
                    <InputLabel>Priority</InputLabel>
                    <Select {...field} label="Priority">
                      <MenuItem value="LOW">Low</MenuItem>
                      <MenuItem value="MEDIUM">Medium</MenuItem>
                      <MenuItem value="HIGH">High</MenuItem>
                    </Select>
                  </FormControl>
                )}
              />

              <Controller
                name="dueDate"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Due Date"
                    type="date"
                    fullWidth
                    InputLabelProps={{ shrink: true }}
                  />
                )}
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createTaskMutation.isLoading || updateTaskMutation.isLoading}
            >
              {editingTask ? 'Update' : 'Create'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default TasksPage;