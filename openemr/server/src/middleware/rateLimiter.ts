import rateLimit from 'express-rate-limit';
import { Request, Response } from 'express';

// General API rate limiter
export const rateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // Limit each IP to 1000 requests per windowMs
  message: {
    success: false,
    error: {
      code: 'RATE_LIMIT_EXCEEDED',
      message: 'Too many requests from this IP, please try again later.',
    },
  },
  standardHeaders: true,
  legacyHeaders: false,
});

// Strict rate limiter for authentication endpoints
export const authRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 10, // Limit each IP to 10 login attempts per windowMs
  message: {
    success: false,
    error: {
      code: 'AUTH_RATE_LIMIT_EXCEEDED',
      message: 'Too many authentication attempts, please try again later.',
    },
  },
  standardHeaders: true,
  legacyHeaders: false,
  skipSuccessfulRequests: true, // Don't count successful requests
});

// Medical Aid API rate limiter (more restrictive due to external API limits)
export const medicalAidRateLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 30, // Limit each IP to 30 medical aid requests per minute
  message: {
    success: false,
    error: {
      code: 'MEDICAL_AID_RATE_LIMIT_EXCEEDED',
      message: 'Too many medical aid verification requests, please try again later.',
    },
  },
  standardHeaders: true,
  legacyHeaders: false,
});

// Healthbridge API rate limiter
export const healthbridgeRateLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 20, // Limit each IP to 20 Healthbridge requests per minute
  message: {
    success: false,
    error: {
      code: 'HEALTHBRIDGE_RATE_LIMIT_EXCEEDED',
      message: 'Too many Healthbridge requests, please try again later.',
    },
  },
  standardHeaders: true,
  legacyHeaders: false,
});