"""
SDOH Chat - Contacts Routes
Add, list, delete contacts
Privacy: Code not shared, only alias visible
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session

from RIS-1.SDOH-chat.backend.models import User, Contact
from RIS-1.SDOH-chat.backend.schemas import (
    ContactAddRequest, ContactResponse, ContactListResponse
)
from RIS-1.SDOH-chat.backend.utils.auth_utils import AuthUtils

router = APIRouter(prefix="/api/sdoh/contacts", tags=["contacts"])


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


@router.post("/add")
async def add_contact(
    req: ContactAddRequest,
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Add contact by their 10-digit code
    
    User must manually share code (explicit opt-in)
    Name field is YOUR alias for them
    """
    try:
        current_user = get_current_user(token, db)
        
        # Validate contact exists
        contact_user = db.query(User).filter(User.user_id == req.contact_id).first()
        if not contact_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Can't add yourself
        if req.contact_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add yourself"
            )
        
        # Check if already a contact
        existing = db.query(Contact).filter(
            Contact.user_id == current_user.user_id,
            Contact.contact_id == req.contact_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already in contacts"
            )
        
        # Add contact
        contact = Contact(
            user_id=current_user.user_id,
            contact_id=req.contact_id,
            contact_alias=req.contact_alias  # User's name for them
        )
        db.add(contact)
        db.commit()
        
        return {
            "status": "added",
            "contact_alias": req.contact_alias,
            "contact_user_alias": contact_user.alias  # Their actual alias
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/", response_model=ContactListResponse)
async def get_contacts(
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Get user's contact list
    
    Privacy: Shows aliases only (codes hidden)
    """
    try:
        current_user = get_current_user(token, db)
        
        contacts = db.query(Contact).filter(
            Contact.user_id == current_user.user_id
        ).all()
        
        contact_list = []
        for contact in contacts:
            contact_user = db.query(User).filter(User.user_id == contact.contact_id).first()
            if contact_user:
                contact_list.append(ContactResponse(
                    user_id=contact.contact_id,
                    alias=contact_user.alias,  # Their actual alias
                    contact_alias=contact.contact_alias,  # Your name for them
                    added_at=contact.added_at
                ))
        
        return ContactListResponse(contacts=contact_list)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{contact_id}")
async def remove_contact(
    contact_id: str,
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Remove contact
    """
    try:
        current_user = get_current_user(token, db)
        
        contact = db.query(Contact).filter(
            Contact.user_id == current_user.user_id,
            Contact.contact_id == contact_id
        ).first()
        
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )
        
        db.delete(contact)
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


@router.put("/{contact_id}")
async def update_contact_alias(
    contact_id: str,
    new_alias: str = Query(..., min_length=1, max_length=50),
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Update your alias for a contact
    """
    try:
        current_user = get_current_user(token, db)
        
        contact = db.query(Contact).filter(
            Contact.user_id == current_user.user_id,
            Contact.contact_id == contact_id
        ).first()
        
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )
        
        contact.contact_alias = new_alias
        db.commit()
        
        return {
            "status": "updated",
            "contact_alias": new_alias
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/search")
async def search_users(
    alias: str = Query(..., min_length=1, max_length=50),
    token: str = Query(...),
    db: Session = Depends()
):
    """
    Search for users by alias
    
    Returns list of users matching alias (not codes)
    """
    try:
        current_user = get_current_user(token, db)
        
        # Search for users with matching alias
        results = db.query(User).filter(
            User.alias.ilike(f"%{alias}%"),
            User.user_id != current_user.user_id  # Exclude self
        ).limit(10).all()
        
        return {
            "results": [
                {
                    "user_id": user.user_id if user.code_visible else None,
                    "alias": user.alias,
                    "code_visible": user.code_visible
                }
                for user in results
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
