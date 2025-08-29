import React, { useState, useEffect, useRef } from 'react';
import { 
  Users, 
  MessageCircle, 
  Video, 
  Mic, 
  MicOff, 
  VideoOff,
  Share2,
  Pencil,
  Ruler,
  MousePointer,
  Crown,
  Send,
  Settings,
  Eye,
  EyeOff,
  Volume2,
  VolumeX
} from 'lucide-react';
import io from 'socket.io-client';

const RealtimeCollaboration = ({ studyId, currentUser, onAnnotationAdd, onMeasurementAdd }) => {
  const [socket, setSocket] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [annotations, setAnnotations] = useState([]);
  const [measurements, setMeasurements] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showParticipants, setShowParticipants] = useState(true);
  const [chatMessage, setChatMessage] = useState('');
  const [cursorPositions, setCursorPositions] = useState({});
  const [isPresenter, setIsPresenter] = useState(false);
  const [followPresenter, setFollowPresenter] = useState(true);
  const [collaborationMode, setCollaborationMode] = useState('view'); // 'view', 'annotate', 'measure'
  
  const chatContainerRef = useRef(null);
  const mousePositionRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    initializeSocket();
    return () => {
      if (socket) {
        socket.disconnect();
      }
    };
  }, []);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatMessages]);

  const initializeSocket = () => {
    const newSocket = io('/collaboration', {
      transports: ['websocket']
    });

    newSocket.on('connect', () => {
      setIsConnected(true);
      console.log('Connected to collaboration server');
    });

    newSocket.on('disconnect', () => {
      setIsConnected(false);
      console.log('Disconnected from collaboration server');
    });

    newSocket.on('session_data', (data) => {
      setParticipants(data.session.participants || []);
      setChatMessages(data.chat_messages || []);
      setAnnotations(data.annotations || []);
      setMeasurements(data.measurements || []);
      
      // Check if current user is presenter
      const currentParticipant = data.session.participants?.find(p => p.user_id === currentUser.id);
      setIsPresenter(currentParticipant?.is_presenter || false);
    });

    newSocket.on('cursor_update', (data) => {
      setCursorPositions(prev => ({
        ...prev,
        [data.user_id]: data.cursor_data
      }));
    });

    newSocket.on('viewport_update', (data) => {
      if (followPresenter && data.user_id !== currentUser.id) {
        // Update viewport to follow presenter
        handleViewportUpdate(data.viewport_data);
      }
    });

    newSocket.on('annotation_update', (data) => {
      setAnnotations(prev => [...prev, data.annotation]);
      if (onAnnotationAdd) {
        onAnnotationAdd(data.annotation);
      }
    });

    newSocket.on('measurement_update', (data) => {
      setMeasurements(prev => [...prev, data.measurement]);
      if (onMeasurementAdd) {
        onMeasurementAdd(data.measurement);
      }
    });

    newSocket.on('chat_update', (data) => {
      setChatMessages(prev => [...prev, {
        message_id: data.message_id,
        user_id: data.user_id,
        username: data.username,
        message: data.message,
        timestamp: new Date().toISOString()
      }]);
    });

    newSocket.on('user_joined', (data) => {
      setParticipants(prev => [...prev, data.user]);
      addSystemMessage(`${data.user.username} joined the session`);
    });

    newSocket.on('user_left', (data) => {
      setParticipants(prev => prev.filter(p => p.user_id !== data.user_id));
      addSystemMessage(`User left the session`);
    });

    setSocket(newSocket);
  };

  const createSession = async () => {
    try {
      const response = await fetch('/api/collaboration/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          study_id: studyId,
          created_by: currentUser.id,
          title: `Collaborative Review - ${studyId}`,
          description: 'Multi-user DICOM viewing session'
        })
      });

      const data = await response.json();
      if (data.success) {
        setSessionId(data.session_id);
        joinSession(data.session_id);
      }
    } catch (error) {
      console.error('Error creating session:', error);
    }
  };

  const joinSession = async (sessionId) => {
    try {
      const response = await fetch(`/api/collaboration/sessions/${sessionId}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: currentUser.id,
          username: currentUser.username,
          role: currentUser.role,
          hospital_id: currentUser.hospital_id
        })
      });

      const data = await response.json();
      if (data.success) {
        setSessionId(sessionId);
        
        // Join socket room
        socket.emit('join_collaboration_session', {
          session_id: sessionId,
          user_id: currentUser.id
        });
      }
    } catch (error) {
      console.error('Error joining session:', error);
    }
  };

  const leaveSession = () => {
    if (socket && sessionId) {
      socket.emit('leave_collaboration_session', {
        session_id: sessionId,
        user_id: currentUser.id
      });
    }
    setSessionId(null);
    setParticipants([]);
    setChatMessages([]);
    setAnnotations([]);
    setMeasurements([]);
  };

  const sendChatMessage = () => {
    if (!chatMessage.trim() || !socket || !sessionId) return;

    const messageData = {
      session_id: sessionId,
      user_id: currentUser.id,
      username: currentUser.username,
      message: chatMessage
    };

    socket.emit('chat_message', messageData);
    
    // Add to local chat immediately
    setChatMessages(prev => [...prev, {
      message_id: Date.now().toString(),
      user_id: currentUser.id,
      username: currentUser.username,
      message: chatMessage,
      timestamp: new Date().toISOString()
    }]);

    setChatMessage('');
  };

  const handleMouseMove = (event) => {
    if (!socket || !sessionId) return;

    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;

    mousePositionRef.current = { x, y };

    // Throttle cursor updates
    if (Date.now() - (mousePositionRef.current.lastUpdate || 0) > 50) {
      socket.emit('cursor_move', {
        session_id: sessionId,
        user_id: currentUser.id,
        cursor_data: { x, y, timestamp: Date.now() }
      });
      mousePositionRef.current.lastUpdate = Date.now();
    }
  };

  const handleViewportChange = (viewportData) => {
    if (!socket || !sessionId || !isPresenter) return;

    socket.emit('viewport_change', {
      session_id: sessionId,
      user_id: currentUser.id,
      viewport_data: viewportData
    });
  };

  const handleViewportUpdate = (viewportData) => {
    // Implementation would update the DICOM viewer viewport
    console.log('Updating viewport:', viewportData);
  };

  const addSystemMessage = (message) => {
    setChatMessages(prev => [...prev, {
      message_id: Date.now().toString(),
      user_id: 'system',
      username: 'System',
      message: message,
      timestamp: new Date().toISOString(),
      is_system: true
    }]);
  };

  const changePresenter = async (userId) => {
    try {
      const response = await fetch(`/api/collaboration/sessions/${sessionId}/presenter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });

      if (response.ok) {
        setParticipants(prev => prev.map(p => ({
          ...p,
          is_presenter: p.user_id === userId
        })));
        setIsPresenter(userId === currentUser.id);
      }
    } catch (error) {
      console.error('Error changing presenter:', error);
    }
  };

  const ParticipantsList = () => (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900 flex items-center">
          <Users className="h-5 w-5 mr-2" />
          Participants ({participants.length})
        </h3>
        <button
          onClick={() => setShowParticipants(!showParticipants)}
          className="text-gray-400 hover:text-gray-600"
        >
          {showParticipants ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>

      {showParticipants && (
        <div className="space-y-3">
          {participants.map(participant => (
            <div key={participant.user_id} className="flex items-center justify-between">
              <div className="flex items-center">
                <div 
                  className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium"
                  style={{ backgroundColor: participant.avatar_color }}
                >
                  {participant.username.charAt(0).toUpperCase()}
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-900 flex items-center">
                    {participant.username}
                    {participant.is_presenter && (
                      <Crown className="h-4 w-4 ml-1 text-yellow-500" />
                    )}
                  </p>
                  <p className="text-xs text-gray-500">{participant.role}</p>
                </div>
              </div>
              
              {currentUser.role === 'admin' && !participant.is_presenter && (
                <button
                  onClick={() => changePresenter(participant.user_id)}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  Make Presenter
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const ChatPanel = () => (
    <div className="bg-white rounded-lg shadow-sm border flex flex-col h-96">
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="text-lg font-medium text-gray-900 flex items-center">
          <MessageCircle className="h-5 w-5 mr-2" />
          Chat
        </h3>
        <button
          onClick={() => setShowChat(!showChat)}
          className="text-gray-400 hover:text-gray-600"
        >
          {showChat ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>

      {showChat && (
        <>
          <div 
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto p-4 space-y-3"
          >
            {chatMessages.map(message => (
              <div key={message.message_id} className={`flex ${
                message.user_id === currentUser.id ? 'justify-end' : 'justify-start'
              }`}>
                <div className={`max-w-xs lg:max-w-md px-3 py-2 rounded-lg ${
                  message.is_system 
                    ? 'bg-gray-100 text-gray-600 text-center text-sm'
                    : message.user_id === currentUser.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-900'
                }`}>
                  {!message.is_system && message.user_id !== currentUser.id && (
                    <p className="text-xs font-medium mb-1">{message.username}</p>
                  )}
                  <p className="text-sm">{message.message}</p>
                  <p className="text-xs opacity-75 mt-1">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 border-t">
            <div className="flex space-x-2">
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
                placeholder="Type a message..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={sendChatMessage}
                disabled={!chatMessage.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );

  const CollaborationToolbar = () => (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {isPresenter && (
            <div className="flex items-center space-x-2 text-yellow-600">
              <Crown className="h-4 w-4" />
              <span className="text-sm font-medium">Presenter</span>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setFollowPresenter(!followPresenter)}
            className={`px-3 py-1 text-sm rounded-md ${
              followPresenter 
                ? 'bg-blue-100 text-blue-700' 
                : 'bg-gray-100 text-gray-700'
            }`}
          >
            {followPresenter ? 'Following Presenter' : 'Free Navigation'}
          </button>

          <select
            value={collaborationMode}
            onChange={(e) => setCollaborationMode(e.target.value)}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md"
          >
            <option value="view">View Only</option>
            <option value="annotate">Annotate</option>
            <option value="measure">Measure</option>
          </select>

          {sessionId ? (
            <button
              onClick={leaveSession}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
            >
              Leave Session
            </button>
          ) : (
            <button
              onClick={createSession}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Start Collaboration
            </button>
          )}
        </div>
      </div>
    </div>
  );

  const CursorOverlay = () => (
    <div className="absolute inset-0 pointer-events-none">
      {Object.entries(cursorPositions).map(([userId, position]) => {
        const participant = participants.find(p => p.user_id === userId);
        if (!participant || userId === currentUser.id) return null;

        return (
          <div
            key={userId}
            className="absolute transform -translate-x-1/2 -translate-y-1/2 pointer-events-none"
            style={{
              left: `${position.x}%`,
              top: `${position.y}%`,
              color: participant.avatar_color
            }}
          >
            <MousePointer className="h-4 w-4" />
            <span className="text-xs bg-black text-white px-1 py-0.5 rounded ml-2">
              {participant.username}
            </span>
          </div>
        );
      })}
    </div>
  );

  return (
    <div className="space-y-4">
      <CollaborationToolbar />
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <div 
            className="relative bg-gray-100 rounded-lg h-96"
            onMouseMove={handleMouseMove}
          >
            {/* DICOM Viewer would go here */}
            <div className="absolute inset-0 flex items-center justify-center text-gray-500">
              DICOM Viewer with Collaboration Features
            </div>
            
            {sessionId && <CursorOverlay />}
          </div>
        </div>
        
        <div className="space-y-4">
          <ParticipantsList />
          {sessionId && <ChatPanel />}
        </div>
      </div>

      {/* Annotations and Measurements Summary */}
      {sessionId && (annotations.length > 0 || measurements.length > 0) && (
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Session Activity</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">
                Annotations ({annotations.length})
              </h4>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {annotations.slice(-5).map(annotation => (
                  <div key={annotation.annotation_id} className="text-sm text-gray-600">
                    <span className="font-medium">{annotation.username}:</span> {annotation.text || annotation.type}
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">
                Measurements ({measurements.length})
              </h4>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {measurements.slice(-5).map(measurement => (
                  <div key={measurement.measurement_id} className="text-sm text-gray-600">
                    <span className="font-medium">{measurement.username}:</span> {measurement.label} ({measurement.value} {measurement.unit})
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RealtimeCollaboration;