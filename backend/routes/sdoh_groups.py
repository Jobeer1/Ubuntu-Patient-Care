"""
SDOH Chat - Groups Routes
Create, list, manage groups
Privacy: Codes hidden, only aliases visible in groups
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from RIS-1.SDOH-chat.backend.models import User, Group, Message
from RIS-1.SDOH-chat.backend.schemas import (
    GroupCreateRequest, GroupResponse, GroupDetailResponse, GroupMemberAddRequest
)
from RIS-1.SDOH-chat.backend.utils.auth_utils import AuthUtils

router = APIRouter(prefix="/api/sdoh/groups", tags=["groups"])


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


@router.post("/create")
async def create_group(
    req: GroupCreateRequest,
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Create new group chat
    
    Privacy: Private by default (invite-only)
    Creator is automatically added
    """
    try:
        current_user = get_current_user(token, db)
        
        # Create group
        group = Group(
            group_name=req.group_name,
            created_by=current_user.user_id,
            is_private=req.is_private
        )
        db.add(group)
        db.flush()
        
        # Add creator as member
        group.members.append(current_user)
        db.commit()
        
        return GroupResponse(
            id=group.id,
            group_name=group.group_name,
            created_by=group.created_by,
            is_private=group.is_private,
            member_count=1,
            created_at=group.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/")
async def list_groups(
    token: str = Query(...),
    db: Session = Depends()
):
    """
    List all groups user is a member of
    """
    try:
        current_user = get_current_user(token, db)
        
        groups = current_user.groups
        
        group_list = []
        for group in groups:
            # Get unread message count
            unread = db.query(Message).filter(
                Message.chat_id == group.id,
                Message.sender_id != current_user.user_id
            ).count()
            
            group_list.append({
                "id": group.id,
                "group_name": group.group_name,
                "created_by": group.created_by,
                "is_private": group.is_private,
                "member_count": len(group.members),
                "unread": unread,
                "created_at": group.created_at
            })
        
        return {"groups": group_list}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{group_id}")
async def get_group_detail(
    group_id: str,
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Get group details and members
    
    Privacy: Members shown with aliases only
    """
    try:
        current_user = get_current_user(token, db)
        
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        # Check if user is member
        if current_user not in group.members:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this group"
            )
        
        members = [
            {"user_id": member.user_id if member.code_visible else None, "alias": member.alias}
            for member in group.members
        ]
        
        return GroupDetailResponse(
            id=group.id,
            group_name=group.group_name,
            created_by=group.created_by,
            is_private=group.is_private,
            members=members,
            created_at=group.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{group_id}/add-member")
async def add_member_to_group(
    group_id: str,
    req: GroupMemberAddRequest,
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Add member to group
    
    Only group creator can add members (or implement role-based later)
    """
    try:
        current_user = get_current_user(token, db)
        
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        # Only creator can add members
        if group.created_by != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group creator can add members"
            )
        
        # Check member limit
        if len(group.members) >= group.member_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group is at member limit ({group.member_limit})"
            )
        
        # Get user to add
        user_to_add = db.query(User).filter(User.user_id == req.user_id).first()
        if not user_to_add:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if already member
        if user_to_add in group.members:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already a member"
            )
        
        group.members.append(user_to_add)
        db.commit()
        
        return {
            "status": "added",
            "user_alias": user_to_add.alias,
            "member_count": len(group.members)
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{group_id}/remove-member/{member_id}")
async def remove_member_from_group(
    group_id: str,
    member_id: str,
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Remove member from group
    
    Creator can remove anyone, member can remove themselves
    """
    try:
        current_user = get_current_user(token, db)
        
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        # Check permission
        can_remove = (
            group.created_by == current_user.user_id or
            member_id == current_user.user_id
        )
        
        if not can_remove:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot remove this member"
            )
        
        user_to_remove = db.query(User).filter(User.user_id == member_id).first()
        if not user_to_remove:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user_to_remove not in group.members:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a member"
            )
        
        group.members.remove(user_to_remove)
        db.commit()
        
        return {"status": "removed"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Delete group (only creator)
    """
    try:
        current_user = get_current_user(token, db)
        
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        if group.created_by != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only creator can delete group"
            )
        
        # Delete all messages in group
        db.query(Message).filter(Message.chat_id == group_id).delete()
        db.delete(group)
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
