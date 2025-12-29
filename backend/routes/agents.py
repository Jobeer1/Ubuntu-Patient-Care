from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
import json
import os
from ..extensions import db
from ..models import User, Message, Quest
from ..auth_utils import get_current_user, require_auth
from agent_forge import IntegrityForge
from agent_quest import QuestMaster

agents_bp = Blueprint('agents', __name__)

# Initialize Agents
# Assuming config.ini is in the project root (two levels up from here)
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config.ini'))
forge_agent = IntegrityForge(config_path)
quest_agent = QuestMaster(config_path)

@agents_bp.route('/forge/chat', methods=['POST'])
@require_auth
def chat_with_forge(current_user):
    """Send message to The Forge Agent"""
    data = request.json
    content = data.get('content', '').strip()
    location = data.get('location')
    if not content:
        return jsonify({'error': 'Empty message'}), 400
        
    # 1. Save User Message
    chat_id = f"forge_{current_user.user_id}"
    user_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id=current_user.user_id,
        chat_id=chat_id,
        content=content
    )
    db.session.add(user_msg)
    
    # 2. Get History
    try:
        history = json.loads(current_user.forge_history)
    except:
        history = []
        
    # 3. Call Agent
    result = forge_agent.chat(
        user_input=content,
        history=history,
        current_score=current_user.integrity_score,
        user_api_key=current_user.custom_api_key,
        location=location
    )
    
    # 4. Extract response text and score adjustment
    if isinstance(result, dict):
        ai_response = result.get('response', str(result))
        score_adjustment = result.get('score_adjustment', 0)
        new_insight = result.get('new_insight')
        insight_type = result.get('insight_type', 'strength') # Default to strength
    else:
        ai_response = str(result)
        score_adjustment = 0
        new_insight = None
        insight_type = None
    
    # 5. Update User State
    # Remove 100 cap for RuneScape XP system
    current_user.integrity_score = max(0, current_user.integrity_score + score_adjustment)
    current_user.is_verified = True
    
    # Save Insight
    if new_insight:
        try:
            current_insights = json.loads(current_user.insights) if current_user.insights else []
        except:
            current_insights = []
        
        # Avoid duplicates
        insight_texts = [i.get('text') for i in current_insights if isinstance(i, dict)]
        if new_insight not in insight_texts:
            current_insights.append({
                "text": new_insight, 
                "type": insight_type,
                "xp": score_adjustment,
                "trigger_msg": content[:100] + "..." if len(content) > 100 else content,
                "date": datetime.utcnow().isoformat()
            })
            current_user.insights = json.dumps(current_insights)
        
    # Update history
    history.append({"role": "user", "content": content})
    history.append({"role": "model", "content": ai_response})
    current_user.forge_history = json.dumps(history[-20:]) # Keep last 20 turns
    
    # 5. Save Agent Response
    agent_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id='FORGE',
        chat_id=chat_id,
        content=ai_response
    )
    db.session.add(agent_msg)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'response': ai_response,
        'score': current_user.integrity_score,
        'insights': json.loads(current_user.insights) if current_user.insights else [],
        'verified': current_user.is_verified
    })

@agents_bp.route('/quest/chat', methods=['POST'])
@require_auth
def chat_with_quest(current_user):
    """Send message to The Quest-Master Agent"""
    data = request.json
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Empty message'}), 400
    
    # Get or create quest history
    chat_id = f"quest_{current_user.user_id}"
    try:
        quest_history = json.loads(current_user.forge_history) if current_user.forge_history else []
    except:
        quest_history = []
    
    # 1. Save User Message
    user_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id=current_user.user_id,
        chat_id=chat_id,
        content=content
    )
    db.session.add(user_msg)
    
    # 2. Call Quest Agent
    result = quest_agent.chat(
        user_input=content,
        history=quest_history,
        user_alias=current_user.alias,
        user_api_key=current_user.custom_api_key
    )
    
    # 3. If quest is ready, post to Quest Board
    posted_quest = None
    if result['quest_ready'] and result['quest_data']:
        quest_data = result['quest_data']
        posted_quest = Quest(
            id=str(uuid.uuid4()),
            name=quest_data.get('name', 'Untitled Quest'),
            description=quest_data.get('description', ''),
            requirements=json.dumps(quest_data.get('requirements', {})),
            difficulty=quest_data.get('difficulty', 'solo'),
            created_by=current_user.user_id,
            reward=quest_data.get('reward', '')
        )
        db.session.add(posted_quest)
    
    # 4. Update history
    quest_history.append({"role": "user", "content": content})
    quest_history.append({"role": "model", "content": result['response']})
    
    # 5. Save Agent Response
    agent_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id='QUEST',
        chat_id=chat_id,
        content=result['response']
    )
    db.session.add(agent_msg)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'response': result['response'],
        'quest_posted': result['quest_ready'],
        'quest_id': posted_quest.id if posted_quest else None
    })

@agents_bp.route('/quests', methods=['GET'])
def get_quests():
    """Get all active quests from the Quest Board"""
    try:
        quests = Quest.query.filter_by(status='active').order_by(Quest.created_at.desc()).all()
        
        quests_data = []
        for q in quests:
            creator = User.query.get(q.created_by)
            quests_data.append({
                'id': q.id,
                'name': q.name,
                'description': q.description,
                'requirements': json.loads(q.requirements) if q.requirements else {},
                'difficulty': q.difficulty,
                'created_by': creator.alias if creator else 'Unknown',
                'reward': q.reward,
                'created_at': q.created_at.isoformat()
            })
        
        return jsonify({'quests': quests_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agents_bp.route('/forge/greeting', methods=['GET'])
@require_auth
def get_forge_greeting(current_user):
    """Get personalized Forge greeting for user"""
    greeting = f"""Hello {current_user.alias}. I'm The Forge - your personal integrity coach and character auditor. I'm here to help you discover what you're truly made of. What brings you here today?

**[PRIVACY NOTICE]** Your API keys (ElevenLabs, Google Gemini, etc.) are stored ONLY in your browser's local storage. They are NEVER sent to our servers and NEVER logged. Each request is encrypted end-to-end. Your credentials are 100% under your control - we don't even have access to them. You can clear them anytime in Settings → Clear API Keys."""
    
    return jsonify({
        'greeting': greeting,
        'agent': 'The Forge',
        'role': 'Integrity Auditor - Onboarding & Personal Challenge Coach'
    })
