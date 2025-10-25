import express from 'express';
import Joi from 'joi';
import { prisma } from '../index';
import { validateRequest } from '../middleware/validation';
import { asyncHandler } from '../middleware/errorHandler';
import { logger } from '../utils/logger';

const router = express.Router();

// Validation schemas
const createTaskSchema = {
  body: Joi.object({
    title: Joi.string().min(1).max(200).required(),
    description: Joi.string().max(1000).optional(),
    priority: Joi.string().valid('LOW', 'MEDIUM', 'HIGH').default('MEDIUM'),
    dueDate: Joi.date().optional(),
  }),
};

const updateTaskSchema = {
  body: Joi.object({
    title: Joi.string().min(1).max(200).optional(),
    description: Joi.string().max(1000).optional(),
    completed: Joi.boolean().optional(),
    priority: Joi.string().valid('LOW', 'MEDIUM', 'HIGH').optional(),
    dueDate: Joi.date().optional(),
  }),
};

// Get all tasks for user
router.get('/', asyncHandler(async (req, res) => {
  const userId = (req as any).user.id;
  
  const tasks = await prisma.task.findMany({
    where: { userId },
    orderBy: [
      { completed: 'asc' },
      { priority: 'desc' },
      { createdAt: 'desc' }
    ],
  });

  res.json({
    success: true,
    data: { tasks },
  });
}));

// Create new task
router.post('/', validateRequest(createTaskSchema), asyncHandler(async (req, res) => {
  const userId = (req as any).user.id;
  const { title, description, priority, dueDate } = req.body;

  const task = await prisma.task.create({
    data: {
      title,
      description,
      priority: priority || 'MEDIUM',
      dueDate: dueDate ? new Date(dueDate) : null,
      userId,
    },
  });

  logger.info(`Task created: ${task.id} by user: ${userId}`);

  res.status(201).json({
    success: true,
    data: { task },
  });
}));

// Update task
router.put('/:id', validateRequest(updateTaskSchema), asyncHandler(async (req, res) => {
  const userId = (req as any).user.id;
  const taskId = req.params.id;
  const updates = req.body;

  // Check if task belongs to user
  const existingTask = await prisma.task.findFirst({
    where: { id: taskId, userId },
  });

  if (!existingTask) {
    return res.status(404).json({
      success: false,
      error: {
        code: 'TASK_NOT_FOUND',
        message: 'Task not found',
      },
    });
  }

  const task = await prisma.task.update({
    where: { id: taskId },
    data: {
      ...updates,
      dueDate: updates.dueDate ? new Date(updates.dueDate) : undefined,
    },
  });

  res.json({
    success: true,
    data: { task },
  });
}));

// Delete task
router.delete('/:id', asyncHandler(async (req, res) => {
  const userId = (req as any).user.id;
  const taskId = req.params.id;

  // Check if task belongs to user
  const existingTask = await prisma.task.findFirst({
    where: { id: taskId, userId },
  });

  if (!existingTask) {
    return res.status(404).json({
      success: false,
      error: {
        code: 'TASK_NOT_FOUND',
        message: 'Task not found',
      },
    });
  }

  await prisma.task.delete({
    where: { id: taskId },
  });

  res.json({
    success: true,
    message: 'Task deleted successfully',
  });
}));

export default router;