from flask import Blueprint, request, jsonify
from urllib.parse import quote_plus
from ..extensions import db
from ..models import User, InviteCode, Referral, Contact, Group, GroupMember
from ..auth_utils import get_current_user, require_auth
import uuid

social_bp = Blueprint('social', __name__)

# ============================================================================
# CONTACTS
# ============================================================================

@social_bp.route('/contacts', methods=['GET'])
@require_auth
def get_contacts(current_user):
    """Get list of contacts"""
    contacts = Contact.query.filter_by(user_id=current_user.user_id).all()
    
    results = []
    for c in contacts:
        # Get user details
        u = User.query.get(c.contact_id)
        if u:
            results.append({
                'user_id': u.user_id,
                'alias': c.contact_alias or u.alias,
                'is_online': False # TODO: Implement online status
            })
            
    return jsonify(results), 200

@social_bp.route('/contacts/add', methods=['POST'])
@require_auth
def add_contact(current_user):
    """Add a contact by Alias or User ID"""
    data = request.json
    target = data.get('target', '').strip()
    
    if not target:
        return jsonify({'error': 'Username or ID required'}), 400
        
    if target == current_user.user_id or target == current_user.alias:
        return jsonify({'error': 'Cannot add yourself'}), 400
        
    # Find user
    user_to_add = User.query.filter(
        (User.user_id == target) | (User.alias == target)
    ).first()
    
    if not user_to_add:
        return jsonify({'error': 'User not found'}), 404
        
    # Check if already added
    existing = Contact.query.filter_by(
        user_id=current_user.user_id, 
        contact_id=user_to_add.user_id
    ).first()
    
    if existing:
        return jsonify({'error': 'User already in contacts'}), 400
        
    # Add contact
    new_contact = Contact(
        user_id=current_user.user_id,
        contact_id=user_to_add.user_id,
        contact_alias=user_to_add.alias
    )
    db.session.add(new_contact)
    db.session.commit()
    
    return jsonify({
        'message': 'Contact added',
        'contact': {
            'user_id': user_to_add.user_id,
            'alias': user_to_add.alias
        }
    }), 201

@social_bp.route('/contacts/<contact_id>/chat', methods=['POST'])
@require_auth
def open_contact_chat(current_user, contact_id):
    """Get or create a private DM group with a contact"""
    # Check if DM group already exists
    # We need a way to identify DM groups. 
    # For now, let's search for a private group with exactly these 2 members.
    
    # This is a bit inefficient but works for MVP
    my_groups = GroupMember.query.filter_by(user_id=current_user.user_id).all()
    
    for membership in my_groups:
        group = Group.query.get(membership.group_id)
        if group.is_private and group.group_name == 'DM': 
            # Check members
            members = GroupMember.query.filter_by(group_id=group.id).all()
            member_ids = [m.user_id for m in members]
            if len(member_ids) == 2 and contact_id in member_ids:
                return jsonify({'group_id': group.id, 'name': 'Private Chat'}), 200
                
    # Create new DM group
    other_user = User.query.get(contact_id)
    if not other_user:
        return jsonify({'error': 'User not found'}), 404
        
    new_group = Group(
        id=str(uuid.uuid4()),
        group_name='DM', # Special name for DMs
        created_by=current_user.user_id,
        is_private=True
    )
    db.session.add(new_group)
    
    # Add members
    m1 = GroupMember(group_id=new_group.id, user_id=current_user.user_id)
    m2 = GroupMember(group_id=new_group.id, user_id=contact_id)
    db.session.add(m1)
    db.session.add(m2)
    
    db.session.commit()
    
    return jsonify({'group_id': new_group.id, 'name': other_user.alias}), 201

# ============================================================================
# TRADING (THE GHOST GRID)
# ============================================================================

@social_bp.route('/trade', methods=['POST'])
@require_auth
def trade_item(current_user):
    """Transfer an item from current user to another user"""
    import json
    data = request.json
    recipient_id = data.get('recipient_id')
    item_name = data.get('item_name')
    
    if not recipient_id or not item_name:
        return jsonify({'error': 'Recipient ID and Item Name required'}), 400
        
    # Find recipient
    recipient = User.query.get(recipient_id)
    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404
        
    # Get current user's inventory
    try:
        inventory = json.loads(current_user.inventory) if current_user.inventory else []
    except:
        inventory = []
        
    if item_name not in inventory:
        return jsonify({'error': f"Item '{item_name}' not in inventory"}), 400
        
    # Get recipient's inventory
    try:
        recipient_inventory = json.loads(recipient.inventory) if recipient.inventory else []
    except:
        recipient_inventory = []
        
    # Perform Transfer
    inventory.remove(item_name)
    recipient_inventory.append(item_name)
    
    # Save changes
    current_user.inventory = json.dumps(inventory)
    recipient.inventory = json.dumps(recipient_inventory)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': f"Transferred '{item_name}' to {recipient.alias}",
        'inventory': inventory
    }), 200

# ============================================================================
# INVITES
# ============================================================================

@social_bp.route('/invites/generate', methods=['POST'])
@require_auth
def generate_invite_link(current_user):
    """Generate a new invite code for the current user"""
    # Generate unique code
    import secrets
    code = secrets.token_urlsafe(9)[:12].upper()
    
    # Check for collision (unlikely but possible)
    while InviteCode.query.get(code):
        code = secrets.token_urlsafe(9)[:12].upper()
    
    invite = InviteCode(
        code=code,
        created_by=current_user.user_id,
        uses_remaining=20,  # 20 invites per code
        is_active=True
    )
    
    db.session.add(invite)
    db.session.commit()
    
    # Build shareable links
    base_url = request.host_url.rstrip('/')
    invite_url = f"{base_url}/?ref={code}"
    
    return jsonify({
        'code': code,
        'invite_url': invite_url,
        'share_links': {
            'whatsapp': f"https://wa.me/?text=Join%20SDOH%20Chat!%20{quote_plus(invite_url)}",
            'email': f"mailto:?subject=Join%20SDOH%20Chat&body={quote_plus(f'Click here to join: {invite_url}')}",
            'copy': invite_url
        }
    }), 201

@social_bp.route('/invites/my-link', methods=['GET'])
@require_auth
def get_my_invite_link(current_user):
    """Get or create the user's personal invite link"""
    # Check if user already has an active invite code
    invite = InviteCode.query.filter_by(created_by=current_user.user_id, is_active=True).first()
    
    if not invite:
        # Create one if it doesn't exist
        import secrets
        code = secrets.token_urlsafe(9)[:12].upper()
        while InviteCode.query.get(code):
            code = secrets.token_urlsafe(9)[:12].upper()
        
        invite = InviteCode(
            code=code,
            created_by=current_user.user_id,
            uses_remaining=50,  # More generous for personal link
            is_active=True
        )
        db.session.add(invite)
        db.session.commit()
    
    base_url = request.host_url.rstrip('/')
    invite_url = f"{base_url}/?ref={invite.code}"
    
    return jsonify({
        'code': invite.code,
        'invite_url': invite_url,
        'uses_remaining': invite.uses_remaining,
        'user_alias': current_user.alias,
        'share_links': {
            'whatsapp': f"https://wa.me/?text=Join%20SDOH%20Chat%20with%20me!%20{quote_plus(invite_url)}",
            'email': f"mailto:?subject=Join%20SDOH%20Chat%20-%20Invite%20from%20{quote_plus(current_user.alias)}&body={quote_plus(f'Hey! Join me on SDOH Chat - a privacy-first healthcare communication platform.\\n\\n{invite_url}')}",
            'sms': f"sms:?body={quote_plus(f'Join SDOH Chat with me! {invite_url}')}",
            'copy': invite_url
        }
    }), 200

@social_bp.route('/invites/<code>/stats', methods=['GET'])
@require_auth
def get_invite_stats(current_user, code):
    """Get stats for an invite code"""
    invite = InviteCode.query.get(code)
    if not invite or invite.created_by != current_user.user_id:
        return jsonify({'error': 'Invite not found or not yours'}), 403
    
    # Count how many people used this code
    referrals = Referral.query.filter_by(invite_code=code).count()
    
    return jsonify({
        'code': code,
        'created_at': invite.created_at.isoformat(),
        'expires_at': invite.expires_at.isoformat(),
        'uses_remaining': invite.uses_remaining,
        'uses_total': 20 - invite.uses_remaining,
        'referrals_count': referrals,
        'is_active': invite.is_active
    }), 200
