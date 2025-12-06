import express from 'express';
import { asyncHandler } from '../middleware/errorHandler';

const router = express.Router();

// Get financial reports
router.get('/financial', asyncHandler(async (req, res) => {
  res.json({
    success: true,
    message: 'Financial reports endpoint - to be implemented',
  });
}));

export default router;