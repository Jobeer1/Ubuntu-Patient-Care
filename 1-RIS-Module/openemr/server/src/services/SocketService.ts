import { Server } from 'socket.io';
import { logger } from '../utils/logger';

export class SocketService {
  private io: Server;

  constructor(io: Server) {
    this.io = io;
  }

  // Emit workflow status updates
  emitWorkflowUpdate(studyOrderId: string, status: string, step?: string) {
    this.io.to(`workflow-${studyOrderId}`).emit('workflow-update', {
      studyOrderId,
      status,
      step,
      timestamp: new Date().toISOString(),
    });

    logger.info(`Workflow update emitted for study ${studyOrderId}: ${status}`);
  }

  // Emit patient updates
  emitPatientUpdate(patientId: string, updateType: string, data: any) {
    this.io.to(`patient-${patientId}`).emit('patient-update', {
      patientId,
      updateType,
      data,
      timestamp: new Date().toISOString(),
    });

    logger.info(`Patient update emitted for patient ${patientId}: ${updateType}`);
  }

  // Emit claim status updates
  emitClaimUpdate(claimId: string, status: string, data?: any) {
    this.io.to(`claim-${claimId}`).emit('claim-update', {
      claimId,
      status,
      data,
      timestamp: new Date().toISOString(),
    });

    logger.info(`Claim update emitted for claim ${claimId}: ${status}`);
  }

  // Emit system notifications
  emitSystemNotification(message: string, type: 'info' | 'warning' | 'error' | 'success' = 'info', userId?: string) {
    const notification = {
      message,
      type,
      timestamp: new Date().toISOString(),
    };

    if (userId) {
      this.io.to(`user-${userId}`).emit('notification', notification);
    } else {
      this.io.emit('notification', notification);
    }

    logger.info(`System notification emitted: ${message} (${type})`);
  }

  // Emit medical aid verification results
  emitMedicalAidVerification(patientId: string, result: any) {
    this.io.to(`patient-${patientId}`).emit('medical-aid-verification', {
      patientId,
      result,
      timestamp: new Date().toISOString(),
    });

    logger.info(`Medical aid verification result emitted for patient ${patientId}`);
  }

  // Emit Healthbridge status updates
  emitHealthbridgeStatus(status: 'connected' | 'disconnected' | 'error', message?: string) {
    this.io.emit('healthbridge-status', {
      status,
      message,
      timestamp: new Date().toISOString(),
    });

    logger.info(`Healthbridge status emitted: ${status}`);
  }

  // Get connected clients count
  getConnectedClientsCount(): number {
    return this.io.engine.clientsCount;
  }

  // Get room members count
  getRoomMembersCount(room: string): number {
    const roomMembers = this.io.sockets.adapter.rooms.get(room);
    return roomMembers ? roomMembers.size : 0;
  }
}