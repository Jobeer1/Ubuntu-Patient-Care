import axios from 'axios';
import { logger } from '../utils/logger';
import { prisma } from '../index';

export interface MembershipVerificationResult {
  isActive: boolean;
  memberName?: string;
  benefitStatus?: string;
  dependentStatus?: string;
  schemeOptions?: string[];
  message: string;
}

export interface BenefitCheckResult {
  hasAuthorization: boolean;
  benefitLimit?: number;
  benefitUsed?: number;
  benefitRemaining?: number;
  requiresPreAuth: boolean;
  message: string;
}

export interface PreAuthRequest {
  memberNumber: string;
  dependentCode?: string;
  procedureCode: string;
  diagnosis: string[];
  urgency: 'ROUTINE' | 'URGENT' | 'STAT';
  clinicalNotes?: string;
}

export interface PreAuthResult {
  authorizationNumber?: string;
  status: 'APPROVED' | 'REJECTED' | 'PENDING';
  validUntil?: Date;
  rejectionReason?: string;
  message: string;
}

export class MedicalAidService {
  private async getSchemeConfig(schemeCode: string) {
    const scheme = await prisma.medicalAidScheme.findUnique({
      where: { code: schemeCode, isActive: true },
    });

    if (!scheme) {
      throw new Error(`Medical aid scheme ${schemeCode} not found or inactive`);
    }

    return scheme;
  }

  async verifyMembership(memberNumber: string, schemeCode: string): Promise<MembershipVerificationResult> {
    try {
      const scheme = await this.getSchemeConfig(schemeCode);
      
      // In a real implementation, this would make actual API calls to medical aid schemes
      // For demo purposes, we'll simulate the verification
      
      logger.info(`Verifying membership for ${memberNumber} with ${scheme.name}`);

      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Mock verification logic based on member number patterns
      const isValidFormat = /^\d{10,15}$/.test(memberNumber);
      const isActive = isValidFormat && !memberNumber.endsWith('999'); // Mock: numbers ending in 999 are inactive

      if (!isValidFormat) {
        return {
          isActive: false,
          message: 'Invalid member number format',
        };
      }

      if (isActive) {
        return {
          isActive: true,
          memberName: 'John Doe', // Mock name
          benefitStatus: 'ACTIVE',
          dependentStatus: 'ACTIVE',
          schemeOptions: ['Hospital Plan', 'Savings Account'],
          message: 'Member verification successful',
        };
      } else {
        return {
          isActive: false,
          message: 'Member not found or inactive',
        };
      }
    } catch (error) {
      logger.error(`Medical aid verification failed for ${memberNumber}:`, error);
      throw new Error('Medical aid verification service unavailable');
    }
  }

  async checkBenefits(memberNumber: string, schemeCode: string, procedureCode: string): Promise<BenefitCheckResult> {
    try {
      const scheme = await this.getSchemeConfig(schemeCode);
      
      logger.info(`Checking benefits for ${memberNumber} with ${scheme.name} for procedure ${procedureCode}`);

      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 800));

      // Mock benefit checking logic
      const requiresPreAuth = scheme.preAuthRequired.includes(procedureCode);
      const hasAuthorization = !requiresPreAuth || Math.random() > 0.3; // 70% approval rate for demo

      return {
        hasAuthorization,
        benefitLimit: 50000,
        benefitUsed: 12000,
        benefitRemaining: 38000,
        requiresPreAuth,
        message: hasAuthorization 
          ? 'Benefits available for procedure'
          : 'Pre-authorization required for this procedure',
      };
    } catch (error) {
      logger.error(`Benefit check failed for ${memberNumber}:`, error);
      throw new Error('Benefit checking service unavailable');
    }
  }

  async requestPreAuthorization(request: PreAuthRequest, schemeCode: string): Promise<PreAuthResult> {
    try {
      const scheme = await this.getSchemeConfig(schemeCode);
      
      logger.info(`Requesting pre-authorization for ${request.memberNumber} with ${scheme.name}`);

      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Mock pre-authorization logic
      const isApproved = Math.random() > 0.2; // 80% approval rate for demo
      
      if (isApproved) {
        const authNumber = `AUTH${Date.now()}${Math.floor(Math.random() * 1000)}`;
        const validUntil = new Date();
        validUntil.setDate(validUntil.getDate() + 30); // Valid for 30 days

        return {
          authorizationNumber: authNumber,
          status: 'APPROVED',
          validUntil,
          message: 'Pre-authorization approved',
        };
      } else {
        const rejectionReasons = [
          'Insufficient clinical information provided',
          'Procedure not covered under current benefit option',
          'Annual benefit limit exceeded',
          'Alternative treatment required first',
        ];

        return {
          status: 'REJECTED',
          rejectionReason: rejectionReasons[Math.floor(Math.random() * rejectionReasons.length)],
          message: 'Pre-authorization rejected',
        };
      }
    } catch (error) {
      logger.error(`Pre-authorization request failed:`, error);
      throw new Error('Pre-authorization service unavailable');
    }
  }

  async getAllSchemes() {
    return await prisma.medicalAidScheme.findMany({
      where: { isActive: true },
      select: {
        id: true,
        code: true,
        name: true,
        contactPhone: true,
        contactEmail: true,
        preAuthRequired: true,
      },
      orderBy: { name: 'asc' },
    });
  }

  async getSchemeByCode(code: string) {
    return await prisma.medicalAidScheme.findUnique({
      where: { code, isActive: true },
    });
  }
}