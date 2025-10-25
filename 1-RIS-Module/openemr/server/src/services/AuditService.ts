import { prisma } from '../index';
import { logger } from '../utils/logger';

export class AuditService {
  async logAction(
    userId: string | undefined,
    tableName: string,
    recordId: string,
    action: string,
    oldValues?: any,
    newValues?: any,
    ipAddress?: string,
    userAgent?: string
  ) {
    try {
      await prisma.auditLog.create({
        data: {
          userId,
          action,
          tableName,
          recordId,
          oldValues: oldValues ? JSON.parse(JSON.stringify(oldValues)) : null,
          newValues: newValues ? JSON.parse(JSON.stringify(newValues)) : null,
          ipAddress,
          userAgent,
        },
      });

      logger.info(`Audit log created: ${action} on ${tableName}:${recordId} by user:${userId}`);
    } catch (error) {
      logger.error('Failed to create audit log:', error);
      // Don't throw error to avoid breaking the main operation
    }
  }

  async logAccess(
    userId: string | undefined,
    tableName: string,
    recordId: string,
    action: string = 'VIEW',
    ipAddress?: string,
    userAgent?: string
  ) {
    return this.logAction(userId, tableName, recordId, action, null, null, ipAddress, userAgent);
  }

  async getAuditLogs(
    tableName?: string,
    recordId?: string,
    userId?: string,
    limit: number = 100,
    offset: number = 0
  ) {
    const where: any = {};
    
    if (tableName) where.tableName = tableName;
    if (recordId) where.recordId = recordId;
    if (userId) where.userId = userId;

    return await prisma.auditLog.findMany({
      where,
      include: {
        user: {
          select: {
            firstName: true,
            lastName: true,
            email: true,
          },
        },
      },
      orderBy: { timestamp: 'desc' },
      take: limit,
      skip: offset,
    });
  }

  async getPatientAuditTrail(patientId: string) {
    return await prisma.auditLog.findMany({
      where: {
        OR: [
          { patientId },
          { tableName: 'patients', recordId: patientId },
        ],
      },
      include: {
        user: {
          select: {
            firstName: true,
            lastName: true,
            email: true,
          },
        },
      },
      orderBy: { timestamp: 'desc' },
    });
  }

  async getSystemAuditSummary(days: number = 30) {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    const summary = await prisma.auditLog.groupBy({
      by: ['action', 'tableName'],
      where: {
        timestamp: {
          gte: startDate,
        },
      },
      _count: {
        id: true,
      },
      orderBy: {
        _count: {
          id: 'desc',
        },
      },
    });

    return summary;
  }
}