import express from 'express';
import Joi from 'joi';
import { prisma } from '../index';
import { validateRequest } from '../middleware/validation';
import { requireRole } from '../middleware/auth';
import { asyncHandler } from '../middleware/errorHandler';
import { logger } from '../utils/logger';

const router = express.Router();

const createStudyOrderSchema = {
  body: Joi.object({
    patientId: Joi.string().uuid().required(),
    orderingPhysician: Joi.string().min(2).max(100).required(),
    procedureCode: Joi.string().required(),
    procedureDesc: Joi.string().required(),
    nrplCode: Joi.string().required(),
    tariff: Joi.number().positive().required(),
    indication: Joi.string().required(),
    icd10Codes: Joi.array().items(Joi.string()).min(1).required(),
    urgency: Joi.string().valid('ROUTINE', 'URGENT', 'STAT').default('ROUTINE'),
    preferredDate: Joi.date().optional(),
    specialInstructions: Joi.string().optional(),
  }),
};

// Get all study orders with filtering
router.get('/', asyncHandler(async (req, res) => {
  const { 
    patientId, 
    status, 
    urgency, 
    page = 1, 
    limit = 20,
    sortBy = 'createdAt',
    sortOrder = 'desc'
  } = req.query as any;

  const skip = (page - 1) * limit;
  const where: any = {};

  if (patientId) where.patientId = patientId;
  if (status) where.status = status;
  if (urgency) where.urgency = urgency;

  const [studyOrders, total] = await Promise.all([
    prisma.studyOrder.findMany({
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
            medicalAidScheme: true,
          },
        },
        workflowSteps: {
          orderBy: { stepNumber: 'asc' },
        },
      },
    }),
    prisma.studyOrder.count({ where }),
  ]);

  res.json({
    success: true,
    data: {
      studyOrders,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
      },
    },
  });
}));

// Create new study order
router.post('/',
  requireRole(['ADMIN', 'RADIOLOGIST', 'TECHNOLOGIST']),
  validateRequest(createStudyOrderSchema),
  asyncHandler(async (req, res) => {
    const orderData = req.body;

    // Verify patient exists
    const patient = await prisma.patient.findUnique({
      where: { id: orderData.patientId },
    });

    if (!patient) {
      return res.status(404).json({
        success: false,
        error: {
          code: 'PATIENT_NOT_FOUND',
          message: 'Patient not found',
        },
      });
    }

    // Create study order with initial workflow steps
    const studyOrder = await prisma.studyOrder.create({
      data: {
        ...orderData,
        workflowSteps: {
          create: [
            { stepNumber: 1, stepName: 'Order Received', status: 'COMPLETED' },
            { stepNumber: 2, stepName: 'Patient Registration', status: 'PENDING' },
            { stepNumber: 3, stepName: 'Pre-Authorization', status: 'PENDING' },
            { stepNumber: 4, stepName: 'Appointment Scheduled', status: 'PENDING' },
            { stepNumber: 5, stepName: 'Study Acquired', status: 'PENDING' },
            { stepNumber: 6, stepName: 'Study Reported', status: 'PENDING' },
            { stepNumber: 7, stepName: 'Results Delivered', status: 'PENDING' },
          ],
        },
      },
      include: {
        patient: true,
        workflowSteps: true,
      },
    });

    logger.info(`Study order created: ${studyOrder.id} for patient ${patient.firstName} ${patient.lastName}`);

    res.status(201).json({
      success: true,
      data: { studyOrder },
    });
  })
);

// Get study order by ID
router.get('/:id', asyncHandler(async (req, res) => {
  const { id } = req.params;

  const studyOrder = await prisma.studyOrder.findUnique({
    where: { id },
    include: {
      patient: true,
      workflowSteps: {
        orderBy: { stepNumber: 'asc' },
      },
      claims: true,
    },
  });

  if (!studyOrder) {
    return res.status(404).json({
      success: false,
      error: {
        code: 'STUDY_ORDER_NOT_FOUND',
        message: 'Study order not found',
      },
    });
  }

  res.json({
    success: true,
    data: { studyOrder },
  });
}));

// Update study order status
router.patch('/:id/status', 
  requireRole(['ADMIN', 'RADIOLOGIST', 'TECHNOLOGIST']),
  asyncHandler(async (req, res) => {
    const { id } = req.params;
    const { status } = req.body;

    const studyOrder = await prisma.studyOrder.update({
      where: { id },
      data: { status },
      include: {
        patient: true,
        workflowSteps: true,
      },
    });

    logger.info(`Study order ${id} status updated to: ${status}`);

    res.json({
      success: true,
      data: { studyOrder },
    });
  })
);

export default router;