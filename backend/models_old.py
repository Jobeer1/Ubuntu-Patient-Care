"""
SDOH Chat - Database Models
SQLAlchemy models for users, messages, groups, contacts, voice notes, invites
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Table, Index, LargeBinary, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
import secrets

Base = declarative_base()

# Association table for group members (many-to-many)
group_members = Table(
    'group_members',
    Base.metadata,
    Column('group_id', String(36), ForeignKey('groups.id'), primary_key=True),
    Column('user_id', String(10), ForeignKey('users.user_id'), primary_key=True),
    Column('joined_at', DateTime, default=datetime.utcnow)
)


class User(Base):
    """User model - Privacy first (code hidden, alias visible)"""
    __tablename__ = 'users'
    
    user_id = Column(String(10), primary_key=True)  # 10-digit code (HIDDEN by default)
    alias = Column(String(50), unique=True, nullable=False, index=True)  # Display name (VISIBLE)
    pin_hash = Column(String(255), nullable=False)  # bcrypt hash
    sso_id = Column(String(255), unique=True, nullable=True)  # MCP OAuth link
    code_visible = Column(Boolean, default=False)  # User controls code visibility
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_login = Column(DateTime, nullable=True)
    device_fingerprint = Column(String(255), nullable=True)
    referred_by = Column(String(10), ForeignKey('users.user_id'), nullable=True)  # Referral tracking
    
    # Relationships
    messages = relationship('Message', back_populates='sender', foreign_keys='Message.sender_id')
    groups = relationship('Group', secondary=group_members, back_populates='members')
    contacts = relationship('Contact', back_populates='user', foreign_keys='Contact.user_id')
    voice_notes = relationship('VoiceNote', back_populates='sender', foreign_keys='VoiceNote.sender_id')
    
    def __repr__(self):
        return f'<User {self.alias}>'


class Message(Base):
    """Message model - Minimal payload, linked to sender"""
    __tablename__ = 'messages'
    
    msg_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String(10), ForeignKey('users.user_id'), nullable=False, index=True)
    chat_id = Column(String(36), nullable=False, index=True)  # user_id or group_id
    content = Column(Text, nullable=False)  # Max 500 chars
    msg_type = Column(String(20), default='text')  # text, status, notice, voice, voice_note
    voice_note_id = Column(String(36), ForeignKey('voice_notes.id'), nullable=True)  # Link to voice note if type='voice_note'
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    edited_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    
    # Relationships
    sender = relationship('User', back_populates='messages', foreign_keys=[sender_id])
    voice_note = relationship('VoiceNote', back_populates='message')
    
    # Composite index for chat history queries
    __table_args__ = (
        Index('ix_messages_chat_ts', 'chat_id', 'created_at'),
    )
    
    def __repr__(self):
        return f'<Message {self.msg_id}>'


class Group(Base):
    """Group chat model"""
    __tablename__ = 'groups'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_name = Column(String(100), nullable=True)
    created_by = Column(String(10), ForeignKey('users.user_id'), nullable=False)
    is_private = Column(Boolean, default=True)  # Private by default
    member_limit = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    description = Column(Text, nullable=True)  # Optional group description
    
    # Relationships
    members = relationship('User', secondary=group_members, back_populates='groups')
    
    def __repr__(self):
        return f'<Group {self.group_name or self.id}>'


class Contact(Base):
    """Contact model - User's saved contacts (for quick access)"""
    __tablename__ = 'contacts'
    
    user_id = Column(String(10), ForeignKey('users.user_id'), primary_key=True)
    contact_id = Column(String(10), ForeignKey('users.user_id'), primary_key=True)  # Other user's code
    contact_alias = Column(String(50), nullable=False)  # Their alias (user-set display name)
    added_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship('User', back_populates='contacts', foreign_keys=[user_id])


class VoiceNote(Base):
    """Voice note model - Audio files in messages"""
    __tablename__ = 'voice_notes'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String(10), ForeignKey('users.user_id'), nullable=False, index=True)
    group_id = Column(String(36), ForeignKey('groups.id'), nullable=True, index=True)  # Group where shared
    audio_data = Column(LargeBinary, nullable=False)  # WAV/MP3 blob
    duration = Column(Float, default=0.0)  # Duration in seconds
    transcription = Column(Text, nullable=True)  # Optional transcription (via Whisper)
    file_type = Column(String(10), default='wav')  # wav, mp3, m4a, etc
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    sender = relationship('User', back_populates='voice_notes', foreign_keys=[sender_id])
    message = relationship('Message', back_populates='voice_note', uselist=False)
    
    def __repr__(self):
        return f'<VoiceNote {self.id}>'


class InviteCode(Base):
    """Invite code model - For user referral"""
    __tablename__ = 'invite_codes'
    
    code = Column(String(16), primary_key=True)  # Random alphanumeric: e.g., 'ABC123DEF456'
    created_by = Column(String(10), ForeignKey('users.user_id'), nullable=False, index=True)
    uses_remaining = Column(Integer, default=10)  # Max invites per code
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))  # 30 day expiry
    is_active = Column(Boolean, default=True)
    
    # Relationships
    creator = relationship('User')
    
    @staticmethod
    def generate_code():
        """Generate a unique 12-char invite code"""
        return secrets.token_urlsafe(9)[:12].upper()
    
    def __repr__(self):
        return f'<InviteCode {self.code}>'


class Referral(Base):
    """Referral tracking model"""
    __tablename__ = 'referrals'
    
    referrer_id = Column(String(10), ForeignKey('users.user_id'), primary_key=True)
    referred_id = Column(String(10), ForeignKey('users.user_id'), primary_key=True)
    invite_code = Column(String(16), ForeignKey('invite_codes.code'), nullable=True)
    referred_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    referrer = relationship('User', foreign_keys=[referrer_id])
    referred_user = relationship('User', foreign_keys=[referred_id])
    
    __table_args__ = (
        Index('ix_referrals_referrer', 'referrer_id'),
    )
    
    def __repr__(self):
        return f'<Referral {self.referrer_id} → {self.referred_id}>'
    
    def __repr__(self):
        return f'<Contact {self.contact_alias}>'


class Status(Base):
    """User status updates (presence)"""
    __tablename__ = 'statuses'
    
    user_id = Column(String(10), ForeignKey('users.user_id'), primary_key=True)
    status = Column(String(20), default='available')  # available, busy, away, offline
    expires_at = Column(DateTime, nullable=True)  # Auto-clear after 8 hours
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Status {self.user_id}: {self.status}>'
