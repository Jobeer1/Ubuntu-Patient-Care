#!/usr/bin/env python3
"""
WebSocket Service for Real-time Features
Handles real-time voice transcription, report collaboration, and status updates
"""

import json
import logging
from datetime import datetime
from flask import request, session
from flask_socketio import emit, join_room, leave_room, disconnect
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class WebSocketService:
    """Manages WebSocket connections and real-time features"""
    
    def __init__(self, app, socketio):
        self.app = app
        self.socketio = socketio
        self.active_sessions = {}  # session_id -> user_info
        self.voice_sessions = {}   # voice_session_id -> session_info
        self.report_rooms = {}     # report_id -> list of connected users
        
        # Register WebSocket event handlers
        self._register_handlers()
        
    def _register_handlers(self):
        """Register all WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            try:
                # Get user info from session or request
                user_id = session.get('user_id', 'anonymous')
                user_role = session.get('user_role', 'doctor')
                
                # Store session info
                self.active_sessions[request.sid] = {
                    'user_id': user_id,
                    'user_role': user_role,
                    'connected_at': datetime.utcnow(),
                    'current_report': None,
                    'voice_session': None
                }
                
                logger.info(f"User {user_id} connected with session {request.sid}")
                
                # Send connection confirmation
                emit('connection_confirmed', {
                    'session_id': request.sid,
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'features': ['voice_transcription', 'real_time_collaboration', 'sync_status']
                })
                
            except Exception as e:
                logger.error(f"Connection error: {e}")
                emit('error', {'message': 'Connection failed'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            try:
                session_info = self.active_sessions.get(request.sid)
                if session_info:
                    user_id = session_info['user_id']
                    
                    # Clean up voice session if active
                    if session_info.get('voice_session'):
                        self._cleanup_voice_session(session_info['voice_session'])
                    
                    # Leave report room if in one
                    if session_info.get('current_report'):
                        self._leave_report_room(session_info['current_report'], request.sid)
                    
                    # Remove from active sessions
                    del self.active_sessions[request.sid]
                    
                    logger.info(f"User {user_id} disconnected from session {request.sid}")
                
            except Exception as e:
                logger.error(f"Disconnection error: {e}")
        
        @self.socketio.on('join_report')
        def handle_join_report(data):
            """Handle joining a report room for collaboration"""
            try:
                report_id = data.get('report_id')
                if not report_id:
                    emit('error', {'message': 'Report ID required'})
                    return
                
                session_info = self.active_sessions.get(request.sid)
                if not session_info:
                    emit('error', {'message': 'Invalid session'})
                    return
                
                # Join the report room
                join_room(f"report_{report_id}")
                session_info['current_report'] = report_id
                
                # Track users in report room
                if report_id not in self.report_rooms:
                    self.report_rooms[report_id] = []
                self.report_rooms[report_id].append(request.sid)
                
                # Notify other users in the room
                emit('user_joined_report', {
                    'user_id': session_info['user_id'],
                    'user_role': session_info['user_role'],
                    'report_id': report_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f"report_{report_id}", include_self=False)
                
                # Send current report status to new user
                emit('report_status', {
                    'report_id': report_id,
                    'active_users': len(self.report_rooms[report_id]),
                    'status': 'joined'
                })
                
                logger.info(f"User {session_info['user_id']} joined report {report_id}")
                
            except Exception as e:
                logger.error(f"Join report error: {e}")
                emit('error', {'message': 'Failed to join report'})
        
        @self.socketio.on('leave_report')
        def handle_leave_report(data):
            """Handle leaving a report room"""
            try:
                report_id = data.get('report_id')
                session_info = self.active_sessions.get(request.sid)
                
                if session_info and report_id:
                    self._leave_report_room(report_id, request.sid)
                    
            except Exception as e:
                logger.error(f"Leave report error: {e}")
        
        @self.socketio.on('start_voice_session')
        def handle_start_voice_session(data):
            """Handle starting a voice dictation session"""
            try:
                report_id = data.get('report_id')
                session_info = self.active_sessions.get(request.sid)
                
                if not session_info:
                    emit('error', {'message': 'Invalid session'})
                    return
                
                # Create voice session
                voice_session_id = f"voice_{request.sid}_{datetime.utcnow().timestamp()}"
                voice_session = {
                    'id': voice_session_id,
                    'user_id': session_info['user_id'],
                    'report_id': report_id,
                    'session_id': request.sid,
                    'started_at': datetime.utcnow(),
                    'is_active': True,
                    'audio_chunks': [],
                    'transcription_buffer': ''
                }
                
                self.voice_sessions[voice_session_id] = voice_session
                session_info['voice_session'] = voice_session_id
                
                # Notify report room about voice session start
                if report_id:
                    emit('voice_session_started', {
                        'voice_session_id': voice_session_id,
                        'user_id': session_info['user_id'],
                        'report_id': report_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=f"report_{report_id}")
                
                emit('voice_session_ready', {
                    'voice_session_id': voice_session_id,
                    'status': 'ready'
                })
                
                logger.info(f"Voice session {voice_session_id} started for user {session_info['user_id']}")
                
            except Exception as e:
                logger.error(f"Start voice session error: {e}")
                emit('error', {'message': 'Failed to start voice session'})
        
        @self.socketio.on('voice_audio_chunk')
        def handle_voice_audio_chunk(data):
            """Handle incoming audio chunks for transcription"""
            try:
                voice_session_id = data.get('voice_session_id')
                audio_data = data.get('audio_data')
                chunk_index = data.get('chunk_index', 0)
                
                voice_session = self.voice_sessions.get(voice_session_id)
                if not voice_session or not voice_session['is_active']:
                    emit('error', {'message': 'Invalid or inactive voice session'})
                    return
                
                # Store audio chunk
                voice_session['audio_chunks'].append({
                    'index': chunk_index,
                    'data': audio_data,
                    'timestamp': datetime.utcnow()
                })
                
                # Process audio for transcription (placeholder - will integrate with STT service)
                transcription_text = self._process_audio_chunk(audio_data, voice_session)
                
                if transcription_text:
                    # Send real-time transcription update
                    emit('transcription_update', {
                        'voice_session_id': voice_session_id,
                        'text': transcription_text,
                        'chunk_index': chunk_index,
                        'is_final': False,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
                    # Update report room with transcription
                    if voice_session['report_id']:
                        emit('report_transcription_update', {
                            'report_id': voice_session['report_id'],
                            'user_id': voice_session['user_id'],
                            'text': transcription_text,
                            'timestamp': datetime.utcnow().isoformat()
                        }, room=f"report_{voice_session['report_id']}", include_self=False)
                
            except Exception as e:
                logger.error(f"Voice audio chunk error: {e}")
                emit('error', {'message': 'Failed to process audio chunk'})
        
        @self.socketio.on('end_voice_session')
        def handle_end_voice_session(data):
            """Handle ending a voice dictation session"""
            try:
                voice_session_id = data.get('voice_session_id')
                voice_session = self.voice_sessions.get(voice_session_id)
                
                if voice_session:
                    voice_session['is_active'] = False
                    voice_session['ended_at'] = datetime.utcnow()
                    
                    # Process final transcription
                    final_transcription = self._finalize_transcription(voice_session)
                    
                    # Send final transcription
                    emit('voice_session_complete', {
                        'voice_session_id': voice_session_id,
                        'final_transcription': final_transcription,
                        'duration': (voice_session['ended_at'] - voice_session['started_at']).total_seconds(),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
                    # Notify report room
                    if voice_session['report_id']:
                        emit('voice_session_ended', {
                            'voice_session_id': voice_session_id,
                            'user_id': voice_session['user_id'],
                            'report_id': voice_session['report_id'],
                            'final_transcription': final_transcription,
                            'timestamp': datetime.utcnow().isoformat()
                        }, room=f"report_{voice_session['report_id']}")
                    
                    # Clean up session
                    session_info = self.active_sessions.get(request.sid)
                    if session_info:
                        session_info['voice_session'] = None
                    
                    logger.info(f"Voice session {voice_session_id} ended")
                
            except Exception as e:
                logger.error(f"End voice session error: {e}")
                emit('error', {'message': 'Failed to end voice session'})
        
        @self.socketio.on('sync_status_request')
        def handle_sync_status_request():
            """Handle request for sync status"""
            try:
                # Get offline sync status (placeholder - will integrate with offline manager)
                sync_status = self._get_sync_status()
                
                emit('sync_status_update', sync_status)
                
            except Exception as e:
                logger.error(f"Sync status request error: {e}")
                emit('error', {'message': 'Failed to get sync status'})
        
        @self.socketio.on('report_update')
        def handle_report_update(data):
            """Handle real-time report updates"""
            try:
                report_id = data.get('report_id')
                update_type = data.get('type')  # 'content', 'status', 'template'
                update_data = data.get('data')
                
                session_info = self.active_sessions.get(request.sid)
                if not session_info:
                    emit('error', {'message': 'Invalid session'})
                    return
                
                # Broadcast update to report room
                emit('report_updated', {
                    'report_id': report_id,
                    'type': update_type,
                    'data': update_data,
                    'user_id': session_info['user_id'],
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f"report_{report_id}", include_self=False)
                
                logger.info(f"Report {report_id} updated by {session_info['user_id']}: {update_type}")
                
            except Exception as e:
                logger.error(f"Report update error: {e}")
                emit('error', {'message': 'Failed to update report'})
    
    def _leave_report_room(self, report_id: str, session_id: str):
        """Helper to leave a report room"""
        try:
            leave_room(f"report_{report_id}")
            
            # Remove from report room tracking
            if report_id in self.report_rooms:
                if session_id in self.report_rooms[report_id]:
                    self.report_rooms[report_id].remove(session_id)
                
                # Clean up empty rooms
                if not self.report_rooms[report_id]:
                    del self.report_rooms[report_id]
            
            # Update session info
            session_info = self.active_sessions.get(session_id)
            if session_info:
                session_info['current_report'] = None
                
                # Notify other users
                emit('user_left_report', {
                    'user_id': session_info['user_id'],
                    'report_id': report_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f"report_{report_id}")
            
        except Exception as e:
            logger.error(f"Leave report room error: {e}")
    
    def _cleanup_voice_session(self, voice_session_id: str):
        """Helper to clean up voice session"""
        try:
            if voice_session_id in self.voice_sessions:
                voice_session = self.voice_sessions[voice_session_id]
                voice_session['is_active'] = False
                
                # Could save audio data here for later processing
                logger.info(f"Cleaned up voice session {voice_session_id}")
                
        except Exception as e:
            logger.error(f"Voice session cleanup error: {e}")
    
    def _process_audio_chunk(self, audio_data: str, voice_session: dict) -> Optional[str]:
        """Process audio chunk for real-time transcription"""
        try:
            # Placeholder for STT integration
            # In production, this would call the offline STT service
            
            # For now, return a mock transcription
            chunk_count = len(voice_session['audio_chunks'])
            if chunk_count % 5 == 0:  # Every 5th chunk
                return f"Transcribed text chunk {chunk_count}..."
            
            return None
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            return None
    
    def _finalize_transcription(self, voice_session: dict) -> str:
        """Finalize transcription for completed voice session"""
        try:
            # Placeholder for final transcription processing
            # In production, this would process all audio chunks together
            
            chunk_count = len(voice_session['audio_chunks'])
            duration = (voice_session['ended_at'] - voice_session['started_at']).total_seconds()
            
            return f"Final transcription of {chunk_count} audio chunks over {duration:.1f} seconds."
            
        except Exception as e:
            logger.error(f"Transcription finalization error: {e}")
            return "Transcription processing failed."
    
    def _get_sync_status(self) -> dict:
        """Get current synchronization status"""
        try:
            # Placeholder for offline manager integration
            return {
                'online': True,
                'last_sync': datetime.utcnow().isoformat(),
                'pending_uploads': 0,
                'pending_downloads': 0,
                'sync_errors': [],
                'cache_size': '125 MB'
            }
            
        except Exception as e:
            logger.error(f"Sync status error: {e}")
            return {
                'online': False,
                'error': 'Failed to get sync status'
            }
    
    def broadcast_system_message(self, message: str, message_type: str = 'info'):
        """Broadcast system message to all connected users"""
        try:
            self.socketio.emit('system_message', {
                'message': message,
                'type': message_type,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Broadcasted system message: {message}")
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
    
    def notify_report_status_change(self, report_id: str, status: str, user_id: str):
        """Notify users about report status changes"""
        try:
            self.socketio.emit('report_status_changed', {
                'report_id': report_id,
                'status': status,
                'changed_by': user_id,
                'timestamp': datetime.utcnow().isoformat()
            }, room=f"report_{report_id}")
            
            logger.info(f"Report {report_id} status changed to {status} by {user_id}")
            
        except Exception as e:
            logger.error(f"Report status notification error: {e}")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active WebSocket sessions"""
        return len(self.active_sessions)
    
    def get_active_voice_sessions_count(self) -> int:
        """Get count of active voice sessions"""
        return len([vs for vs in self.voice_sessions.values() if vs['is_active']])