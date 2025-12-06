import express from 'express';
import { asyncHandler } from '../middleware/errorHandler';
import { MedicalAidService } from '../services/MedicalAidService';

const router = express.Router();
const medicalAidService = new MedicalAidService();

// Get all medical aid schemes
router.get('/', asyncHandler(async (req, res) => {
  const schemes = await medicalAidService.getAllSchemes();

  res.json({
    success: true,
    data: { schemes },
  });
}));

// Get medical aid scheme by code
router.get('/:code', asyncHandler(async (req, res) => {
  const { code } = req.params;
  const scheme = await medicalAidService.getSchemeByCode(code);

  if (!scheme) {
    return res.status(404).json({
      success: false,
      error: {
        code: 'SCHEME_NOT_FOUND',
        message: 'Medical aid scheme not found',
      },
    });
  }

  res.json({
    success: true,
    data: { scheme },
  });
}));

export default router;