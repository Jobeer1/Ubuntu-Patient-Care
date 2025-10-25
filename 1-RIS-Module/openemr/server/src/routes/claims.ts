import express from 'express';
import Joi from 'joi';
import { prisma } from '../index';
import { validateRequest } from '../middleware/validation';
import { requireRole } from '../middleware/auth';
import { asyncHandler } from '../middleware/errorHandler';
import { logger } from '../utils/logger';

const router = express.Router();

// Get all claims
router.get('/', asyncHandler(async (req, res) => {
  const { 
    status, 
    patientId, 
    page = 1, 
    limit = 20,
    sortBy = 'createdAt',
    sortOrder = 'desc'
  } = req.query as any;

  const skip = (page - 1) * limit;
  const where: any = {};

  if (status) where.status = status;
  if (patientId) where.patientId = patientId;

  const [claims, total] = await Promise.all([
    prisma.claim.findMany({
      where,
      skip,
      take: limit,
      orderBy: { [sortBy]: sortOrder },
      include: {
        patient: {
          select: {
            firstName: true,
            lastName: true,
            idNumber: true,
          },
        },
        medicalAidScheme: {
          select: {
            name: true,
            code: true,
          },
        },
        claimItems: true,
      },
    }),
    prisma.claim.count({ where }),
  ]);

  res.json({
    success: true,
    data: {
      claims,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
      },
    },
  });
}));

// Create new claim
router.post('/',
  requireRole(['ADMIN', 'BILLING_CLERK']),
  asyncHandler(async (req, res) => {
    // Implementation for creating claims
    res.json({
      success: true,
      message: 'Claim creation endpoint - to be implemented',
    });
  })
);

export default router;