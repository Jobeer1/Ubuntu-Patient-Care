import express from 'express';
import { requireRole } from '../middleware/auth';
import { asyncHandler } from '../middleware/errorHandler';

const router = express.Router();

// Admin-only routes
router.use(requireRole(['ADMIN']));

// Get system status
router.get('/system-status', asyncHandler(async (req, res) => {
  res.json({
    success: true,
    data: {
      status: 'online',
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      timestamp: new Date().toISOString(),
    },
  });
}));

export default router;