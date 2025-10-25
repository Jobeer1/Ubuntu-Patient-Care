import express from 'express';
import { asyncHandler } from '../middleware/errorHandler';

const router = express.Router();

// Get NRPL codes
router.get('/nrpl-codes', asyncHandler(async (req, res) => {
  res.json({
    success: true,
    message: 'NRPL codes endpoint - to be implemented',
  });
}));

// Get ICD-10 codes
router.get('/icd10-codes', asyncHandler(async (req, res) => {
  res.json({
    success: true,
    message: 'ICD-10 codes endpoint - to be implemented',
  });
}));

export default router;