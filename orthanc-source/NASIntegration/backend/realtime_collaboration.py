#!/usr/bin/env python3
"""
Real-time Collaboration System for Multi-User DICOM Viewing
Enables multiple users to view and annotate images simultaneously
"""

import sqlite3
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import asyncio
import websockets
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue

class CollaborationEventType(Enum):
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    ANNOTATION_ADDED = "annotation_added"
    ANNOTATION_UPDATED = "annotation_updated"
    ANNOTATION_DELETED = "annotation_deleted"
    VIEWPORT_CHANGED = "viewport_changed"
    MEASUREMENT_ADDED = "measurement_added"
    CURSOR_MOVED = "cursor_moved"
    CHAT_MESSAGE = "chat_message"
    STUDY_CHANGED = "study_changed"
    WINDOW_LEVEL_CHANGED = "window_level_changed"

@dataclass
class CollaborationUser:
    user_id: str
    username: str
    role: str
    hospital_id: str
    avatar_color: str
    is_presenter: bool = False
    last_activity: datetime = None

@dataclass
class CollaborationSession:
    session_id: str
    study_id: str
    created_by: str
    created_at: datetime
    title: str
    description: str
    max_participants: int = 10
    is_active: bool = True
    participants: List[CollaborationUser] = None

@dataclass
class CollaborationEvent:
    event_id: str
    session_id: str
    user_id: str
    event_type: CollaborationEventType
    data: Dict
    timestamp: datetime

class RealtimeCollaborationManager:
    """Manages real-time collaboration sessions for DICOM viewing"""
    
    def __init__(self, db_path: str = "collaboration.db"):
        self.db_path = db_path
        self.active_sessions: Dict[str, CollaborationSession] = {}
        self.websocket_connections: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.event_queue = queue.Queue()
        self.init_database()
        
    def init_database(self):
        """Initialize the collaboration database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Collaboration sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collaboration_sessions (
                session_id TEXT PRIMARY KEY,
                study_id TEXT NOT NULL,
                created_by TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                max_participants INTEGER DEFAULT 10,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP
            )
        ''')
        
        # Session participants
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_participants (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                hospital_id TEXT,
                avatar_color TEXT,
                is_presenter BOOLEAN DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                left_at TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES collaboration_sessions (session_id)
            )
        ''')
        
        # Real-time annotations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collaboration_annotations (
                annotation_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                study_id TEXT NOT NULL,
                series_id TEXT,
                instance_id TEXT,
                annotation_type TEXT NOT NULL, -- 'arrow', 'text', 'circle', 'rectangle', 'freehand'
                coordinates TEXT NOT NULL, -- JSON array of coordinates
                text_content TEXT,
                style_properties TEXT, -- JSON of color, thickness, etc.
                is_temporary BOOLEAN DEFAULT 0, -- for cursor trails, etc.
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES collaboration_sessions (session_id)
            )
        ''')
        
        # Collaboration events log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collaboration_events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT, -- JSON
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES collaboration_sessions (session_id)
            )
        ''')
        
        # Shared measurements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collaboration_measurements (
                measurement_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                study_id TEXT NOT NULL,
                measurement_type TEXT NOT NULL, -- 'distance', 'angle', 'area', 'volume'
                coordinates TEXT NOT NULL, -- JSON array of measurement points
                value REAL,
                unit TEXT,
                label TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES collaboration_sessions (session_id)
            )
        ''')
        
        # Chat messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collaboration_chat (
                message_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                message_type TEXT DEFAULT 'text', -- 'text', 'system', 'annotation_reference'
                reference_id TEXT, -- for annotation references
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES collaboration_sessions (session_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def create_collaboration_session(self, study_id: str, created_by: str, 
                                   title: str, description: str = None,
                                   max_participants: int = 10) -> str:
        """Create a new collaboration session"""
        session_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO collaboration_sessions (
                session_id, study_id, created_by, title, description, max_participants
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, study_id, created_by, title, description, max_participants))
        
        conn.commit()
        conn.close()
        
        # Initialize session in memory
        session = CollaborationSession(
            session_id=session_id,
            study_id=study_id,
            created_by=created_by,
            created_at=datetime.now(),
            title=title,
            description=description,
            max_participants=max_participants,
            participants=[]
        )
        
        self.active_sessions[session_id] = session
        self.websocket_connections[session_id] = set()
        
        return session_id
        
    def join_session(self, session_id: str, user_id: str, username: str, 
                    role: str, hospital_id: str = None) -> bool:
        """Add a user to a collaboration session"""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        
        # Check if session is full
        if len(session.participants) >= session.max_participants:
            return False
            
        # Generate avatar color
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8']
        avatar_color = colors[len(session.participants) % len(colors)]
        
        # Create user object
        user = CollaborationUser(
            user_id=user_id,
            username=username,
            role=role,
            hospital_id=hospital_id,
            avatar_color=avatar_color,
            is_presenter=(len(session.participants) == 0),  # First user is presenter
            last_activity=datetime.now()
        )
        
        session.participants.append(user)
        self.user_sessions[user_id] = session_id
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO session_participants (
                id, session_id, user_id, username, role, hospital_id, 
                avatar_color, is_presenter
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), session_id, user_id, username, role,
            hospital_id, avatar_color, user.is_presenter
        ))
        
        conn.commit()
        conn.close()
        
        # Broadcast user joined event
        self._broadcast_event(session_id, CollaborationEvent(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            event_type=CollaborationEventType.USER_JOINED,
            data={
                'user': asdict(user),
                'participant_count': len(session.participants)
            },
            timestamp=datetime.now()
        ))
        
        return True
        
    def leave_session(self, session_id: str, user_id: str):
        """Remove a user from a collaboration session"""
        if session_id not in self.active_sessions:
            return
            
        session = self.active_sessions[session_id]
        
        # Remove user from participants
        session.participants = [p for p in session.participants if p.user_id != user_id]
        
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            
        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE session_participants 
            SET left_at = CURRENT_TIMESTAMP 
            WHERE session_id = ? AND user_id = ?
        ''', (session_id, user_id))
        
        conn.commit()
        conn.close()
        
        # Broadcast user left event
        self._broadcast_event(session_id, CollaborationEvent(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            event_type=CollaborationEventType.USER_LEFT,
            data={
                'user_id': user_id,
                'participant_count': len(session.participants)
            },
            timestamp=datetime.now()
        ))
        
        # End session if no participants left
        if len(session.participants) == 0:
            self._end_session(session_id)
            
    def add_annotation(self, session_id: str, user_id: str, annotation_data: Dict) -> str:
        """Add a real-time annotation"""
        annotation_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO collaboration_annotations (
                annotation_id, session_id, user_id, study_id, series_id,
                instance_id, annotation_type, coordinates, text_content,
                style_properties, is_temporary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            annotation_id, session_id, user_id,
            annotation_data.get('study_id'),
            annotation_data.get('series_id'),
            annotation_data.get('instance_id'),
            annotation_data.get('type'),
            json.dumps(annotation_data.get('coordinates')),
            annotation_data.get('text'),
            json.dumps(annotation_data.get('style', {})),
            annotation_data.get('is_temporary', False)
        ))
        
        conn.commit()
        conn.close()
        
        # Broadcast annotation event
        self._broadcast_event(session_id, CollaborationEvent(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            event_type=CollaborationEventType.ANNOTATION_ADDED,
            data={
                'annotation_id': annotation_id,
                'annotation': annotation_data
            },
            timestamp=datetime.now()
        ))
        
        return annotation_id
        
    def add_measurement(self, session_id: str, user_id: str, measurement_data: Dict) -> str:
        """Add a shared measurement"""
        measurement_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO collaboration_measurements (
                measurement_id, session_id, user_id, study_id,
                measurement_type, coordinates, value, unit, label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            measurement_id, session_id, user_id,
            measurement_data.get('study_id'),
            measurement_data.get('type'),
            json.dumps(measurement_data.get('coordinates')),
            measurement_data.get('value'),
            measurement_data.get('unit'),
            measurement_data.get('label')
        ))
        
        conn.commit()
        conn.close()
        
        # Broadcast measurement event
        self._broadcast_event(session_id, CollaborationEvent(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            event_type=CollaborationEventType.MEASUREMENT_ADDED,
            data={
                'measurement_id': measurement_id,
                'measurement': measurement_data
            },
            timestamp=datetime.now()
        ))
        
        return measurement_id
        
    def send_chat_message(self, session_id: str, user_id: str, username: str, 
                         message: str, message_type: str = 'text',
                         reference_id: str = None) -> str:
        """Send a chat message in the collaboration session"""
        message_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO collaboration_chat (
                message_id, session_id, user_id, username, message,
                message_type, reference_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (message_id, session_id, user_id, username, message, message_type, reference_id))
        
        conn.commit()
        conn.close()
        
        # Broadcast chat message
        self._broadcast_event(session_id, CollaborationEvent(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            event_type=CollaborationEventType.CHAT_MESSAGE,
            data={
                'message_id': message_id,
                'username': username,
                'message': message,
                'message_type': message_type,
                'reference_id': reference_id
            },
            timestamp=datetime.now()
        ))
        
        return message_id
        
    def update_viewport(self, session_id: str, user_id: str, viewport_data: Dict):
        """Update user's viewport (for presenter mode)"""
        if session_id not in self.active_sessions:
            return
            
        session = self.active_sessions[session_id]
        user = next((p for p in session.participants if p.user_id == user_id), None)
        
        if user and user.is_presenter:
            # Broadcast viewport change to all participants
            self._broadcast_event(session_id, CollaborationEvent(
                event_id=str(uuid.uuid4()),
                session_id=session_id,
                user_id=user_id,
                event_type=CollaborationEventType.VIEWPORT_CHANGED,
                data=viewport_data,
                timestamp=datetime.now()
            ))
            
    def update_cursor_position(self, session_id: str, user_id: str, cursor_data: Dict):
        """Update user's cursor position for real-time tracking"""
        self._broadcast_event(session_id, CollaborationEvent(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            event_type=CollaborationEventType.CURSOR_MOVED,
            data=cursor_data,
            timestamp=datetime.now()
        ), exclude_user=user_id)
        
    def get_session_data(self, session_id: str) -> Dict:
        """Get complete session data including participants and annotations"""
        if session_id not in self.active_sessions:
            return None
            
        session = self.active_sessions[session_id]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get annotations
        cursor.execute('''
            SELECT * FROM collaboration_annotations 
            WHERE session_id = ? AND is_temporary = 0
            ORDER BY created_at
        ''', (session_id,))
        
        annotations = []
        for row in cursor.fetchall():
            annotations.append({
                'annotation_id': row[0],
                'user_id': row[2],
                'study_id': row[3],
                'series_id': row[4],
                'instance_id': row[5],
                'type': row[6],
                'coordinates': json.loads(row[7]),
                'text': row[8],
                'style': json.loads(row[9]) if row[9] else {},
                'created_at': row[11]
            })
            
        # Get measurements
        cursor.execute('''
            SELECT * FROM collaboration_measurements 
            WHERE session_id = ?
            ORDER BY created_at
        ''', (session_id,))
        
        measurements = []
        for row in cursor.fetchall():
            measurements.append({
                'measurement_id': row[0],
                'user_id': row[2],
                'study_id': row[3],
                'type': row[4],
                'coordinates': json.loads(row[5]),
                'value': row[6],
                'unit': row[7],
                'label': row[8],
                'created_at': row[9]
            })
            
        # Get recent chat messages
        cursor.execute('''
            SELECT * FROM collaboration_chat 
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 50
        ''', (session_id,))
        
        chat_messages = []
        for row in cursor.fetchall():
            chat_messages.append({
                'message_id': row[0],
                'user_id': row[2],
                'username': row[3],
                'message': row[4],
                'message_type': row[5],
                'reference_id': row[6],
                'timestamp': row[7]
            })
            
        conn.close()
        
        return {
            'session': asdict(session),
            'annotations': annotations,
            'measurements': measurements,
            'chat_messages': list(reversed(chat_messages))
        }
        
    def _broadcast_event(self, session_id: str, event: CollaborationEvent, exclude_user: str = None):
        """Broadcast an event to all participants in a session"""
        if session_id not in self.websocket_connections:
            return
            
        # Save event to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO collaboration_events (
                event_id, session_id, user_id, event_type, event_data
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            event.event_id, event.session_id, event.user_id,
            event.event_type.value, json.dumps(event.data)
        ))
        
        conn.commit()
        conn.close()
        
        # Broadcast to WebSocket connections
        event_data = {
            'event_id': event.event_id,
            'session_id': event.session_id,
            'user_id': event.user_id,
            'event_type': event.event_type.value,
            'data': event.data,
            'timestamp': event.timestamp.isoformat()
        }
        
        # Add to event queue for WebSocket broadcasting
        self.event_queue.put((session_id, event_data, exclude_user))
        
    def _end_session(self, session_id: str):
        """End a collaboration session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            
        if session_id in self.websocket_connections:
            del self.websocket_connections[session_id]
            
        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE collaboration_sessions 
            SET is_active = 0, ended_at = CURRENT_TIMESTAMP 
            WHERE session_id = ?
        ''', (session_id,))
        
        conn.commit()
        conn.close()

# WebSocket handler for real-time communication
async def websocket_handler(websocket, path, collaboration_manager):
    """Handle WebSocket connections for real-time collaboration"""
    session_id = None
    user_id = None
    
    try:
        async for message in websocket:
            data = json.loads(message)
            
            if data['type'] == 'join_session':
                session_id = data['session_id']
                user_id = data['user_id']
                
                if session_id in collaboration_manager.websocket_connections:
                    collaboration_manager.websocket_connections[session_id].add(websocket)
                    
                    # Send current session data
                    session_data = collaboration_manager.get_session_data(session_id)
                    if session_data:
                        await websocket.send(json.dumps({
                            'type': 'session_data',
                            'data': session_data
                        }))
                        
            elif data['type'] == 'cursor_move':
                collaboration_manager.update_cursor_position(
                    data['session_id'], data['user_id'], data['cursor_data']
                )
                
            elif data['type'] == 'viewport_change':
                collaboration_manager.update_viewport(
                    data['session_id'], data['user_id'], data['viewport_data']
                )
                
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Clean up connection
        if session_id and session_id in collaboration_manager.websocket_connections:
            collaboration_manager.websocket_connections[session_id].discard(websocket)
            
        if session_id and user_id:
            collaboration_manager.leave_session(session_id, user_id)

if __name__ == "__main__":
    # Example usage
    collaboration = RealtimeCollaborationManager()
    
    # Create a session
    session_id = collaboration.create_collaboration_session(
        study_id="study_123",
        created_by="dr_smith",
        title="Cardiac CT Review",
        description="Multi-disciplinary review of cardiac CT scan"
    )
    
    print(f"Created collaboration session: {session_id}")
    
    # Join session
    collaboration.join_session(
        session_id, "dr_jones", "Dr. Jones", "cardiologist", "hospital_1"
    )
    
    # Add annotation
    annotation_data = {
        'study_id': 'study_123',
        'type': 'arrow',
        'coordinates': [100, 150, 200, 250],
        'text': 'Possible stenosis here'
    }
    
    collaboration.add_annotation(session_id, "dr_jones", annotation_data)