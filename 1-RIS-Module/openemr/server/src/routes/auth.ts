import express from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import Joi from 'joi';
import { prisma } from '../index';
import { validateRequest } from '../middleware/validation';
import { authRateLimiter } from '../middleware/rateLimiter';
import { asyncHandler } from '../middleware/errorHandler';
import { logger } from '../utils/logger';

const router = express.Router();

// Validation schemas
const loginSchema = {
  body: Joi.object({
    email: Joi.string().email().required(),
    password: Joi.string().min(6).required(),
  }),
};

const registerSchema = {
  body: Joi.object({
    email: Joi.string().email().required(),
    password: Joi.string().min(6).required(),
    firstName: Joi.string().min(2).max(50).required(),
    lastName: Joi.string().min(2).max(50).required(),
  }),
};

const changePasswordSchema = {
  body: Joi.object({
    currentPassword: Joi.string().required(),
    newPassword: Joi.string().min(8).required(),
  }),
};

// Login endpoint
router.post('/login', authRateLimiter, validateRequest(loginSchema), asyncHandler(async (req, res) => {
  const { email, password } = req.body;

  logger.info(`Login attempt for email: ${email}`);

  try {
    // Find user
    const user = await prisma.user.findUnique({
      where: { email: email.toLowerCase() },
    });

    if (!user) {
      logger.warn(`Failed login attempt for email: ${email} - user not found`);
      return res.status(401).json({
        success: false,
        error: {
          code: 'INVALID_CREDENTIALS',
          message: 'Invalid email or password',
        },
      });
    }

  if (!user.isActive) {
    logger.warn(`Failed login attempt for email: ${email} - user inactive`);
    return res.status(401).json({
      success: false,
      error: {
        code: 'ACCOUNT_INACTIVE',
        message: 'Account is inactive',
      },
    });
  }

  // Verify password
  const isValidPassword = await bcrypt.compare(password, user.password);
  if (!isValidPassword) {
    logger.warn(`Failed login attempt for email: ${email} - invalid password`);
    return res.status(401).json({
      success: false,
      error: {
        code: 'INVALID_CREDENTIALS',
        message: 'Invalid email or password',
      },
    });
  }

  // Generate JWT token
  const jwtSecret = process.env.JWT_SECRET;
  if (!jwtSecret) {
    logger.error('JWT_SECRET not configured');
    return res.status(500).json({
      success: false,
      error: {
        code: 'SERVER_ERROR',
        message: 'Server configuration error',
      },
    });
  }

  const token = jwt.sign(
    { 
      id: user.id, 
      email: user.email
    },
    jwtSecret,
    { expiresIn: '24h' }
  );

  // Update last login
  await prisma.user.update({
    where: { id: user.id },
    data: { lastLogin: new Date() },
  });

    logger.info(`Successful login for user: ${user.email}`);

    res.json({
      success: true,
      data: {
        token,
        user: {
          id: user.id,
          email: user.email,
          firstName: user.firstName,
          lastName: user.lastName,
        },
      },
    });
  } catch (error) {
    logger.error('Database error during login:', error);
    return res.status(500).json({
      success: false,
      error: {
        code: 'DATABASE_ERROR',
        message: 'Database connection error. Please try again.',
      },
    });
  }
}));

// Register endpoint
router.post('/register', validateRequest(registerSchema), asyncHandler(async (req, res) => {
  const { email, password, firstName, lastName } = req.body;

  // Check if user already exists
  const existingUser = await prisma.user.findUnique({
    where: { email: email.toLowerCase() },
  });

  if (existingUser) {
    return res.status(400).json({
      success: false,
      error: {
        code: 'USER_EXISTS',
        message: 'User with this email already exists',
      },
    });
  }

  // Hash password
  const hashedPassword = await bcrypt.hash(password, 12);

  // Create user
  const user = await prisma.user.create({
    data: {
      email: email.toLowerCase(),
      password: hashedPassword,
      firstName,
      lastName,
    },
    select: {
      id: true,
      email: true,
      firstName: true,
      lastName: true,
      createdAt: true,
    },
  });

  logger.info(`New user registered: ${user.email}`);

  res.status(201).json({
    success: true,
    data: {
      user,
      message: 'User registered successfully',
    },
  });
}));

// Change password endpoint
router.post('/change-password', validateRequest(changePasswordSchema), asyncHandler(async (req, res) => {
  // This would require authentication middleware in a real implementation
  // For now, we'll implement a basic version
  
  res.json({
    success: true,
    message: 'Password change functionality will be implemented with authentication',
  });
}));

// Logout endpoint
router.post('/logout', asyncHandler(async (req, res) => {
  // In a stateless JWT implementation, logout is handled client-side
  // In production, you might want to implement token blacklisting
  
  res.json({
    success: true,
    message: 'Logged out successfully',
  });
}));

// Verify token endpoint
router.get('/verify', asyncHandler(async (req, res) => {
  const token = req.header('Authorization')?.replace('Bearer ', '');

  if (!token) {
    return res.status(401).json({
      success: false,
      error: {
        code: 'NO_TOKEN',
        message: 'No token provided',
      },
    });
  }

  try {
    const jwtSecret = process.env.JWT_SECRET;
    if (!jwtSecret) {
      throw new Error('JWT_SECRET not configured');
    }

    const decoded = jwt.verify(token, jwtSecret) as any;
    
    const user = await prisma.user.findUnique({
      where: { id: decoded.id },
      select: {
        id: true,
        email: true,
        firstName: true,
        lastName: true,
        isActive: true,
      },
    });

    if (!user || !user.isActive) {
      return res.status(401).json({
        success: false,
        error: {
          code: 'INVALID_TOKEN',
          message: 'Invalid or expired token',
        },
      });
    }

    res.json({
      success: true,
      data: { user },
    });
  } catch (error) {
    return res.status(401).json({
      success: false,
      error: {
        code: 'INVALID_TOKEN',
        message: 'Invalid token',
      },
    });
  }
}));

export default router;