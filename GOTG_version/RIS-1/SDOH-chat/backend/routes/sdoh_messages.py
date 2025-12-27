"""
SDOH Chat - Messages Routes
Send, receive, list, delete messages
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime

from RIS-1.SDOH-chat.backend.models import Message, User
from RIS-1.SDOH-chat.backend.schemas import (
    MessageSendRequest, MessageResponse, MessageListResponse
)
from RIS-1.SDOH-chat.backend.utils.auth_utils import AuthUtils, PrivacyUtils

router = APIRouter(prefix="/api/sdoh/messages", tags=["messages"])


def get_current_user(token: str, db: Session = Depends()) -> User:
    """Dependency to get current user from token"""
    payload = AuthUtils.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    user = db.query(User).filter(User.user_id == payload['user_id']).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/send")
async def send_message(
    req: MessageSendRequest,
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Send message to user or group
    
    Privacy: Message shows sender's alias, not code
    """
    try:
        current_user = get_current_user(token, db)
        
        # Validate recipient exists
        recipient = db.query(User).filter(User.user_id == req.to).first()
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient not found"
            )
        
        # Create message
        message = Message(
            sender_id=current_user.user_id,
            chat_id=req.to,  # Direct message to user_id or group_id
            content=req.text,
            msg_type=req.msg_type
        )
        db.add(message)
        db.commit()
        
        return {
            "msg_id": message.msg_id,
            "status": "sent",
            "created_at": message.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{chat_id}", response_model=MessageListResponse)
async def get_messages(
    chat_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Get message history for chat (user_id or group_id)
    
    Privacy: Messages show sender alias, code hidden
    Pagination: Load 50 messages at a time for low bandwidth
    """
    try:
        current_user = get_current_user(token, db)
        
        # Query messages
        total = db.query(Message).filter(
            Message.chat_id == chat_id,
            Message.deleted_at == None
        ).count()
        
        messages = db.query(Message).filter(
            Message.chat_id == chat_id,
            Message.deleted_at == None
        ).order_by(desc(Message.created_at)).offset(offset).limit(limit).all()
        
        # Format responses (hide codes)
        message_list = []
        for msg in reversed(messages):  # Reverse to show chronological order
            message_list.append(MessageResponse(
                msg_id=msg.msg_id,
                sender_id=None,  # Hidden
                sender_alias=msg.sender.alias,  # Visible
                chat_id=msg.chat_id,
                content=msg.content,
                msg_type=msg.msg_type,
                created_at=msg.created_at
            ))
        
        return MessageListResponse(
            messages=message_list,
            has_more=(offset + limit) < total,
            total=total
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{msg_id}")
async def delete_message(
    msg_id: str,
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Soft delete message (only sender can delete)
    """
    try:
        current_user = get_current_user(token, db)
        
        message = db.query(Message).filter(Message.msg_id == msg_id).first()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Only sender can delete
        if message.sender_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete other user's message"
            )
        
        message.deleted_at = datetime.utcnow()
        db.commit()
        
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{msg_id}")
async def edit_message(
    msg_id: str,
    new_text: str = Query(..., max_length=500),
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Edit message (only sender can edit, within 5 minutes)
    """
    try:
        current_user = get_current_user(token, db)
        
        message = db.query(Message).filter(Message.msg_id == msg_id).first()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Only sender can edit
        if message.sender_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot edit other user's message"
            )
        
        # Check if edit is within 5 minutes
        from datetime import timedelta
        if (datetime.utcnow() - message.created_at) > timedelta(minutes=5):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only edit messages within 5 minutes"
            )
        
        message.content = new_text
        message.edited_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "edited",
            "msg_id": msg_id,
            "edited_at": message.edited_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
