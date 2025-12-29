from datetime import datetime, timedelta
import uuid
from .extensions import db

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.String(10), primary_key=True)
    alias = db.Column(db.String(50), unique=True, nullable=True)
    pin_hash = db.Column(db.String(255), nullable=True)
    code_visible = db.Column(db.Boolean, default=False)
    alias_colors = db.Column(db.Text, nullable=True)
    
    # Forge / Agent Fields
    integrity_score = db.Column(db.Integer, default=10)
    forge_history = db.Column(db.Text, default='[]') # JSON list of messages
    insights = db.Column(db.Text, default='[]') # JSON list of extracted insights
    custom_api_key = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Role & Moderation Fields (NEW)
    user_role = db.Column(db.String(20), default='user')  # admin, moderator, user
    credentials = db.Column(db.Text, default='[]')  # JSON list of earned badges/credentials
    is_reported = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

class Message(db.Model):
    __tablename__ = 'messages'
    msg_id = db.Column(db.String(36), primary_key=True)
    sender_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    chat_id = db.Column(db.String(36), nullable=False)
    content = db.Column(db.Text, nullable=False)
    msg_type = db.Column(db.String(20), default='text')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    edited_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    
    __table_args__ = (db.Index('idx_chat_created', 'chat_id', 'created_at'),)

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.String(36), primary_key=True)
    group_name = db.Column(db.String(100))
    created_by = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    is_private = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_renamed_at = db.Column(db.DateTime)
    previous_name = db.Column(db.String(100))
    renamed_by = db.Column(db.String(10))
    
    # Moderation Fields (NEW)
    moderator_ids = db.Column(db.Text, default='[]')  # JSON list of appointed moderator user_ids
    moderation_type = db.Column(db.String(20), default='human')  # human, ai, hybrid
    ai_moderator_key = db.Column(db.String(255), nullable=True)  # Optional LLM API key for AI moderation
    ai_moderator_enabled = db.Column(db.Boolean, default=False)

class GroupVote(db.Model):
    __tablename__ = 'group_votes'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.String(36), db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    vote_type = db.Column(db.String(20))  # 'revert_name'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GroupMember(db.Model):
    __tablename__ = 'group_members'
    group_id = db.Column(db.String(36), db.ForeignKey('groups.id'), primary_key=True)
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class Contact(db.Model):
    __tablename__ = 'contacts'
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), primary_key=True)
    contact_id = db.Column(db.String(10), primary_key=True)
    contact_alias = db.Column(db.String(50))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

class Quest(db.Model):
    __tablename__ = 'quests'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)  # JSON
    difficulty = db.Column(db.String(20), default='solo')  # solo, small-group, community
    created_by = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    reward = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

class BlockList(db.Model):
    __tablename__ = 'block_list'
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), primary_key=True)
    blocked_id = db.Column(db.String(10), primary_key=True)  # Blocked user's code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MuteList(db.Model):
    __tablename__ = 'mute_list'
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), primary_key=True)
    muted_id = db.Column(db.String(10), primary_key=True)  # Muted user's code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.String(36), primary_key=True)
    reporter_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    reportee_id = db.Column(db.String(10), nullable=False)  # User being reported
    report_reason = db.Column(db.Text, nullable=False)
    report_context = db.Column(db.Text, nullable=True)  # Group ID or chat context
    status = db.Column(db.String(20), default='pending')  # pending, investigating, resolved, dismissed
    assigned_moderator = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=True)
    investigation_notes = db.Column(db.Text, nullable=True)
    resolution = db.Column(db.String(20), nullable=True)  # warning, mute, ban, dismiss
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ModeratorLog(db.Model):
    __tablename__ = 'moderator_logs'
    id = db.Column(db.String(36), primary_key=True)
    moderator_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # appoint, remove, warn, mute, investigate
    target_user = db.Column(db.String(10), nullable=True)
    group_id = db.Column(db.String(36), nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON details
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Credential(db.Model):
    __tablename__ = 'credentials'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    credential_type = db.Column(db.String(50), nullable=False)  # quest-completed, peer-validated, community-vote
    credential_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    issued_by = db.Column(db.String(10), nullable=True)  # User/quest that issued it

class VoiceNote(db.Model):
    """Voice note model - Audio files in messages"""
    __tablename__ = 'voice_notes'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False, index=True)
    group_id = db.Column(db.String(36), db.ForeignKey('groups.id'), nullable=True, index=True)
    audio_data = db.Column(db.LargeBinary, nullable=False)  # WAV/MP3 blob
    duration = db.Column(db.Float, default=0.0)  # Duration in seconds
    transcription = db.Column(db.Text, nullable=True)  # Optional transcription
    file_type = db.Column(db.String(10), default='wav')  # wav, mp3, m4a
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class InviteCode(db.Model):
    """Invite code model - For user referral/invitations"""
    __tablename__ = 'invite_codes'
    code = db.Column(db.String(16), primary_key=True)  # e.g., 'ABC123DEF456'
    created_by = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False, index=True)
    uses_remaining = db.Column(db.Integer, default=10)  # Max invites per code
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    is_active = db.Column(db.Boolean, default=True)

class Referral(db.Model):
    """Referral tracking model"""
    __tablename__ = 'referrals'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False, index=True)
    referred_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    invite_code = db.Column(db.String(16), db.ForeignKey('invite_codes.code'), nullable=True)
    referred_at = db.Column(db.DateTime, default=datetime.utcnow)
