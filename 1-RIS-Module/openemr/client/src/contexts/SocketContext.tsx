import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { io, Socket } from 'socket.io-client';
import toast from 'react-hot-toast';
import { useAuth } from './AuthContext';

interface SocketContextType {
  socket: Socket | null;
  connected: boolean;
  joinRoom: (room: string) => void;
  leaveRoom: (room: string) => void;
}

const SocketContext = createContext<SocketContextType | undefined>(undefined);

interface SocketProviderProps {
  children: ReactNode;
}

export const SocketProvider: React.FC<SocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      const newSocket = io(process.env.REACT_APP_SERVER_URL || 'http://localhost:3001', {
        auth: {
          token: localStorage.getItem('token'),
        },
      });

      newSocket.on('connect', () => {
        console.log('Connected to server');
        setConnected(true);
      });

      newSocket.on('disconnect', () => {
        console.log('Disconnected from server');
        setConnected(false);
      });

      // Listen for notifications
      newSocket.on('notification', (notification) => {
        const { message, type } = notification;
        switch (type) {
          case 'success':
            toast.success(message);
            break;
          case 'error':
            toast.error(message);
            break;
          case 'warning':
            toast(message, { icon: '⚠️' });
            break;
          default:
            toast(message);
        }
      });

      // Listen for workflow updates
      newSocket.on('workflow-update', (update) => {
        toast.success(`Workflow updated: ${update.status}`);
      });

      // Listen for claim updates
      newSocket.on('claim-update', (update) => {
        toast.success(`Claim ${update.claimId}: ${update.status}`);
      });

      // Listen for medical aid verification results
      newSocket.on('medical-aid-verification', (result) => {
        if (result.result.isActive) {
          toast.success('Medical aid verification successful');
        } else {
          toast.error('Medical aid verification failed');
        }
      });

      // Listen for Healthbridge status
      newSocket.on('healthbridge-status', (status) => {
        if (status.status === 'connected') {
          toast.success('Healthbridge connected');
        } else if (status.status === 'disconnected') {
          toast.error('Healthbridge disconnected');
        }
      });

      setSocket(newSocket);

      return () => {
        newSocket.close();
      };
    } else {
      if (socket) {
        socket.close();
        setSocket(null);
        setConnected(false);
      }
    }
  }, [user, socket]);

  const joinRoom = (room: string) => {
    if (socket) {
      socket.emit('join-room', room);
    }
  };

  const leaveRoom = (room: string) => {
    if (socket) {
      socket.emit('leave-room', room);
    }
  };

  const value: SocketContextType = {
    socket,
    connected,
    joinRoom,
    leaveRoom,
  };

  return <SocketContext.Provider value={value}>{children}</SocketContext.Provider>;
};

export const useSocket = (): SocketContextType => {
  const context = useContext(SocketContext);
  if (context === undefined) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
};