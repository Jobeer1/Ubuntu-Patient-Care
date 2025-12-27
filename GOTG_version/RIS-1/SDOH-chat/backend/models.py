"""
SDOH Chat - Database Models
SQLAlchemy models for users, messages, groups, contacts
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Table, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

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
    
    # Relationships
    messages = relationship('Message', back_populates='sender', foreign_keys='Message.sender_id')
    groups = relationship('Group', secondary=group_members, back_populates='members')
    contacts = relationship('Contact', back_populates='user', foreign_keys='Contact.user_id')
    
    def __repr__(self):
        return f'<User {self.alias}>'


class Message(Base):
    """Message model - Minimal payload, linked to sender"""
    __tablename__ = 'messages'
    
    msg_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String(10), ForeignKey('users.user_id'), nullable=False, index=True)
    chat_id = Column(String(36), nullable=False, index=True)  # user_id or group_id
    content = Column(Text, nullable=False)  # Max 500 chars
    msg_type = Column(String(20), default='text')  # text, status, notice, voice
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    edited_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    
    # Relationships
    sender = relationship('User', back_populates='messages', foreign_keys=[sender_id])
    
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
