"""
SDOH Chat - Pydantic Schemas
Request/Response validation models
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class UserRegisterRequest(BaseModel):
    """Registration request - empty body, server generates code"""
    pass


class UserRegisterResponse(BaseModel):
    """Registration response"""
    user_id: str = Field(..., description="10-digit code")
    needs_alias: bool = True


class SetAliasRequest(BaseModel):
    """Set unique alias"""
    user_id: str
    alias: str = Field(..., min_length=3, max_length=50)
    
    @validator('alias')
    def alias_valid(cls, v):
        """Alias must be alphanumeric + underscore/dash"""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', v):
            raise ValueError('Alias must be 3-50 chars, alphanumeric, underscore, or dash only')
        return v


class SetPinRequest(BaseModel):
    """Set PIN"""
    user_id: str
    pin: str = Field(..., min_length=4, max_length=8)
    
    @validator('pin')
    def pin_numeric(cls, v):
        """PIN must be numeric"""
        if not v.isdigit():
            raise ValueError('PIN must be numeric')
        return v


class LoginRequest(BaseModel):
    """Login request"""
    user_id: str
    pin: str


class LoginResponse(BaseModel):
    """Login response"""
    token: str
    alias: str
    user_id: str
    expires_in: int = 86400


class MessageSendRequest(BaseModel):
    """Send message"""
    to: str  # recipient user_id or group_id
    text: str = Field(..., max_length=500)
    msg_type: str = "text"


class MessageResponse(BaseModel):
    """Message in response"""
    msg_id: str
    sender_id: str
    sender_alias: str
    chat_id: str
    content: str
    msg_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """List of messages"""
    messages: List[MessageResponse]
    has_more: bool
    total: int


class ContactAddRequest(BaseModel):
    """Add contact"""
    contact_id: str  # Their 10-digit code (they share it with you)
    contact_alias: str = Field(..., min_length=1, max_length=50)  # Your name for them


class ContactResponse(BaseModel):
    """Contact in response"""
    user_id: str
    alias: str  # Their alias
    contact_alias: str  # Your name for them
    added_at: datetime
    
    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """List of contacts"""
    contacts: List[ContactResponse]


class GroupCreateRequest(BaseModel):
    """Create group"""
    group_name: Optional[str] = None
    is_private: bool = True


class GroupResponse(BaseModel):
    """Group in response"""
    id: str
    group_name: Optional[str]
    created_by: str
    is_private: bool
    member_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class GroupDetailResponse(BaseModel):
    """Group with members"""
    id: str
    group_name: Optional[str]
    created_by: str
    is_private: bool
    members: List[dict]  # [{"user_id": "...", "alias": "..."}, ...]
    created_at: datetime


class GroupMemberAddRequest(BaseModel):
    """Add member to group"""
    user_id: str  # Their 10-digit code


class StatusUpdateRequest(BaseModel):
    """Update status"""
    status: str = Field(..., regex='^(available|busy|away|offline)$')


class StatusResponse(BaseModel):
    """Status in response"""
    user_id: str
    alias: str
    status: str
    expires_at: Optional[datetime]
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
