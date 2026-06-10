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
    quest_history = db.Column(db.Text, default='[]') # JSON list of messages
    insights = db.Column(db.Text, default='[]') # JSON list of extracted insights
    custom_api_key = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Role & Moderation Fields (NEW)
    user_role = db.Column(db.String(20), default='user')  # admin, moderator, user
    credentials = db.Column(db.Text, default='[]')  # JSON list of earned badges/credentials
    is_reported = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    
    # Quest Fields
    inventory = db.Column(db.Text, default='[]') # JSON list of items
    active_quest_id = db.Column(db.String(200), nullable=True)
    quest_progress = db.Column(db.Text, default='{}') # JSON dict of quest progress
    
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
    start_location = db.Column(db.String(200), nullable=True)
    end_goal = db.Column(db.Text, nullable=True)
    requirements = db.Column(db.Text, nullable=True)  # JSON
    difficulty = db.Column(db.String(20), default='solo')  # solo, small-group, community
    created_by = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    reward = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

class NPC(db.Model):
    __tablename__ = 'npcs'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    quest_id = db.Column(db.String(200), nullable=True) # Changed from 36 to 200 to support quest names
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100))
    skills = db.Column(db.Text)  # JSON list or description
    personality = db.Column(db.Text)
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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


class PaymentAllocation(db.Model):
    __tablename__ = 'payment_allocations'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=True, index=True)
    patient_alias = db.Column(db.String(50), nullable=True)
    account_number = db.Column(db.String(80), nullable=True, index=True)
    invoice_number = db.Column(db.String(80), nullable=True, index=True)
    payment_reference = db.Column(db.String(120), nullable=True, index=True)
    amount = db.Column(db.String(32), nullable=True)
    currency = db.Column(db.String(10), default='ZAR')
    status = db.Column(db.String(20), default='draft')  # draft, verified, allocated, rejected
    source_channel = db.Column(db.String(40), default='sdoh_chat')
    verification_required = db.Column(db.Boolean, default=True)
    verification_verified = db.Column(db.Boolean, default=False)
    allocated_account = db.Column(db.String(80), nullable=True)
    allocation_notes = db.Column(db.Text, nullable=True)
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

class QuestStory(db.Model):
    """Publicly shared quest stories for reading and listening"""
    __tablename__ = 'quest_stories'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    user_alias = db.Column(db.String(50))
    quest_name = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False) # The full narrative summary/log
    voice_note_url = db.Column(db.String(255), nullable=True) # Optional URL to MP3 voice note
    message_id = db.Column(db.String(36), db.ForeignKey('messages.msg_id'), nullable=True) # Link to the message that created this fragment
    is_public = db.Column(db.Boolean, default=True)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

class QuestSnapshot(db.Model):
    """Snapshot of game state every 10 turns for Stage Mechanics"""
    __tablename__ = 'quest_snapshots'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False, index=True)
    turn_number = db.Column(db.Integer, nullable=False)
    snapshot_data = db.Column(db.Text, nullable=False)  # JSON blob of state
    summary = db.Column(db.Text, nullable=True)  # AI generated 10-turn summary
    tags = db.Column(db.Text, nullable=True)  # JSON list of keywords/entities for indexing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PacsAuditLog(db.Model):
    """Append-only audit log for PACS mentor requests and responses"""
    __tablename__ = 'pacs_audit_logs'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=True, index=True)
    user_alias = db.Column(db.String(50), nullable=True)
    chat_id = db.Column(db.String(36), nullable=True, index=True)
    route = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(120), nullable=False)
    request_text = db.Column(db.Text, nullable=True)
    response_text = db.Column(db.Text, nullable=True)
    model_provider = db.Column(db.String(40), nullable=True)
    model_name = db.Column(db.String(80), nullable=True)
    client_ip = db.Column(db.String(45), nullable=True)
    client_machine = db.Column(db.String(255), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
