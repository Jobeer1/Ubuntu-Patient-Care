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
  Grid,
  IconButton,
  Paper,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Note,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useForm, Controller } from 'react-hook-form';
import toast from 'react-hot-toast';
import { notesAPI } from '../services/api';
import LoadingSpinner from '../components/Common/LoadingSpinner';

interface NoteFormData {
  title: string;
  content: string;
}

const NotesPage: React.FC = () => {
  const [openDialog, setOpenDialog] = useState(false);
  const [editingNote, setEditingNote] = useState<any>(null);
  const queryClient = useQueryClient();

  const { data: notesData, isLoading } = useQuery('notes', notesAPI.getNotes);

  const { control, handleSubmit, reset, formState: { errors } } = useForm<NoteFormData>({
    defaultValues: {
      title: '',
      content: '',
    },
  });

  const createNoteMutation = useMutation(notesAPI.createNote, {
    onSuccess: () => {
      queryClient.invalidateQueries('notes');
      toast.success('Note created successfully!');
      handleCloseDialog();
    },
    onError: () => {
      toast.error('Failed to create note');
    },
  });

  const updateNoteMutation = useMutation(
    ({ id, data }: { id: string; data: any }) => notesAPI.updateNote(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('notes');
        toast.success('Note updated successfully!');
        handleCloseDialog();
      },
      onError: () => {
        toast.error('Failed to update note');
      },
    }
  );

  const deleteNoteMutation = useMutation(notesAPI.deleteNote, {
    onSuccess: () => {
      queryClient.invalidateQueries('notes');
      toast.success('Note deleted successfully!');
    },
    onError: () => {
      toast.error('Failed to delete note');
    },
  });

  const handleOpenDialog = (note?: any) => {
    if (note) {
      setEditingNote(note);
      reset({
        title: note.title,
        content: note.content,
      });
    } else {
      setEditingNote(null);
      reset({
        title: '',
        content: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingNote(null);
    reset();
  };

  const onSubmit = (data: NoteFormData) => {
    if (editingNote) {
      updateNoteMutation.mutate({ id: editingNote.id, data });
    } else {
      createNoteMutation.mutate(data);
    }
  };

  const handleDeleteNote = (noteId: string) => {
    if (window.confirm('Are you sure you want to delete this note?')) {
      deleteNoteMutation.mutate(noteId);
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LoadingSpinner message="Loading notes..." />
      </Box>
    );
  }

  const notes = notesData?.data?.notes || [];

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          My Notes
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => handleOpenDialog()}
        >
          Add Note
        </Button>
      </Box>

      {notes.length === 0 ? (
        <Card>
          <CardContent>
            <Box textAlign="center" py={8}>
              <Note sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                No Notes Yet
              </Typography>
              <Typography variant="body2" color="textSecondary" mb={3}>
                Create your first note to get started.
              </Typography>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => handleOpenDialog()}
              >
                Add Your First Note
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {notes.map((note: any) => (
            <Grid item xs={12} sm={6} md={4} key={note.id}>
              <Paper
                elevation={2}
                sx={{
                  p: 2,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  cursor: 'pointer',
                  '&:hover': {
                    elevation: 4,
                    transform: 'translateY(-2px)',
                    transition: 'all 0.2s ease-in-out',
                  },
                }}
                onClick={() => handleOpenDialog(note)}
              >
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                  <Typography variant="h6" component="h3" fontWeight="bold" noWrap>
                    {note.title}
                  </Typography>
                  <Box>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenDialog(note);
                      }}
                    >
                      <Edit />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteNote(note.id);
                      }}
                    >
                      <Delete />
                    </IconButton>
                  </Box>
                </Box>
                
                <Typography
                  variant="body2"
                  color="textSecondary"
                  sx={{
                    flexGrow: 1,
                    overflow: 'hidden',
                    display: '-webkit-box',
                    WebkitLineClamp: 6,
                    WebkitBoxOrient: 'vertical',
                    lineHeight: 1.5,
                  }}
                >
                  {note.content}
                </Typography>
                
                <Typography variant="caption" color="textSecondary" sx={{ mt: 2 }}>
                  Updated: {new Date(note.updatedAt).toLocaleDateString()}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Note Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>
            {editingNote ? 'Edit Note' : 'Add New Note'}
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
                    label="Note Title"
                    fullWidth
                    error={!!errors.title}
                    helperText={errors.title?.message}
                  />
                )}
              />

              <Controller
                name="content"
                control={control}
                rules={{ required: 'Content is required' }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Note Content"
                    fullWidth
                    multiline
                    rows={12}
                    error={!!errors.content}
                    helperText={errors.content?.message}
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
              disabled={createNoteMutation.isLoading || updateNoteMutation.isLoading}
            >
              {editingNote ? 'Update' : 'Create'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default NotesPage;