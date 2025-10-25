import express from 'express';
import Joi from 'joi';
import { prisma } from '../index';
import { validateRequest } from '../middleware/validation';
import { requireRole } from '../middleware/auth';
import { asyncHandler } from '../middleware/errorHandler';
import { logger } from '../utils/logger';
import { MedicalAidService } from '../services/MedicalAidService';
import { AuditService } from '../services/AuditService';

const router = express.Router();
const medicalAidService = new MedicalAidService();
const auditService = new AuditService();

// Validation schemas
const createPatientSchema = {
  body: Joi.object({
    firstName: Joi.string().min(2).max(50).required(),
    lastName: Joi.string().min(2).max(50).required(),
    idNumber: Joi.string().length(13).pattern(/^\d+$/).required(),
    dateOfBirth: Joi.date().max('now').required(),
    gender: Joi.string().valid('M', 'F', 'O').required(),
    phoneNumber: Joi.string().optional(),
    email: Joi.string().email().optional(),
    address: Joi.string().optional(),
    city: Joi.string().optional(),
    province: Joi.string().optional(),
    postalCode: Joi.string().optional(),
    medicalAidScheme: Joi.string().optional(),
    memberNumber: Joi.string().optional(),
    dependentCode: Joi.string().optional(),
    allergies: Joi.array().items(Joi.string()).optional(),
    chronicConditions: Joi.array().items(Joi.string()).optional(),
    currentMedications: Joi.array().items(Joi.string()).optional(),
  }),
};

const updatePatientSchema = {
  body: Joi.object({
    firstName: Joi.string().min(2).max(50).optional(),
    lastName: Joi.string().min(2).max(50).optional(),
    phoneNumber: Joi.string().optional(),
    email: Joi.string().email().optional(),
    address: Joi.string().optional(),
    city: Joi.string().optional(),
    province: Joi.string().optional(),
    postalCode: Joi.string().optional(),
    medicalAidScheme: Joi.string().optional(),
    memberNumber: Joi.string().optional(),
    dependentCode: Joi.string().optional(),
    allergies: Joi.array().items(Joi.string()).optional(),
    chronicConditions: Joi.array().items(Joi.string()).optional(),
    currentMedications: Joi.array().items(Joi.string()).optional(),
  }),
  params: Joi.object({
    id: Joi.string().uuid().required(),
  }),
};

const searchPatientsSchema = {
  query: Joi.object({
    search: Joi.string().optional(),
    page: Joi.number().integer().min(1).default(1),
    limit: Joi.number().integer().min(1).max(100).default(20),
    sortBy: Joi.string().valid('firstName', 'lastName', 'createdAt', 'idNumber').default('createdAt'),
    sortOrder: Joi.string().valid('asc', 'desc').default('desc'),
  }),
};

// Get all patients with search and pagination
router.get('/', validateRequest(searchPatientsSchema), asyncHandler(async (req, res) => {
  const { search, page, limit, sortBy, sortOrder } = req.query as any;
  const skip = (page - 1) * limit;

  // Build search conditions
  const searchConditions = search ? {
    OR: [
      { firstName: { contains: search, mode: 'insensitive' } },
      { lastName: { contains: search, mode: 'insensitive' } },
      { idNumber: { contains: search } },
      { memberNumber: { contains: search } },
    ],
  } : {};

  // Get patients with pagination
  const [patients, total] = await Promise.all([
    prisma.patient.findMany({
      where: searchConditions,
      skip,
      take: limit,
      orderBy: { [sortBy]: sortOrder },
      select: {
        id: true,
        firstName: true,
        lastName: true,
        idNumber: true,
        dateOfBirth: true,
        gender: true,
        phoneNumber: true,
        email: true,
        medicalAidScheme: true,
        memberNumber: true,
        medicalAidStatus: true,
        createdAt: true,
        updatedAt: true,
      },
    }),
    prisma.patient.count({ where: searchConditions }),
  ]);

  res.json({
    success: true,
    data: {
      patients,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
      },
    },
  });
}));

// Get patient by ID
router.get('/:id', asyncHandler(async (req, res) => {
  const { id } = req.params;

  const patient = await prisma.patient.findUnique({
    where: { id },
    include: {
      studyOrders: {
        orderBy: { createdAt: 'desc' },
        take: 10,
      },
      claims: {
        orderBy: { createdAt: 'desc' },
        take: 10,
      },
    },
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

  // Log patient access for audit
  await auditService.logAccess(req.user?.id, 'patients', id, 'VIEW');

  res.json({
    success: true,
    data: { patient },
  });
}));

// Create new patient
router.post('/', 
  requireRole(['ADMIN', 'RECEPTIONIST', 'TECHNOLOGIST']),
  validateRequest(createPatientSchema), 
  asyncHandler(async (req, res) => {
    const patientData = req.body;

    // Check if patient with same ID number already exists
    const existingPatient = await prisma.patient.findUnique({
      where: { idNumber: patientData.idNumber },
    });

    if (existingPatient) {
      return res.status(400).json({
        success: false,
        error: {
          code: 'PATIENT_EXISTS',
          message: 'Patient with this ID number already exists',
        },
      });
    }

    // Create patient
    const patient = await prisma.patient.create({
      data: {
        ...patientData,
        medicalAidStatus: 'UNKNOWN',
      },
    });

    // Verify medical aid if provided
    if (patientData.medicalAidScheme && patientData.memberNumber) {
      try {
        const medicalAidStatus = await medicalAidService.verifyMembership(
          patientData.memberNumber,
          patientData.medicalAidScheme
        );
        
        await prisma.patient.update({
          where: { id: patient.id },
          data: { medicalAidStatus: medicalAidStatus.isActive ? 'ACTIVE' : 'INACTIVE' },
        });
      } catch (error) {
        logger.warn(`Failed to verify medical aid for patient ${patient.id}:`, error);
      }
    }

    // Log patient creation
    await auditService.logAction(req.user?.id, 'patients', patient.id, 'CREATE', null, patient);

    logger.info(`Patient created: ${patient.firstName} ${patient.lastName} (${patient.idNumber})`);

    res.status(201).json({
      success: true,
      data: { patient },
    });
  })
);

// Update patient
router.put('/:id',
  requireRole(['ADMIN', 'RECEPTIONIST', 'TECHNOLOGIST']),
  validateRequest(updatePatientSchema),
  asyncHandler(async (req, res) => {
    const { id } = req.params;
    const updateData = req.body;

    // Get current patient data for audit
    const currentPatient = await prisma.patient.findUnique({
      where: { id },
    });

    if (!currentPatient) {
      return res.status(404).json({
        success: false,
        error: {
          code: 'PATIENT_NOT_FOUND',
          message: 'Patient not found',
        },
      });
    }

    // Update patient
    const updatedPatient = await prisma.patient.update({
      where: { id },
      data: updateData,
    });

    // Re-verify medical aid if medical aid details changed
    if (updateData.medicalAidScheme || updateData.memberNumber) {
      try {
        const medicalAidStatus = await medicalAidService.verifyMembership(
          updatedPatient.memberNumber || '',
          updatedPatient.medicalAidScheme || ''
        );
        
        await prisma.patient.update({
          where: { id },
          data: { medicalAidStatus: medicalAidStatus.isActive ? 'ACTIVE' : 'INACTIVE' },
        });
      } catch (error) {
        logger.warn(`Failed to verify medical aid for patient ${id}:`, error);
      }
    }

    // Log patient update
    await auditService.logAction(req.user?.id, 'patients', id, 'UPDATE', currentPatient, updatedPatient);

    logger.info(`Patient updated: ${updatedPatient.firstName} ${updatedPatient.lastName} (${updatedPatient.idNumber})`);

    res.json({
      success: true,
      data: { patient: updatedPatient },
    });
  })
);

// Verify medical aid
router.post('/:id/verify-medical-aid', asyncHandler(async (req, res) => {
  const { id } = req.params;

  const patient = await prisma.patient.findUnique({
    where: { id },
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

  if (!patient.medicalAidScheme || !patient.memberNumber) {
    return res.status(400).json({
      success: false,
      error: {
        code: 'MISSING_MEDICAL_AID_INFO',
        message: 'Patient medical aid information is incomplete',
      },
    });
  }

  try {
    const verificationResult = await medicalAidService.verifyMembership(
      patient.memberNumber,
      patient.medicalAidScheme
    );

    // Update patient medical aid status
    await prisma.patient.update({
      where: { id },
      data: { 
        medicalAidStatus: verificationResult.isActive ? 'ACTIVE' : 'INACTIVE' 
      },
    });

    res.json({
      success: true,
      data: { 
        verificationResult,
        message: 'Medical aid verification completed',
      },
    });
  } catch (error) {
    logger.error(`Medical aid verification failed for patient ${id}:`, error);
    
    res.status(500).json({
      success: false,
      error: {
        code: 'VERIFICATION_FAILED',
        message: 'Failed to verify medical aid membership',
      },
    });
  }
}));

// Delete patient (soft delete - mark as inactive)
router.delete('/:id',
  requireRole(['ADMIN']),
  asyncHandler(async (req, res) => {
    const { id } = req.params;

    const patient = await prisma.patient.findUnique({
      where: { id },
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

    // In a real system, we would implement soft delete
    // For now, we'll just log the deletion attempt
    await auditService.logAction(req.user?.id, 'patients', id, 'DELETE_ATTEMPT', patient, null);

    logger.warn(`Patient deletion attempted: ${patient.firstName} ${patient.lastName} (${patient.idNumber})`);

    res.json({
      success: true,
      message: 'Patient deletion logged. Implement soft delete in production.',
    });
  })
);

export default router;