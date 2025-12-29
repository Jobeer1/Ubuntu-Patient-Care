from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
import uuid
import json
import io
from ..extensions import db
from ..models import User, Message, Group, GroupMember, GroupVote, VoiceNote
from ..auth_utils import get_current_user, require_auth

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    """Get user info and groups for dashboard"""
    # ensure_db_initialized() handled by app
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    user = User.query.get(user_id)
    
    # Get public groups
    public_groups = Group.query.filter_by(is_private=False).all()
    
    groups_data = []
    for g in public_groups:
        # Count active users in this group
        member_count = GroupMember.query.filter_by(group_id=g.id).count()
        
        groups_data.append({
            'id': g.id,
            'name': g.group_name,
            'is_private': g.is_private,
            'is_online': True,  # Public rooms are always "online" for now
            'member_count': member_count,
            'max_members': 20,  # 20 user limit per room
            'last_renamed_at': g.last_renamed_at.isoformat() if g.last_renamed_at else None
        })
    
    # Ensure Personal Forge chat exists
    forge_chat_id = f"forge_{user_id}"
    
    return jsonify({
        'user': {
            'user_id': user.user_id,
            'alias': user.alias,
            'alias_colors': json.loads(user.alias_colors) if user.alias_colors else {},
            'integrity_score': user.integrity_score,
            'insights': json.loads(user.insights) if user.insights else [],
            'is_verified': user.is_verified,
            'custom_api_key': user.custom_api_key
        },
        'groups': groups_data,
        'forge_chat_id': forge_chat_id
    })

@chat_bp.route('/groups/<group_id>/join', methods=['POST'])
@require_auth
def join_group(current_user, group_id):
    """Join a group (with 20-user limit)"""
    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    # Check if user is already a member
    existing = GroupMember.query.filter_by(group_id=group_id, user_id=current_user.user_id).first()
    if existing:
        return jsonify({'status': 'already_member'})
    
    # Check room capacity (20 user limit)
    member_count = GroupMember.query.filter_by(group_id=group_id).count()
    if member_count >= 20:
        return jsonify({'error': 'Room is full (20 user limit)'}), 400
    
    # Add user to group
    member = GroupMember(group_id=group_id, user_id=current_user.user_id)
    db.session.add(member)
    db.session.commit()
    
    return jsonify({'status': 'joined', 'member_count': member_count + 1})

@chat_bp.route('/messages/send', methods=['POST'])
@require_auth
def send_message(current_user):
    """Send a message"""
    data = request.json
    to = data.get('to', '')  # recipient user_id or group_id
    text = data.get('text', '').strip()
    
    if not text or len(text) > 500:
        return jsonify({'error': 'Message must be 1-500 characters'}), 400
    
    msg_id = str(uuid.uuid4())
    msg = Message(msg_id=msg_id, sender_id=current_user.user_id, chat_id=to, content=text, msg_type='text')
    db.session.add(msg)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'msg_id': msg_id,
        'sender_alias': current_user.alias,
        'content': text,
        'created_at': msg.created_at.isoformat()
    }), 201

@chat_bp.route('/messages/delete', methods=['POST'])
@require_auth
def delete_message(current_user):
    """Delete a message (Sender OR if it's a Forge/Quest message in user's private chat)"""
    data = request.json
    msg_id = data.get('msg_id')
    
    msg = Message.query.get(msg_id)
    if not msg:
        return jsonify({'error': 'Message not found'}), 404
        
    # Allow deletion if:
    # 1. User is the sender
    # 2. Message is from Forge/Quest AND it is in the user's private chat
    
    is_sender = (msg.sender_id == current_user.user_id)
    
    # Check if it's a private agent chat belonging to this user
    is_my_agent_chat = False
    if msg.chat_id and (f"forge_{current_user.user_id}" in msg.chat_id or f"quest_{current_user.user_id}" in msg.chat_id):
        is_my_agent_chat = True
        
    if not (is_sender or is_my_agent_chat):
        return jsonify({'error': 'Unauthorized'}), 403
        
    db.session.delete(msg)
    db.session.commit()
    
    return jsonify({'status': 'deleted'})

@chat_bp.route('/messages/clear_history', methods=['POST'])
@require_auth
def clear_history(current_user):
    """Clear chat history for a specific chat"""
    data = request.json
    chat_id = data.get('chat_id')
    
    if not chat_id:
        return jsonify({'error': 'Chat ID required'}), 400
        
    # Only allow clearing if user is part of the chat (simple check for now)
    # For Forge/Quest chats, chat_id contains user_id
    if 'forge' in chat_id or 'quest' in chat_id:
        if str(current_user.user_id) not in chat_id:
             return jsonify({'error': 'Unauthorized'}), 403
    
    # Delete all messages in this chat
    Message.query.filter_by(chat_id=chat_id).delete()
    db.session.commit()
    
    return jsonify({'status': 'cleared'})

@chat_bp.route('/messages/<chat_id>', methods=['GET'])
@require_auth
def get_messages(current_user, chat_id):
    """Get messages from a chat"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    messages = Message.query.filter_by(chat_id=chat_id).filter(Message.deleted_at.is_(None)).order_by(Message.created_at.desc()).limit(limit).offset(offset).all()
    
    result = []
    for msg in reversed(messages):
        sender = User.query.get(msg.sender_id)
        result.append({
            'msg_id': msg.msg_id,
            'sender_alias': sender.alias if sender else 'Unknown',
            'content': msg.content,
            'created_at': msg.created_at.isoformat()
        })
    
    return jsonify(result), 200

@chat_bp.route('/groups/<group_id>/rename', methods=['POST'])
@require_auth
def rename_group(current_user, group_id):
    """Rename a group with cooldown"""
    data = request.json
    new_name = data.get('name', '').strip()
    
    if not new_name or len(new_name) < 3:
        return jsonify({'error': 'Name too short'}), 400
        
    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
        
    # Check cooldown (1 hour)
    if group.last_renamed_at:
        diff = datetime.utcnow() - group.last_renamed_at
        if diff.total_seconds() < 3600:
            minutes_left = int((3600 - diff.total_seconds()) / 60)
            return jsonify({'error': f'Please wait {minutes_left} minutes before renaming again'}), 429
            
    # Save previous state
    group.previous_name = group.group_name
    group.group_name = new_name
    group.last_renamed_at = datetime.utcnow()
    group.renamed_by = current_user.user_id
    
    # Clear old votes
    GroupVote.query.filter_by(group_id=group_id, vote_type='revert_name').delete()
    
    db.session.commit()
    return jsonify({'status': 'success', 'name': new_name})

@chat_bp.route('/groups/<group_id>/vote-revert', methods=['POST'])
@require_auth
def vote_revert_group(current_user, group_id):
    """Vote to revert group name"""
    group = Group.query.get(group_id)
    if not group or not group.previous_name:
        return jsonify({'error': 'Nothing to revert'}), 400
        
    # Check if already voted
    existing = GroupVote.query.filter_by(
        group_id=group_id, user_id=current_user.user_id, vote_type='revert_name'
    ).first()
    
    if existing:
        return jsonify({'error': 'Already voted'}), 400
        
    vote = GroupVote(group_id=group_id, user_id=current_user.user_id, vote_type='revert_name')
    db.session.add(vote)
    db.session.commit()
    
    # Check if we should revert (simple logic: 3 votes reverts it for now)
    count = GroupVote.query.filter_by(group_id=group_id, vote_type='revert_name').count()
    
    if count >= 3:  # Threshold
        group.group_name = group.previous_name
        group.previous_name = None
        group.last_renamed_at = None # Reset cooldown
        GroupVote.query.filter_by(group_id=group_id, vote_type='revert_name').delete()
        db.session.commit()
        return jsonify({'status': 'reverted', 'name': group.group_name})
        
    return jsonify({'status': 'voted', 'votes': count})

@chat_bp.route('/user/settings', methods=['POST'])
@require_auth
def update_settings(current_user):
    """Update user settings (alias colors, api key)"""
    data = request.json
    
    if 'alias_colors' in data:
        current_user.alias_colors = json.dumps(data['alias_colors'])
        
    if 'custom_api_key' in data:
        current_user.custom_api_key = data['custom_api_key'].strip() if data['custom_api_key'] else None
        
    db.session.commit()
    return jsonify({'status': 'success'})

# Voice Notes
@chat_bp.route('/voice-notes/upload', methods=['POST'])
@require_auth
def upload_voice_note(current_user):
    """Upload a voice note/recording"""
    # Get audio data from request
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    group_id = request.form.get('group_id')  # Optional: which group to share to
    duration = request.form.get('duration', '0')  # Duration in seconds
    
    try:
        duration = float(duration)
    except:
        duration = 0.0
    
    # Read audio blob
    audio_data = audio_file.read()
    if len(audio_data) == 0:
        return jsonify({'error': 'Empty audio file'}), 400
    
    # Create voice note record
    note_id = str(uuid.uuid4())
    file_ext = audio_file.filename.split('.')[-1] if audio_file.filename else 'wav'
    
    voice_note = VoiceNote(
        id=note_id,
        sender_id=current_user.user_id,
        group_id=group_id,
        audio_data=audio_data,
        duration=duration,
        file_type=file_ext.lower()
    )
    
    db.session.add(voice_note)
    
    # If group specified, create a message linking to the voice note
    if group_id:
        msg = Message(
            msg_id=str(uuid.uuid4()),
            sender_id=current_user.user_id,
            chat_id=group_id,
            content=f'🎙️ Voice note ({duration:.1f}s)',
            msg_type='voice_note'
        )
        db.session.add(msg)
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'note_id': note_id,
        'url': f'/api/voice-notes/{note_id}',
        'duration': duration
    }), 201

@chat_bp.route('/voice-notes/<note_id>', methods=['GET'])
@require_auth
def get_voice_note(current_user, note_id):
    """Retrieve a voice note audio blob"""
    note = VoiceNote.query.get(note_id)
    if not note:
        return jsonify({'error': 'Voice note not found'}), 404
    
    # Return audio blob
    return send_file(
        io.BytesIO(note.audio_data),
        mimetype=f'audio/{note.file_type}'
    )

@chat_bp.route('/voice-notes/chat/<chat_id>', methods=['GET'])
@require_auth
def list_voice_notes(current_user, chat_id):
    """List all voice notes in a chat/group"""
    # Get messages of type 'voice_note'
    messages = Message.query.filter(
        Message.chat_id == chat_id,
        Message.msg_type == 'voice_note',
        Message.deleted_at.is_(None)
    ).order_by(Message.created_at.desc()).limit(50).all()
    
    notes_list = []
    for msg in messages:
        sender = User.query.get(msg.sender_id)
        notes_list.append({
            'msg_id': msg.msg_id,
            'sender_alias': sender.alias if sender else 'Unknown',
            'sender_id': msg.sender_id,
            'duration': msg.voice_note.duration if msg.voice_note else 0,
            'created_at': msg.created_at.isoformat(),
            'url': f'/api/voice-notes/{msg.voice_note.id}' if msg.voice_note else None
        })
    
    return jsonify({'notes': notes_list}), 200
