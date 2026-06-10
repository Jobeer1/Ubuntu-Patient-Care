from flask import Blueprint, request, jsonify
from datetime import datetime
from sqlalchemy import or_
import uuid
import json
import os
import re
import time
from ..extensions import db
from ..models import User, Message, Quest, NPC, QuestStory, QuestSnapshot, PaymentAllocation
from ..auth_utils import get_current_user, require_auth
from backend.agent_pacs import _extract_whatsapp_sender_number, _normalize_sa_whatsapp_number, PACS_MENTOR_ADMIN_NUMBERS, PACS_MENTOR_OWNER_NUMBERS
from agent_forge import IntegrityForge
from agent_quest import FantasyQuestMaster
from agent_sdoh import SDOHContinuityAgent

agents_bp = Blueprint('agents', __name__)

# Initialize Agents
# Assuming config.ini is in the project root (two levels up from here)
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config.ini'))
forge_agent = IntegrityForge(config_path)
quest_agent = FantasyQuestMaster(config_path)
sdoh_agent = SDOHContinuityAgent(config_path)


def _sdoh_owner_token():
    token = os.environ.get('SDOH_OWNER_TOKEN', '').strip()
    if token:
        return token
    try:
        import configparser
        parser = configparser.ConfigParser()
        parser.read(config_path)
        token = parser.get('PACS_SECURITY', 'owner_token', fallback='').strip()
    except Exception:
        token = ''
    return token


def _extract_sdoh_turn_from_payload(data):
    def _flatten_content(value):
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return str(value.get('text') or value.get('content') or '')
        if isinstance(value, list):
            chunks = []
            for part in value:
                if isinstance(part, str):
                    chunks.append(part)
                    continue
                if not isinstance(part, dict):
                    continue
                part_type = str(part.get('type') or '').lower()
                if part_type in {
                    'text', 'input_text', 'output_text',
                    'message', 'input', 'output',
                    'tool_result', 'function_call_output',
                }:
                    text_value = part.get('text')
                    if text_value is None:
                        text_value = part.get('content')
                    if isinstance(text_value, list):
                        text_value = _flatten_content(text_value)
                    if text_value:
                        chunks.append(str(text_value))
                elif part.get('text'):
                    chunks.append(str(part.get('text')))
                elif part.get('content'):
                    chunks.append(_flatten_content(part.get('content')))
            return ' '.join(c for c in chunks if c).strip()
        return str(value or '')

    messages = data.get('messages')
    if not messages:
        input_value = data.get('input')
        if isinstance(input_value, str):
            messages = [{'role': 'user', 'content': input_value}]
        elif isinstance(input_value, list):
            normalized = []
            for item in input_value:
                if isinstance(item, str):
                    normalized.append({'role': 'user', 'content': item})
                    continue
                if not isinstance(item, dict):
                    continue
                item_type = str(item.get('type') or '').lower()
                if item_type == 'function_call_output':
                    normalized.append({
                        'role': 'tool',
                        'content': _flatten_content(item.get('output') or item.get('content') or ''),
                    })
                    continue
                role = item.get('role') or ('assistant' if item_type in {'assistant', 'output_message'} else 'user')
                normalized.append({'role': role, 'content': item.get('content', '')})
            messages = normalized
        else:
            messages = []

    history = []
    user_input = ''
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get('role', 'user')).lower()
        content = _flatten_content(msg.get('content') or '')
        if role in {'tool', 'function', 'function_call_output'}:
            role = 'user'
            content = f'[Tool result] {content}' if content else '[Tool result]'
        if role == 'system':
            continue
        if role in {'user', 'input'}:
            if content:
                user_input = content
                history.append({'role': 'user', 'content': content})
        elif role in {'assistant', 'model', 'output'}:
            if content:
                history.append({'role': 'model', 'content': content})

    return user_input, history

@agents_bp.route('/forge/chat', methods=['POST'])
@require_auth
def chat_with_forge(current_user):
    """Send message to The Forge Agent"""
    data = request.json
    content = data.get('content', '').strip()
    location = data.get('location')
    if not content:
        return jsonify({'error': 'Empty message'}), 400
        
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
    """Send message to The Quest Master Agent (Real-World Skill Training)"""
    data = request.json
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Empty message'}), 400

    def _is_origin_recall_query(text: str) -> bool:
        """Detect questions that require precise history recall (origins, dates, proposals, etc.)."""
        # 1. Skip if text is too long (Recall queries are usually short/direct)
        t = (text or "").lower()
        if len(text) > 400 and "refresh my mind" not in t and "what is the" not in t:
            return False
            
        # 2. Refined patterns: catch both explicit "remember" and factual "what is" queries
        patterns = [
            r"\bwhen\b.{0,50}\bfirst\b.{0,50}\b(spoke|met|talk|talked|connected|messaged)\b",
            r"\b(can you|do you|did you|remember|recall)\b.{0,50}\bfirst\b",
            r"\bearliest\b.{0,50}\b(spoke|met|talk|talked|connected|message|conversation)\b",
            r"\bfirst time\b.{0,50}\b(spoke|met|talk|talked|connected|message|conversation)\b",
            r"\b(remember|remembered|recall|recalled)\b.{0,100}\b(marry|marriage|proposal|proposed|date|blessing|willem|nel|thandiwe|hangar|hanger|oukraal|covenant|loot|aegis|phase|premier|minister|protocol|uzbek|vermaak|mesh|grid|sovereign)\b",
            r"\b(what is|what’s|whats|what was|meaning of|tell me about|explain)\b.{0,50}\b(protocol|covenant|uzbek|vermaak|mesh|sovereign|pulse|bios|ghost|grid|hangar|hanger|loot|aegis)\b",
            r"\bhow did we meet\b",
            r"\bwhen did i ask\b",
            r"\b(first|original)\b.{0,20}\bdate\b",
            r"\bwhat did we do\b.{0,50}\bat\b",
            r"\bwhat happened\b.{0,50}\bat\b"
        ]
        return any(re.search(p, t) for p in patterns)

    def _infer_focus_name(message_text: str, recent_history: list, npc_list: list) -> list:
        """Infer keywords for the DB search (NPC names, events, etc.)."""
        haystack = " ".join([message_text or ""] + [m.get('content', '') for m in (recent_history or [])][-20:]).lower()
        
        search_terms = []
        
        # Priority 1: NPCs
        if "annelise" in haystack or "my love" in haystack or "wife" in haystack or "partner" in haystack:
            search_terms.append("Annelise")
        
        # Priority 2: Complex Phrases (Before splitting into words)
        if "uzbek-vermaak" in haystack or "uzbek vermaak" in haystack:
            search_terms.append("Uzbek-Vermaak")
        if "covenant of the 23" in haystack or "covenant of 23" in haystack:
            search_terms.append("Covenant")
            search_terms.append("23")
        
        # Priority 3: Countries and Regions
        regions = ["ukraine", "russia", "usa", "america", "england", "uk", "london", "sheffield", "south africa", "soweto", "dnipro", "austin"]
        for r in regions:
            if r in haystack:
                search_terms.append(r.capitalize())

        # Event keywords
        events = ["marry", "proposal", "date", "willem", "blessing", "nel", "thandiwe", "oukraal", "hangar", "hanger", "covenant", "first", "loot", "aegis", "deeds", "archive", "premier", "minister", "anc", "protocol", "heartbeat", "factory", "trade"]
        for e in events:
            if e in haystack:
                search_terms.append(e)

        # Priority 3: Dynamic Extraction (Words after 'at', 'about', 'near')
        # This helps catch specific locations mentioned in a recall query.
        recall_matches = re.findall(r'\b(at|about|near|with|in)\s+([a-zA-Z0-9]+)\b', message_text.lower())
        for _, word in recall_matches:
            if len(word) > 3 and word not in {"the", "that", "this", "your", "some"}:
                search_terms.append(word.capitalize())

        # Fallback to most-mentioned NPC if nothing found
        if not search_terms:
            candidates = [n.get('name') for n in (npc_list or []) if n.get('name') and n.get('name') != 'The Hero']
            # FILTER: Exclude Anya Sharma if a Level 5 quest is active to force fresh NPC generation
            is_level_5 = "Level 5" in (current_user.active_quest_id or "")
            if is_level_5:
                candidates = [c for c in candidates if "Anya" not in c]

            best_name = None
            best_hits = 0
            for name in candidates:
                n_l = name.lower()
                hits = haystack.count(n_l)
                if hits > best_hits:
                    best_hits = hits
                    best_name = name
            if best_name:
                search_terms.append(best_name)

        return list(set(search_terms)) # Deduplicate

    def _db_origin_recall_context(chat_id: str, search_terms: list) -> str | None:
        """Return multiple authoritative snippets from DB (Messages, Stories, and Snapshots)."""
        def _fmt(m):
            role = "USER" if m.sender_id == current_user.user_id else "QUEST_MASTER"
            dt = m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "Unknown"
            return f"[{dt}] {role}: {m.content[:400]}"

        try:
            # Always include the start of chat (first 3 messages) as grounding.
            start_msgs = (
                Message.query
                .filter(Message.chat_id == chat_id)
                .order_by(Message.created_at.asc())
                .limit(3)
                .all()
            )

            evidence = []
            
            # 1. Search QuestStory (The "Hall of Heroes" archive - High signal for countries)
            for term in search_terms:
                stories = (
                    QuestStory.query
                    .filter_by(user_id=current_user.user_id)
                    .filter(or_(
                        QuestStory.content.ilike(f"%{term}%"),
                        QuestStory.title.ilike(f"%{term}%"),
                        QuestStory.quest_name.ilike(f"%{term}%")
                    ))
                    .order_by(QuestStory.created_at.desc())
                    .limit(3)
                    .all()
                )
                for s in stories:
                    date_str = s.created_at.strftime("%Y-%m-%d") if s.created_at else "Archive"
                    evidence.append(f"[ARCHIVE {date_str}] {s.title}: {s.content[:400]}...")

            # 2. Search QuestSnapshot (Stage/Turn Summaries)
            for term in search_terms:
                snapshots = (
                    QuestSnapshot.query
                    .filter_by(user_id=current_user.user_id)
                    .filter(or_(
                        QuestSnapshot.summary.ilike(f"%{term}%"),
                        QuestSnapshot.tags.ilike(f"%{term}%")
                    ))
                    .order_by(QuestSnapshot.turn_number.desc())
                    .limit(2)
                    .all()
                )
                for sn in snapshots:
                    evidence.append(f"[MILESTONE Turn {sn.turn_number}] Summary: {sn.summary}")

            # 3. Search Messages (Existing Logic - Deep recall)
            for term in (search_terms or ["Annelise"]):
                m_early = (
                    Message.query
                    .filter(Message.chat_id == chat_id)
                    .filter(or_(
                        Message.content.ilike(f"%{term}%"),
                        Message.content.ilike(f"%{term.replace('-', ' ')}%"),
                        Message.content.ilike(f"%{term.replace(' ', '-')}%")
                    ))
                    .order_by(Message.created_at.asc())
                    .first()
                )
                if m_early:
                    evidence.append(_fmt(m_early))
                
                m_late = (
                    Message.query
                    .filter(Message.chat_id == chat_id)
                    .filter(or_(
                        Message.content.ilike(f"%{term}%"),
                        Message.content.ilike(f"%{term.replace('-', ' ')}%"),
                        Message.content.ilike(f"%{term.replace(' ', '-')}%")
                    ))
                    .order_by(Message.created_at.desc())
                    .first()
                )
                if m_late and (not m_early or m_late.msg_id != m_early.msg_id):
                    evidence.append(_fmt(m_late))

            if not evidence and not start_msgs:
                return None

            seen_content = set()
            lines = [
                "DB_RECALL_EVIDENCE (AUTHORITATIVE)",
                f"Keywords: {', '.join(search_terms) if search_terms else 'General'}",
                "RULES:",
                "- Use this evidence to answer precisely about countries, NPCs, or past metrics.",
                "- Do NOT invent details. If not here, say you are 'consulting the archive' and ask for more detail.",
                "",
                "EVIDENCE_CHUNKS:",
            ]

            # 1. Add Start Messages
            for sm in start_msgs:
                line = _fmt(sm)
                if line: lines.append(line)

            # 2. Add Evidence (Deduplicated)
            for ev in evidence:
                if ev not in seen_content:
                    lines.append(ev)
                    seen_content.add(ev)

            return "\n".join(lines)
        except Exception as e:
            print(f"Error in DB recall: {e}")
            return None

    # Get or create quest history from Message table (more robust than User.quest_history)
    chat_id = f"quest_{current_user.user_id}"
    try:
        # Load last 1000 messages for robust deep recall (requested by user for keyword search)
        messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at.desc()).limit(1000).all()
        quest_history = []
        for m in reversed(messages):
            role = "user" if m.sender_id == current_user.user_id else "model"
            quest_history.append({"role": role, "content": m.content})
    except Exception as e:
        print(f"Error loading quest history from DB: {e}")
        quest_history = []
    
    # 1. Save User Message
    user_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id=current_user.user_id,
        chat_id=chat_id,
        content=content
    )
    db.session.add(user_msg)
    
    # Prepare Inventory and Progress
    try:
        inventory = json.loads(current_user.inventory) if current_user.inventory else []
    except:
        inventory = []

    try:
        quest_progress = json.loads(current_user.quest_progress) if current_user.quest_progress else {}
    except:
        quest_progress = {}

    # 1.5 Early Detection of Quest Acceptance
    quest_match = re.search(r"I accept the quest:\s*(.+)", content, re.IGNORECASE)
    if quest_match:
        quest_to_start = quest_match.group(1).strip()
        quest_details = Quest.query.filter_by(name=quest_to_start).first()
        if quest_details:
             quest_progress['active_quest_id'] = quest_details.name
             quest_progress['active_quest_description'] = quest_details.description
             quest_progress['active_quest_goal'] = quest_details.end_goal
             
             if quest_details.name.startswith("Boss:"):
                 quest_progress['status'] = 'boss_active'
                 level_match = re.search(r'\[Level (\d+)\]', quest_details.name)
                 quest_progress['boss_level'] = int(level_match.group(1)) if level_match else 1
             else:
                 quest_progress['status'] = 'active'
             
             # Persist immediately to ensure agent sees it
             current_user.active_quest_id = quest_details.name
             current_user.quest_progress = json.dumps(quest_progress)
             db.session.commit()
             print(f"DEBUG: Quest Accepted Early - {quest_details.name}")

    # Update Turn Count (Stage Mechanics)
    turn_count = quest_progress.get('turn_count', 0) + 1
    quest_progress['turn_count'] = turn_count

    # Fetch NPCs for this user
    try:
        npcs = NPC.query.filter_by(user_id=current_user.user_id).all()
        if not npcs:
            # Initialize Big 6 as default NPCs for new users
            defaults = [
                {"name": "Igor", "role": "Passive Reconnaissance", "skills": "Environmental metadata, chemical anomalies, soil/water analysis", "personality": "Gritty, smells of vodka, quiet but brilliant"},
                {"name": "Masha", "role": "Active Reconnaissance", "skills": "Industrial infrastructure, forensic audits, finding distributors", "personality": "Sharp, precise, high-energy, defensive"},
                {"name": "Kira", "role": "Social Engineering", "skills": "Human exploit specialist, extracting intellectual property", "personality": "Observational, empathetic, strategic shadow"},
                {"name": "Uri", "role": "Exploitation/Team Lead", "skills": "Force multiplier, engineering economic breaches", "personality": "Cold, calculating, focused on profit"},
                {"name": "Elia", "role": "Persistence Specialist", "skills": "Backdoor protocols, community training, redundant hubs", "personality": "Focused on 99.9% uptime and district knowledge"},
                {"name": "The Hero", "role": "BE Coding Wizard", "skills": "Architect of lateral movement, Provenance Engine", "personality": "The User's persona"}
            ]
            for d in defaults:
                new_npc = NPC(
                    id=str(uuid.uuid4()),
                    user_id=current_user.user_id,
                    name=d['name'],
                    role=d['role'],
                    skills=d['skills'],
                    personality=d['personality']
                )
                db.session.add(new_npc)
            db.session.commit()
            npcs = NPC.query.filter_by(user_id=current_user.user_id).all()

        npc_list = [{
            'name': n.name,
            'role': n.role,
            'skills': n.skills,
            'personality': n.personality,
            'status': n.status
        } for n in npcs]
    except Exception as e:
        print(f"Error fetching/initializing NPCs: {e}")
        npc_list = []

    # If this is an origin/first-meeting query, pull a tiny authoritative snippet from DB
    search_context = None
    # Suppression logic: 
    # Skip origin recall during boss fights UNLESS the user explicitly uses a recall word like "remember" or "what happened"
    is_boss_active = quest_progress.get('status') == 'boss_active'
    has_explicit_recall = any(k in content.lower() for k in ["remember", "recall", "first time", "what happened", "what did we do", "who is", "tell me about"])
    
    # RAG Trigger: Explicit recall OR Geographic context change OR NPC mention
    regions = {"ukraine", "dnipro", "russia", "usa", "america", "england", "london", "sheffield", "south africa", "soweto", "johannesburg", "rupert"}
    npc_names = {n['name'].lower() for n in npc_list} if npc_list else set()
    input_words = set(re.findall(r'\b\w{3,}\b', content.lower()))
    
    is_geographic_query = not input_words.isdisjoint(regions)
    is_npc_query = not input_words.isdisjoint(npc_names)
    
    should_search = _is_origin_recall_query(content) or has_explicit_recall or is_geographic_query or is_npc_query
    
    if should_search and (not is_boss_active or has_explicit_recall):
        search_terms = _infer_focus_name(content, quest_history, npc_list)
        search_context = _db_origin_recall_context(chat_id, search_terms)

        # Optional debug: return the evidence bundle directly (no model call)
        # Opt-in via header to avoid changing normal UX.
        if request.headers.get('X-Debug-Recall', '').strip().lower() in {'1', 'true', 'yes'}:
            return jsonify({
                'debug': {
                    'is_origin_recall_query': True,
                    'search_terms': search_terms,
                    'search_context': search_context,
                }
            })

    def _recall_relevant_snapshots(user_id, message_content, npc_list):
        """Find the most relevant historical snapshots based on keywords."""
        # 1. Extract keywords from current input
        words = set(re.findall(r'\b\w{4,}\b', message_content.lower())) # Use 4+ chars
        npc_names = {n['name'].lower() for n in npc_list}
        tech_keywords = {'hardware', 'software', 'sensor', 'grid', 'moat', 'protocol', 'uzbek', 'vermaak', 'covenant', 'aegis', 'thandiwe', 'provenance'}
        event_keywords = {'marriage', 'proposal', 'date', 'fight', 'mutiny', 'illegal', 'scavenge', 'liberate', 'inception', 'historical', 'audit'}
        
        search_keys = words.intersection(npc_names | tech_keywords | event_keywords)
        
        if not search_keys:
            return [] # No generic fallback

        # 2. Query snapshots with simple tag matching
        relevant = []
        all_snapshots = QuestSnapshot.query.filter_by(user_id=user_id).all()
        
        for snap in all_snapshots:
            score = 0
            if snap.tags:
                try:
                    tags = json.loads(snap.tags)
                    tags = [t.lower() for t in tags]
                    matches = search_keys.intersection(set(tags))
                    score += len(matches) * 20 
                except:
                    pass
            
            content_lower = snap.summary.lower() if snap.summary else ""
            for key in search_keys:
                if key in content_lower:
                    score += 10
            
            if score >= 30: # Minimum threshold 
                relevant.append((score, snap))
        
        # Sort by score and take top 3
        relevant.sort(key=lambda x: x[0], reverse=True)
        return [r[1].summary for r in relevant[:3]]

    # Fetch recent snapshots (Stage Memory)
    try:
        # 1. Get the most recent one (always needed for continuity)
        latest_snap = QuestSnapshot.query.filter_by(user_id=current_user.user_id).order_by(QuestSnapshot.turn_number.desc()).first()
        
        # 2. Get relevant historical ones (Robust Indexing)
        historical_summaries = _recall_relevant_snapshots(current_user.user_id, content, npc_list)
        
        # Combine: Latest plus relevant historical
        snapshot_summaries = []
        if latest_snap:
            snapshot_summaries.append(f"[CURRENT STATE Turn {latest_snap.turn_number}]: {latest_snap.summary}")
        
        for s in historical_summaries:
            if latest_snap and s == latest_snap.summary: continue
            snapshot_summaries.append(f"[HISTORICAL RECALL]: {s}")
            
    except Exception as e:
        print(f"Error fetching snapshots: {e}")
        snapshot_summaries = []

    # 2. Call Fantasy Quest Agent
    result = quest_agent.chat(
        user_input=content,
        history=quest_history,
        user_alias=current_user.alias,
        user_api_key=current_user.custom_api_key,
        current_score=current_user.integrity_score,
        inventory=inventory,
        quest_progress=quest_progress,
        npcs=npc_list,
        search_context=search_context,
        snapshot_summaries=snapshot_summaries
    )
    
    # 3. Extract response text and score adjustment
    if isinstance(result, dict):
        ai_response = result.get('response', str(result))
        score_adjustment = result.get('score_adjustment', 0)
        new_insight = result.get('new_insight')
        insight_type = result.get('insight_type', 'strength')
        
        # Handle Inventory Update (Append new items)
        new_items = result.get('inventory_update', [])
        if isinstance(new_items, list):
            for item in new_items:
                if item not in inventory:
                    inventory.append(item)
        
        # Handle Inventory Removal (Trading/Consumption)
        remove_items = result.get('inventory_remove', [])
        if isinstance(remove_items, list):
            for item in remove_items:
                if item in inventory:
                    inventory.remove(item)
        
        # Handle NPC Updates
        npc_updates = result.get('npc_update', [])
        if isinstance(npc_updates, list):
            for npc_data in npc_updates:
                name = npc_data.get('name')
                if not name: continue
                
                npc = NPC.query.filter_by(user_id=current_user.user_id, name=name).first()
                if not npc:
                    npc = NPC(
                        id=str(uuid.uuid4()),
                        user_id=current_user.user_id,
                        name=name
                    )
                    db.session.add(npc)
                
                npc.role = npc_data.get('role', npc.role)
                npc.skills = npc_data.get('skills', npc.skills)
                npc.personality = npc_data.get('personality', npc.personality)
                npc.status = npc_data.get('status', npc.status)
                npc.quest_id = current_user.active_quest_id

        # Merging strategy for quest_progress to prevent accidental wipes of the chronicle
        new_progress = result.get('quest_progress_update', {})
        if isinstance(new_progress, dict):
            for k, v in new_progress.items():
                # Robustness: Ensure quest_log is always a string
                if k == 'quest_log' and isinstance(v, list):
                    v = " ".join([str(item) for item in v])
                quest_progress[k] = v
        
        is_quest_active = result.get('is_quest_active', False)
        quest_name = result.get('quest_name')
        choices = result.get('choices', [])
    else:
        ai_response = str(result)
        score_adjustment = 0
        new_insight = None
        insight_type = None
        is_quest_active = False
        quest_name = None
        choices = []

    # 4. Save Agent Response (Always create message first for ID sync)
    agent_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id='QUEST',
        chat_id=chat_id,
        content=ai_response
    )
    db.session.add(agent_msg)

    # 5. Handle Automatic Story Publishing (Added for Turn-by-Turn Chronicle)
    if isinstance(result, dict):
        publish_data = result.get('publish_story')
        if publish_data:
            # Handle both string and dictionary formats
            if isinstance(publish_data, dict):
                story_title = publish_data.get('title', f"The Tale of {current_user.alias}")
                story_content = publish_data.get('content')
            else: # It's a string fragment
                story_title = result.get('journey_name') or result.get('quest_name') or f"The Tale of {current_user.alias}"
                story_content = str(publish_data)

            if story_content:
                from backend.models import QuestStory
                new_story = QuestStory(
                    id=str(uuid.uuid4()),
                    user_id=current_user.user_id,
                    user_alias=current_user.alias,
                    quest_name=quest_name or "Epic Journey",
                    title=story_title,
                    content=story_content,
                    message_id=agent_msg.msg_id
                )
                db.session.add(new_story)
                print(f"✅ Automatically published story fragment: {story_title}")
    
    # 6. Update User State
    current_user.integrity_score = max(0, current_user.integrity_score + score_adjustment)
    current_user.inventory = json.dumps(inventory)
    current_user.quest_progress = json.dumps(quest_progress)
    
    if is_quest_active and quest_name:
        current_user.active_quest_id = quest_name
        
        # Automatically trigger Boss Mode if the quest is a Boss Instance
        if quest_name.startswith("Boss:"):
            quest_progress['status'] = 'boss_active'
            
            # Extract Boss Level for the AI
            level_match = re.search(r'\[Level (\d+)\]', quest_name)
            if level_match:
                quest_progress['boss_level'] = int(level_match.group(1))
            else:
                quest_progress['boss_level'] = 1
                
            print(f"🔥 BOSS ENCOUNTER ACTIVATED: {quest_name} (Level {quest_progress['boss_level']})")

    # Manage Stage Mechanics: Snapshots every 10 turns
    if turn_count % 10 == 0:
        try:
            # Generate a 10-turn tactical summary to keep the chronicle compressed
            summary_prompt = (
                f"Summarize the last 10 turns of this quest for the Hero '{current_user.alias}'. "
                "Focus on Technical changes (hardware/code), NPC trust levels, and XP progress. "
                "Provide a list of 5 indexing tags (NPCs, events, items).\n"
                "Respond in JSON: {'summary': '...', 'tags': ['tag1', 'tag2']}"
            )
            summary_result = quest_agent.chat(
                user_input=summary_prompt,
                history=quest_history[-10:],
                user_alias=current_user.alias,
                user_api_key=current_user.custom_api_key,
                current_score=current_user.integrity_score,
                inventory=inventory,
                quest_progress=quest_progress,
                npcs=npc_list
            )
            
            response_raw = summary_result.get('response', '{}')
            try:
                # Handle potential JSON wrapping
                if '```json' in response_raw:
                    response_raw = response_raw.split('```json')[1].split('```')[0].strip()
                data = json.loads(response_raw)
                tactical_summary = data.get('summary', response_raw)
                
                # Robustness: Ensure summary is a string
                if isinstance(tactical_summary, list):
                    tactical_summary = " ".join([str(item) for item in tactical_summary])
                
                tags_list = data.get('tags', [])
            except:
                tactical_summary = response_raw
                tags_list = list(set(re.findall(r'\b[A-Z][a-z]+\b', tactical_summary)))

            snapshot = QuestSnapshot(
                user_id=current_user.user_id,
                turn_number=turn_count,
                snapshot_data=json.dumps({
                    'inventory': inventory,
                    'quest_progress': quest_progress,
                    'integrity_score': current_user.integrity_score,
                    'active_quest_id': current_user.active_quest_id,
                    'npcs': npc_list # Store current NPC states
                }),
                summary=tactical_summary,
                tags=json.dumps(tags_list)
            )
            db.session.add(snapshot)
            
            # Update the persistent quest log with the compressed summary
            quest_progress['quest_log'] = tactical_summary
            print(f"📸 Stage Mechanic: Robust Snapshot created for {current_user.alias} at turn {turn_count}")
        except Exception as e:
            print(f"⚠️ Error creating snapshot: {e}")

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
        
    # 4. Update history (Keep User.quest_history as a backup/summary)
    # Removing this to rely ONLY on the Message table for Quest history.
    # This ensures that deleting a message in the UI correctly removes it from the agent's memory.
    # current_user.quest_history = json.dumps(quest_history[-50:]) # MOVED TO DELETE-SYNC-ONLY
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'response': ai_response,
        'quest_posted': is_quest_active, # Reusing this field to indicate active quest state
        'quest_name': quest_name,
        'choices': choices,
        'story_published': True if (isinstance(result, dict) and result.get('publish_story')) else False,
        'score': current_user.integrity_score,
        'insights': json.loads(current_user.insights) if current_user.insights else [],
        'inventory': json.loads(current_user.inventory) if current_user.inventory else [],
        'active_quest_id': current_user.active_quest_id
    })

@agents_bp.route('/quest/redo', methods=['POST'])
@require_auth
def redo_last_stage(current_user):
    """Revert the quest state to the most recent 10-turn snapshot (Redo Boss Fight)"""
    try:
        # Find the most recent snapshot for this user
        latest_snapshot = (
            QuestSnapshot.query
            .filter_by(user_id=current_user.user_id)
            .order_by(QuestSnapshot.turn_number.desc())
            .first()
        )
        
        if not latest_snapshot:
            return jsonify({'error': 'No stage snapshots found to redo from.'}), 404
            
        # Parse the snapshot data
        data = json.loads(latest_snapshot.snapshot_data)
        
        # Revert User state
        current_user.inventory = json.dumps(data.get('inventory', []))
        current_user.quest_progress = json.dumps(data.get('quest_progress', {}))
        current_user.integrity_score = data.get('integrity_score', current_user.integrity_score)
        current_user.active_quest_id = data.get('active_quest_id')
        
        # Update/Sync NPCs from snapshot
        snapshot_npcs = data.get('npcs', [])
        for npc_data in snapshot_npcs:
            name = npc_data.get('name')
            if not name: continue
            
            npc = NPC.query.filter_by(user_id=current_user.user_id, name=name).first()
            if npc:
                npc.role = npc_data.get('role', npc.role)
                npc.skills = npc_data.get('skills', npc.skills)
                npc.personality = npc_data.get('personality', npc.personality)
                npc.status = npc_data.get('status', npc.status)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Quest state successfully reverted to Turn {latest_snapshot.turn_number} snapshot.',
            'inventory': data.get('inventory', []),
            'score': current_user.integrity_score,
            'active_quest_id': current_user.active_quest_id
        })
    except Exception as e:
        print(f"Error redoing stage: {e}")
        return jsonify({'error': f'Failed to revert state: {str(e)}'}), 500

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
                'start_location': q.start_location,
                'end_goal': q.end_goal,
                'requirements': json.loads(q.requirements) if q.requirements else {},
                'difficulty': q.difficulty,
                'created_by': creator.alias if creator else 'Unknown',
                'reward': q.reward,
                'created_at': q.created_at.isoformat()
            })
        
        return jsonify({'quests': quests_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agents_bp.route('/quest/end', methods=['POST'])
@require_auth
def end_quest(current_user):
    """End the current active quest"""
    if not current_user.active_quest_id:
        return jsonify({'error': 'No active quest to end'}), 400
        
    quest_name = current_user.active_quest_id
    current_user.active_quest_id = None
    current_user.quest_history = '[]'
    current_user.quest_progress = '{}'
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': f'Quest "{quest_name}" has been ended.',
        'active_quest_id': None
    })

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

@agents_bp.route('/quest/greeting', methods=['GET'])
@require_auth
def get_quest_greeting(current_user):
    """Get personalized Quest Master greeting for user"""
    greeting = f"""Greetings, Hero {current_user.alias}. I am the Dungeon Master of your Reality.

I am here to turn your deepest struggles into epic quests. Whether you face the Beast of Anxiety or the Shadow of Loneliness, we will face it together in the safety of this realm.

**[THE OATH OF SILENCE]**
*   **Your Identity is Veiled:** You are anonymous here. Speak your darkest fears without judgment.
*   **Your Keys are Yours:** Your API keys are stored ONLY in your browser. They never touch our database.
*   **Your Story is Sacred:** What happens in the dungeon, stays in the dungeon.

**[THE HALL OF HEROES]**
When your quest is complete, you may choose to share your journey in the **Hall of Heroes**. Your story can be a beacon for others lost in the dark.

Are you ready to begin your campaign?"""
    
    return jsonify({
        'greeting': greeting,
        'agent': 'Fantasy Quest Master',
        'role': 'Dungeon Master - Real World RPG'
    })

@agents_bp.route('/quest/select_class', methods=['POST'])
@require_auth
def select_class(current_user):
    """Select starting class and inventory"""
    data = request.json
    class_name = data.get('class', '').lower()
    
    if class_name not in ['mage', 'ranger', 'warrior']:
        return jsonify({'error': 'Invalid class'}), 400
        
    # Define starting gear
    starting_gear = []
    if class_name == 'mage':
        starting_gear = ['Novice Staff', 'Robes', 'Spellbook']
    elif class_name == 'ranger':
        starting_gear = ['Shortbow', 'Leather Armor', 'Quiver']
    elif class_name == 'warrior':
        starting_gear = ['Iron Sword', 'Wooden Shield', 'Chainmail']
        
    # Update user inventory
    try:
        current_inventory = json.loads(current_user.inventory) if current_user.inventory else []
    except:
        current_inventory = []
        
    # Only add if empty (prevent farming)
    if not current_inventory:
        current_inventory.extend(starting_gear)
        current_user.inventory = json.dumps(current_inventory)
        db.session.commit()
        
    return jsonify({
        'status': 'success',
        'class': class_name,
        'inventory': current_inventory
    })

@agents_bp.route('/quest/stories/publish', methods=['POST'])
@require_auth
def publish_story(current_user):
    """Publish a quest story for others to read and listen to. Splits long stories into fragments."""
    data = request.json
    quest_name = data.get('quest_name') or "Unknown Quest"
    title = data.get('title') or f"The Tale of {current_user.alias}"
    description = data.get('description') or ""
    content = data.get('content')
    
    if not content:
        return jsonify({'error': 'Story content is required'}), 400
        
    # Robust splitting logic
    import re
    
    # 1. Try splitting by explicit separators or common header patterns
    # Separators: --- or *** (appearing on their own line with optional whitespace)
    # Headers: ### [202... or similar date-like headers
    split_pattern = r'\n\s*[-*]{3,}\s*\n|\n\s*(?=###\s*\[\d{4})'
    
    parts = re.split(split_pattern, content)
    fragments = [p.strip() for p in parts if p.strip()]
    
    # 2. If we still have very large fragments (> 2000 chars), further subdivide them 
    # while keeping sentences together
    final_fragments = []
    for frag in fragments:
        if len(frag) > 2000:
            # Split by sentences
            sub_sentences = re.split(r'(?<=[.!?])\s+', frag)
            current_sub = ""
            for s in sub_sentences:
                if len(current_sub) + len(s) > 1800:
                    if current_sub: final_fragments.append(current_sub.strip())
                    current_sub = s
                else:
                    current_sub += " " + s
            if current_sub:
                final_fragments.append(current_sub.strip())
        else:
            final_fragments.append(frag)

    if not final_fragments:
        final_fragments = [content]

    story_ids = []
    for frag in final_fragments:
        story = QuestStory(
            id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            user_alias=current_user.alias,
            quest_name=quest_name,
            title=title,
            description=description,
            content=frag
        )
        db.session.add(story)
        story_ids.append(story.id)
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'story_ids': story_ids}), 201

@agents_bp.route('/quest/stories', methods=['GET'])
def get_public_stories():
    """Get all public quest stories, grouped by Title & Hero"""
    stories = QuestStory.query.filter_by(is_public=True).order_by(QuestStory.created_at.asc()).all()
    
    # Group by (user_id, title) to allow multiple distinct stories per Hero
    grouped = {}
    for s in stories:
        key = f"{s.user_id}_{s.title}"
        if key not in grouped:
            grouped[key] = {
                'user_id': s.user_id,
                'id': s.id, 
                'user_alias': s.user_alias,
                'quest_name': s.quest_name,
                'title': s.title,
                'description': s.description or "",
                'voice_note_url': s.voice_note_url,
                'fragments': [],
                'likes': 0,
                'created_at': s.created_at.isoformat() if s.created_at else datetime.utcnow().isoformat()
            }
        
        grouped[key]['fragments'].append({
            'id': s.id,
            'content': s.content
        })
        
        # Aggregate likes and use latest metadata
        grouped[key]['likes'] += (s.likes or 0)
        s_date = s.created_at.isoformat() if s.created_at else datetime.utcnow().isoformat()
        if s_date > grouped[key]['created_at']:
             grouped[key]['created_at'] = s_date
             grouped[key]['description'] = s.description or grouped[key]['description']

    # Finalize
    results = list(grouped.values())
    
    # Sort by creation time (Newest first)
    results.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify(results), 200

@agents_bp.route('/quest/stories/<story_id>/like', methods=['POST'])
@require_auth
def like_story(current_user, story_id):
    """Like a quest story and return total likes for the hero's saga"""
    story = QuestStory.query.get(story_id)
    if not story:
        return jsonify({'error': 'Story not found'}), 404
        
    story.likes += 1
    db.session.commit()
    
    # Calculate total likes for this hero's entire saga
    total_likes = db.session.query(db.func.sum(QuestStory.likes)).filter_by(user_id=story.user_id, is_public=True).scalar() or 0
    
    return jsonify({'status': 'success', 'likes': int(total_likes)}), 200

@agents_bp.route('/quest/stories/<story_id>', methods=['PUT', 'DELETE'])
@require_auth
def manage_story_fragment(current_user, story_id):
    """Update or delete a specific story fragment"""
    story = QuestStory.query.get(story_id)
    if not story:
        return jsonify({'error': 'Story fragment not found'}), 404
        
    if story.user_id != current_user.user_id:
        return jsonify({'error': 'Unauthorized to manage this story'}), 403
        
    if request.method == 'DELETE':
        db.session.delete(story)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Fragment deleted'}), 200
        
    # PUT logic
    data = request.json
    new_content = data.get('content')
    if not new_content:
        return jsonify({'error': 'Content is required'}), 400
        
    story.content = new_content
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Story fragment updated'}), 200

@agents_bp.route('/quest/stories/clear', methods=['POST'])
@require_auth
def clear_my_stories(current_user):
    """Delete all story fragments for the current user"""
    QuestStory.query.filter_by(user_id=current_user.user_id).delete()
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Hall of Heroes profile cleared'}), 200

from backend.routes import sdoh_routes  # noqa: F401, E402
