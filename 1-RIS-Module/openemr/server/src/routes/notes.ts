import express from 'express';
import Joi from 'joi';
import { prisma } from '../index';
import { validateRequest } from '../middleware/validation';
import { asyncHandler } from '../middleware/errorHandler';
import { logger } from '../utils/logger';

const router = express.Router();

// Validation schemas
const createNoteSchema = {
  body: Joi.object({
    title: Joi.string().min(1).max(200).required(),
    content: Joi.string().min(1).required(),
  }),
};

const updateNoteSchema = {
  body: Joi.object({
    title: Joi.string().min(1).max(200).optional(),
    content: Joi.string().min(1).optional(),
  }),
};

// Get all notes for user
router.get('/', asyncHandler(async (req, res) => {
  const userId = (req as any).user.id;
  
  const notes = await prisma.note.findMany({
    where: { userId },
    orderBy: { updatedAt: 'desc' },
  });

  res.json({
    success: true,
    data: { notes },
  });
}));

// Get single note
router.get('/:id', asyncHandler(async (req, res) => {
  const userId = (req as any).user.id;
  const noteId = req.params.id;
  
  const note = await prisma.note.findFirst({
    where: { id: noteId, userId },
  });

  if (!note) {
    return res.status(404).json({
      success: false,
      error: {
        code: 'NOTE_NOT_FOUND',
        message: 'Note not found',
      },
    });
  }

  res.json({
    success: true,
    data: { note },
  });
}));

// Create new note
router.post('/', validateRequest(createNoteSchema), asyncHandler(async (req, res) => {
  const userId = (req as any).user.id;
  const { title, content } = req.body;

  const note = await prisma.note.create({
    data: {
      title,
      content,
      userId,
    },
  });

  logger.info(`Note created: ${note.id} by user: ${userId}`);

  res.status(201).json({
    success: true,
    data: { note },
  });
}));

// Update note
router.put('/:id', validateRequest(updateNoteSchema), asyncHandler(async (req, res) => {
  const userId = (req as any).user.id;
  const noteId = req.params.id;
  const updates = req.body;

  // Check if note belongs to user
  const existingNote = await prisma.note.findFirst({
    where: { id: noteId, userId },
  });

  if (!existingNote) {
    return res.status(404).json({
      success: false,
      error: {
        code: 'NOTE_NOT_FOUND',
        message: 'Note not found',
      },
    });
  }

  const note = await prisma.note.update({
    where: { id: noteId },
    data: updates,
  });

  res.json({
    success: true,
    data: { note },
  });
}));

// Delete note
router.delete('/:id', asyncHandler(async (req, res) => {
  const userId = (req as any).user.id;
  const noteId = req.params.id;

  // Check if note belongs to user
  const existingNote = await prisma.note.findFirst({
    where: { id: noteId, userId },
  });

  if (!existingNote) {
    return res.status(404).json({
      success: false,
      error: {
        code: 'NOTE_NOT_FOUND',
        message: 'Note not found',
      },
    });
  }

  await prisma.note.delete({
    where: { id: noteId },
  });

  res.json({
    success: true,
    message: 'Note deleted successfully',
  });
}));

export default router;