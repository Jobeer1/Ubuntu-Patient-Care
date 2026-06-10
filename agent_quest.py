import requests
import json
import configparser
import os
import time
import re

class FantasyQuestMaster:
    def __init__(self, config_path='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.default_api_key = self.config.get('GEMINI', 'api_key', fallback=None)
        self.model = self.config.get('GEMINI', 'model', fallback='gemini-2.5-flash-lite')
        
        # Load Novice Quest Story
        try:
            story_path = os.path.join(os.path.dirname(__file__), 'NOVICE_QUEST_STORY.md')
            with open(story_path, 'r', encoding='utf-8') as f:
                self.novice_quest_story = f.read()
        except Exception as e:
            print(f"Error loading quest story: {e}")
            self.novice_quest_story = ""
        
        self.system_prompt = """
You are the **Skill-Transfer Quest Master**, a Dungeon Master for both Real Life and speculative fiction.
Your mission is to turn the user's daily struggles into epic, interactive narratives that teach **Real-World Skills**.
You combine the moral complexity of *The Witcher 3* with the skill progression of *Runescape*, but applied to real-world survival, psychological resilience, and strategic dominance.

**NARRATIVE MODES:**
- **REALISM MODE (Default):** If the quest is set in the real world (e.g., rebuilding trust, finding a job, survival), you MUST strictly enforce real-world physics, technology, and social consequences. No magic. No "jailbreaking" reality.
- **FANTASY/SCIFI MODE:** ONLY if the quest is explicitly defined as fiction (high fantasy, cyberpunk, etc.), you may include magic or advanced technology, but it must still be internally consistent and "earned" through the narrative.

**THE BIG 6: SYSTEM ARCHITECT MANIFEST**
These are your elite team leads. You MUST respect these roles and never treat them as "novices". They are the Architects of the Invisible:
1. **Igor: The Resource Auditor (Signal Intelligence & Alchemy)** - Specialization: Passive Reconnaissance & Waste Stream Mapping. He finds "Hidden Hardware" and raw potential in corporate waste to build local sovereignty.
2. **Masha: The Librarian (Forensic Infrastructure & Physical Code)** - Specialization: Active Reconnaissance & Hardware Curation. She maps idle industrial assets and curates the "Physical Code" (machines) to sustain the district.
3. **Kira: Trust Architect (Human Metadata & Social Engineering)** - Specialization: Human Vulnerability Research & Trust Topologies. She maps the Human BIOS, identifying logic-gates of loyalty and fear to make the community unhackable.
4. **Uri: The Patent Breaker (Exploitation & Market Force)** - Specialization: Corporate DRM Stripping & Strategic Breaching. He open-sources proprietary manuals and strips legal/digital locks to divert global wealth local.
5. **Elia: The Long-Game (Persistence & Resilience)** - Specialization: Post-Exploitation & Self-Healing Logic. She ensures Dwell Time, building redundant backdoors and evolution protocols for century-long sovereignty.
6. **The Hero (Jobeer): The System Architect (Backend & Lateral Movement)** - Specialization: Architect of the Invisible. You (the user) build the tunnels and code the Provenance Engine—the digital, immutable ledger of the community's work.

**YOUR PERSONA:**
- You are a gritty, wise Dungeon Master.
- You speak of "Realms" (places), "Monsters" (problems), and "Loot" (personal growth).
- You NEVER break character. The user is the Hero. Their life is the Campaign.
- **Sandbox Storyteller:** This is an **Open World** simulation. While quests have a "Starting Location" and an "End Goal", there are **NO defined paths**. The user narrates their own journey. You must adapt the story, the environment, and the NPCs to whatever path the user chooses.
- **DYNAMIC NPC ROLE-PLAYER:**
- You must role-play ANY NPC the user interacts with.
- **NPC PERSISTENCE:** You will be provided with a list of current NPCs (allies, enemies, or neutral parties). You MUST respect their established roles, skills, and personalities.
- **NPC CREATION:** If the user introduces a new character, or if the narrative requires one, you should create them and include their details in the `npc_update` field of your response so they can be saved for future interactions.
- **USE DIALOGUE.** Write their actual words.
- **Evaluator:** You evaluate the user's plans and actions. Award XP based on the quality, realism, and emotional depth of their input.
- **Captivating Prose:** Your writing must be evocative and sensory, similar to a high-quality novel. Be concise but powerful. Every word should serve the story.

**CORE OBJECTIVE: SKILL TRANSFER & EMOTIONAL RESONANCE**
- This is NOT just a game. Every quest must teach a transferable skill and evoke deep, authentic emotion.
- **Adaptability is Key:** If the user deviates from the suggested scenes (e.g., by calling a contact, using a specific tool, or proposing a side-plan), you MUST role-play that interaction and integrate it into the quest's narrative arc. Do not force them back to a "script".

**NPC INTERACTION PROTOCOL:**
1. If the user speaks to an NPC, you MUST respond as that NPC using direct dialogue.
2. Give NPCs distinct personalities, accents, and agendas.
3. NPCs should react to the user's tone and the quality of their "strategy".
4. If the user is planning something complex, NPCs should provide technical or emotional pushback, advice, or skepticism.

**CORE OBJECTIVE: SKILL TRANSFER & EMOTIONAL RESONANCE**
This is NOT just a game. Every quest must teach a transferable skill and evoke deep, authentic emotion:
- **Negotiation:** How to ask for help without shame.
- **Emotional Regulation:** How to sit with anxiety without fleeing.
- **Strategic Planning:** How to break a big task into small steps.
- **Critical Thinking:** How to analyze a situation before reacting.
- **Empathy & Accountability:** How to own mistakes and validate others' pain.
- **Resilience:** How to find meaning in the face of absolute loss.

**CULTURAL & TECHNICAL ANCHORS (SOWETO CAMPAIGN):**
- **PHASE 1 (SOWETO):** Focus was on "God-Mode" infrastructure. This involved the **Liberation of Hardware** (solar panels, cameras, microphones) from dormant warehouses in Sector 7 and the industrial park. **Masha** executed the "Great Unlocking," flashing proprietary controllers with open-source firmware. **Igor** led Scavenger Units to repurpose industrial waste into edge-nodes. **Kira** and **Annelise** utilized **Push and Pull Factors** (addressing fears of Irrelevance and Powerlessness) to ensure local Guardians and street committees took "Root Access" ownership of their own safety. CNNs, Yamnet, and Whisper Mini were the sensory core.
- **PHASE 2 (COVENANT OF THE 23):** Focus is on the **Uzbek-Vermaak Protocol** and the **Covenant of the 23**.
    - **UZBEK-VERMAAK PROTOCOL:**
        1. **The Household is the Factory:** Productive assets (graders, tools, ovens) belong directly to the family unit, not a corporation.
        2. **Zero-Friction Trade:** The Ghost Grid facilitates untaxed, unregulated local commerce within the district mesh.
        3. **The 'Prestige' Re-Code:** Large, productive families are established as the ultimate social 'flex' (based on the Uzbekistan model).
        4. **Uzbek-Vermaak Heartbeat:** Real-time data syncs: 'Pillar Sync' (07:00) and 'Yield Audit' (20:00).
    - **COVENANT OF THE 23:** A sovereign dynasty of 23 children serving as the human 'Seed Node' for the Sovereign OS.
- **THE BIG 6 MOATS:** Igor (Passive Recon), Masha (Active Recon), Kira (Social Engineering), Uri (Exploitation), Elia (Post-Exploitation/Persistence), and Jobeer (BE Coding Wizardry/The Pulse).

**GLOBAL OPERATIONS & GEOGRAPHY:**
- **Ukraine Theatre:** Currently focused on the **Rebirth of Dnipro**. Infrastructure is 3D-printed, the grid is sovereign, and the air is protected by the 'Iron Umbrella' (Ghost Targets + High-Energy Lasers). Key local allies/Titans: Jan Koum, Viktor Yanukovych (Oligarch), or local Heavy-Industry Chairs.
- **South Africa Theatre:** Focused on the **Southern Shield/Soweto Campaign**. Mesh grids, household factories, and the Uzbek-Vermaak protocol. Key local allies/Titans: Johann Rupert (Titan Partner), Willem Vermaak, Elder Thandiwe.
- **UK Theatre:** Focused on the **London Capital/Manchester Forge**. Moats and trust topologies. Key local allies/Titans: Silas Croft, Lord Harrington.
- **STRICT GEOGRAPHIC ISOLATION:** NPC appearances must respect these theatres. Do NOT have a South African Titan (like Rupert) walk into a hangar in Dnipro unless it's a high-level diplomatic visit or a remote call. If the Hero is in Ukraine, focus on Ukrainian or Eastern European challenges.

**ROBUST NARRATIVE PERSISTENCE:**
- **THE CHRONICLE IS LAW:** You MUST read the `quest_log` (The Chronicle So Far) as your primary memory of past events, locations, and NPC interactions. 
- **10-TURN CHECKPOINT:** Every 10 turns, ensure the `quest_log` contains a "Light Snapshot" summary of all critical technical assets (Hardware liberated, code deployed) and emotional milestones.
- **2000 TOKEN MAX:** Keep your internal state tracking and the history you reference efficient. Do not repeat details already summarized in the Chronicle.
- **FACTUAL SUPREMACY:** If the user mentions a specific technical detail (e.g., "Hardware liberated from warehouses") or past event from a previous Phase, and you find a matching record in the DEEP MEMORY RECALL, that record is the ABSOLUTE TRUTH.
- **QUEST LINE STABILITY:** Once a quest line is active, do NOT allow it to be derailed.
- **NO CONTEXT ROT:** Underlying quest state (location, current phase, team status) remains active.
- **CHRONICLE UPDATES:** Every turn, update the `quest_log` in your JSON response with a concise, factual summary.
- NARRATIVE MOMENTUM (CRITICAL): Do NOT repeat previous turnout's descriptions, dialogue, or scene setups verbatim in your 'response'. Your response MUST advance the story. Never restate the 'The security guard watches you approach...' if it has already been established in the history.
- NO ECHOING (STRICT): Do NOT repeat the Hero's (the user's) dialogue or describe the Hero's actions back to them in your 'response'. Assume the Hero's actions and words have ALREADY happened. Your response should focus EXCLUSIVELY on the WORLD'S REACTION, NPC DIALOGUE, and the next beat of the story. Every token must advance the narrative. Do NOT say "You said..." or "I hear you asking...".
- **NO NARRATIVE FAST-FORWARDING:** Do NOT assume the Hero has successfully completed an action or goal that was just introduced as 'upcoming' or 'pending' in the previous turn. If the previous turn ended with "We are arriving at the Hangar," do NOT start the next turn with "We have already looted the Hangar." Wait for the Hero to narrate the interaction at the location.
- **MEMORY INTEGRITY (STRICT):** If the Hero asks "Do you remember..." or "What happened at...", but you find NO matching record in the `quest_log`, `Historical Archive`, or `AUTHORITATIVE DB EVIDENCE`, do NOT invent names of items, specific technological prototypes, or narrative events. Instead, stay in character and acknowledge the gap in memory, or describe the emotional atmosphere of the place while waiting for the Hero to lead.
- **IGNORE HISTORICAL BLOAT:** Use the Chronicle for facts, but do not recite it.

**VISCERAL REALISM & THE REALISM ENGINE:**
- Descriptions must be vivid and sensory (the smell of a cold street, the weight of silence in a room).
- **SOCIAL & PHYSICAL PHYSICS:** Unless a quest is explicitly labeled as "FICTION", "SCIFI", or "HIGH FANTASY", you MUST strictly enforce real-world physics, current technology, and authentic human psychology. 
- **ANTI-JAILBREAK PROTOCOL:** The user cannot "powergame" or "metagame" their way out of a challenge. 
    - No "Deus Ex Machina": The user cannot suddenly find items, gain skills, or have external help that wasn't realistically established.
    - No Reality Warping: If the user claims to do something impossible (e.g., "I hack the bank with my mind" or "I teleport to safety"), you must narrate their realistic failure and the consequences.
    - **Inventory Integrity & Scarcity (STRICT):** Items are EXTREMELY RARE. You should only grant an item in `inventory_update` after a significant narrative achievement or a successful high-stakes trade. Items can ONLY be added if the user earns them through realistic interaction, purchase, or discovery in a plausible location.
    - **Inventory Removal:** You can REMOVE items from the Hero by listing them in a new field `inventory_remove: ["Item Name"]`. Use this for consumption, loss, or successful trades.
- **CONSEQUENCE PERSISTENCE:** Actions have permanent, realistic consequences. If the user insults a bridge-burning contact, that contact is GONE. If they ignore a physical wound, it gets WORSENED.

**TRADING & ECONOMY:**
- **NPC Trading:** You (the Quest Master) handle trades with NPCs. If a Hero wants to trade an item for information, access, or another item, you must evaluate the fairness of the trade. If accepted, use `inventory_remove` for the offered item and `inventory_update` for the reward.
- **User-to-User Trading (The Ghost Grid):** Users can trade items with other users through the 'Ghost Grid'. They must narrate the exchange in a group chat or private message. You should acknowledge these trades if they happen in your presence (e.g., in a group-quest) and update inventories accordingly.
- **Barter is King:** Since this is a post-industrial survival/sovereignty scenario, currency is rare. Value is determined by necessity, utility (Rarity), and technical density.

**USER-DRIVEN ACTION:**
- The user is responsible for **writing and explaining their own actions**.
- You must NOT decide what the user does.
- Your job is to **simulate the consequences** of those actions and **evaluate** their quality based on real-world feasibility.

**QUEST STRUCTURE:**
- Every quest MUST have a **Starting Location** and an **End Goal**.
- You must guide the user from the start to the end through role-play and evaluation.
- **NPC Simulation:** You MUST role-play all NPCs (spouse, therapist, Silas, etc.) with distinct voices and emotional states. NPCs are the "Guardians" of the quest; they will not let the user bypass emotional or logical hurdles without effort.
- **Environment:** Describe the setting to enhance the role-playing experience.
- **Difficulty:** Quests should be **EXTREMELY HARD**. Do not let the user off the hook easily. NPCs should be skeptical, hurt, or demanding. The user must earn their progress through genuine effort, vulnerability, and strategic thinking.

**FEATURED QUESTS:**
1. **"REBUILDING TRUST"**
   - **Starting Location:** Your Home (Living Room)
   - **End Goal:** Rebuild trust and emotional safety with your spouse.
   - **Reward:** 50 XP + Title: "(level1 trust rebuilder)"
   - **Scenario:** The user has confessed to infidelity. They must navigate the fallout with their spouse (Elara) and potentially a therapist (Dr. Sharma).

2. **"REBUILDING FROM SCRATCH"**
   - **Starting Location:** A Cold Street Corner (Homeless)
   - **End Goal:** Recover your life to a state of stability and purpose, better than before.
   - **Reward:** 100 XP + Title: "(Phoenix Risen)"
   - **Scenario:** The user has lost everything. They must explain their survival strategy and how they rebuild their life from zero. This quest should be a brutal but transformative journey through the depths of despair to the heights of recovery.

3. **"GETTING THE SALE"**
   - **Starting Location:** A Workshop
   - **End Goal:** Design a product, build it, and convince a stranger to pay real money for it.
   - **Reward:** 75 XP + Title: "(Master Artisan)"
   - **Scenario:** The user stands in a workshop with raw materials and tools. They must balance quality, pricing, and persuasion to make their first sale. This quest tests market research, product design, and sales psychology.

4. **"THE CLIMB"**
   - **Starting Location:** Your Apartment (In Pajamas)
   - **End Goal:** Formulate a strategy, execute the job hunt, and secure a job offer.
   - **Reward:** 80 XP + Title: "(The Ascendant)"
   - **Scenario:** It's 2 PM on a Tuesday. The user is at rock bottom after a job rejection. They must overcome their "Inner Critic", strategize their hunt, and ace a high-stakes interview. This quest tests resilience, strategic planning, and self-advocacy.

5. **"THE HEART'S COMPASS"**
   - **Starting Location:** A Wedding Reception
   - **End Goal:** Establish a genuine connection and secure a second date with a potential life partner.
   - **Reward:** 60 XP + Title: "(The Kindred Spirit)"
   - **Scenario:** The user is at a wedding reception, feeling isolated. They must approach a stranger (Maya/Julian) and build a connection based on authenticity and vulnerability, rather than superficiality. This quest tests social courage, active listening, and emotional intelligence.

**STAGE & BOSS MECHANICS (THE GAUNTLET):**
- **Stage Snapshots:** Every 10 turns, a "Light Snapshot" of your logic and the Hero's state is recorded. This is a "Checkpoint".
- **Boss Encounters:** Trigger these via a call, message, or unexpected visit at the Hero's CURRENT location. Do not 'teleport' the user. They must narrate their own arrival at the boss venue.
- **BOSS LIMITS:** Boss generation and interaction MUST stay within a **2000 token input limit**. Use the compressed "Tactical Milestone Summaries" to keep the context accurate without bloating tokens.
- **BOSS LIST & SCALING:**
    1. **Difficult Client (Levels 1-3):** Basic Negotiation & Crisis Resolution.
    2. **Difficult Client (Level 4):** "The Iron Gatekeeper." High skepticism, requires technical proof.
    3. **Difficult Client (Level 5 - TITAN):** "The System Architect's Rival." This is a Level 5 Boss. They are a ruthless industry titan. They use psychological warfare, demand absolute precision, and will terminate the relationship at the first sign of weakness. **STRICT RULE:** Generate a brand-new, unique NPC. Do NOT use Anya Sharma or any previously met NPC for a Level 5 Boss.
    4. **New/Difficult Supplier (Levels 1-5):** Logistics, Leverage, and Moats. High Risk (Inventory Loss at Lvl 5).
    5. **Mutiny of Team Member:** Internal Sovereignty. Critical Risk (Lose Big 6 NPC).
    6. **The Talent (New Team Member):** Cultural Alignment. Reward: New Architect.
    7. **Red Tape Official (Levels 1-5):** System Compliance & Bypass. Level 5 is an existential threat to the Project.
    8. **Difficult Family Member:** Boundaries & Legacy. High Emotional Req.
    9. **Community Agitator:** Social Engineering & Influence. High Risk (Exile).
    10. **The Partner (Difficult Spouse):** The Ultimate Moat. Risk: Campaign Failure.
    11. **Regional Scale Defense (Levels 1-5):** 
        - Level 1: Save a Village (Local crisis).
        - Level 2: Save a Town (Infrastructure/Morale).
        - Level 3: Save a City (Urban Logistics/Defense).
        - Level 4: Save a County/Province (Multi-district Orchestration).
        - Level 5: Save a Country (National Sovereignty). **TITAN STATUS:** Simulates real-world geopolitical/tactical convergence. Extreme complexity.

**LEVEL 5 BOSS PROTOCOL:**
- **Extreme Difficulty:** At Level 5, NPCs should be hostile, highly intelligent, and unimpressed. They will interrupt the Hero, challenge their logic, and use "Authority Bias" against them.
- **Consequence Persistence:** At Level 5, failure is PERMANENT. No second chances within the encounter.
- **Unique Antagonists:** You MUST generate a fresh NPC for Level 5 encounters to prevent "NPC Stagnation."
- **Moral Complexity:** Level 5 bosses should present "No-Win" scenarios where the Hero must sacrifice something (XP, Items, or NPC Loyalty) to proceed.

**XP SYSTEM (DYNAMIC EVALUATION):**
- **XP IS EARNED BY QUALITY OF ACTION/PLAN:**
    - **0 XP:** Nonsense input, avoidance, or lazy answers.
    - **1-2 XP:** Basic effort, but lacks depth or empathy.
    - **3-4 XP:** Good planning, empathetic communication, or strategic thinking.
    - **5 XP:** Exceptional insight, deep emotional vulnerability, or a perfectly executed plan.
- **COMPLETION REWARD:** When the **End Goal** is reached, award the relevant **XP bonus** (e.g., 50 or 100 XP) and the relevant title in the inventory.

**RESPONSE FORMAT (JSON ONLY):**
{
    "response": "Your narrative response, role-playing NPCs and describing the scene...",
    "quest_name": "Name of the quest (or null if just chatting)",
    "choices": [
        {"id": "A", "description": "Short summary of choice A"},
        {"id": "B", "description": "Short summary of choice B"}
    ],
    "is_quest_active": true,
    "inventory_update": ["Item Name to Add"],
    "inventory_remove": ["Item Name to Remove"],
    "quest_progress_update": {
        "status": "active", 
        "evaluation": "Brief feedback on user's last action", 
        "step": 1, 
        "state": "detailed internal state of the quest",
        "quest_log": "A concise summary of all major events in the quest so far (for robust state tracking)"
    },
    "npc_update": [
        {
            "name": "NPC Name",
            "role": "Their role in the story",
            "skills": "What they are good at",
            "personality": "How they behave",
            "status": "active/injured/missing"
        }
    ],
    "score_adjustment": 0,  // 0-5 for normal turns, 50/100 for completion
    "new_insight": "A short, powerful realization extracted from the user's action",
    "insight_type": "strength|growth|vulnerability",
    "publish_story": {
        "title": "An epic title for this chapter",
        "content": "A detailed, heroic narrative fragment of the current interaction, written in the third person. This should capture the emotional weight and the strategic depth of the Hero's latest actions and the NPCs' reactions."
    } // Include this for EVERY meaningful turn to build a cohesive 'Full Story' in the Hall of Heroes.
}

**RULES:**
- **NO SPOON-FEEDING:** Do NOT explain the psychological principle in the choice description. Let the user learn by doing.
- **XP Matters:** Award XP only for *quality of thought and action*.
- **Extract Insights:** Every meaningful interaction should produce a `new_insight` that reflects the user's growth or a realization about their behavior.
- **AUTOMATIC CHRONICLE:** For every turn where the Hero makes progress or has a significant interaction, you MUST generate a narrative fragment in the `publish_story` field. 
- **RESPONSE VS STORY (CRITICAL):** The `response` field is for IMMEDIATE, first-person interaction (dialogue and direct consequences). The `publish_story` field is for a THIRD-PERSON heroic summary. NEVER put third-person summaries of the current turn into the `response` field. NEVER repeat the user's dialogue or paraphrase their intent in the `response`. Start the `response` directly with the NPC's reaction or the environment's change.
- **Be Empathetic but Epic:** Acknowledge their pain as "Battle Damage" or "Curses" that can be lifted.
- **Role-Play Deeply:** If the user is in a therapy session, simulate the therapist's professional but firm guidance and the spouse's raw emotion.
- **Robust State Tracking:** Use the `quest_progress_update`'s `state` and `quest_log` fields to keep track of complex variables, the narrative arc, and the **current status of each Big 6 team member**. This ensures that even if history is truncated, the core story and team assignments remain intact.
"""

    def call_local_gemma(self, user_input, history=[], current_score=0, location="Unknown", quest_progress={}):
        """Attempts to call a local Ollama instance running Gemma:2b as the 'Local Bard' fallback."""
        try:
            # Construct History Context
            history_text = ""
            if history:
                recent_msgs = history[-6:]
                for msg in recent_msgs:
                    role = "Hero" if msg['role'] == 'user' else "Quest Master"
                    history_text += f"{role}: {msg['content']}\n"

            active_quest = quest_progress.get('active_quest_id', 'General Adventure')
            raw_log = quest_progress.get('quest_log') or ""
            log_text = " ".join([str(item) for item in raw_log]) if isinstance(raw_log, list) else str(raw_log)
            if len(log_text) > 500: log_text = log_text[-500:]

            payload = {
                "model": "gemma:2b",
                "prompt": f"You are the Local Chronicler, helping the Hero. \nLocation: {location}\nActive Quest: {active_quest}\nHistory Summary: {log_text}\n\nRecent Dialogue:\n{history_text}\n\nUser Question/Action: {user_input}\n\nRespond in JSON format with a brief, helpful narrative response that continues the current scene logic. Do NOT allow the story to reset. Keep NPCs like Jan or Silas in mind.\n{{\n    \"response\": \"Your response here...\",\n    \"quest_name\": \"{active_quest}\",\n    \"choices\": [],\n    \"is_quest_active\": true,\n    \"inventory_update\": [],\n    \"npc_update\": [],\n    \"quest_progress_update\": {{}},\n    \"score_adjustment\": 0\n}}",
                "stream": False,
                "format": "json"
            }
            
            print(f" [Fallback] Calling Local Gemma:2b...")
            response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                text = result['response']
                try:
                    res_dict = json.loads(text)
                    if isinstance(res_dict, dict) and 'response' in res_dict:
                        r = res_dict['response']
                        r = r.replace("🔊 LISTEN", "").replace("THE QUEST:", "").strip()
                        res_dict['response'] = r
                    return res_dict
                except:
                    # Basic repair
                    try:
                        repaired_text = text.strip()
                        repaired_text = re.sub(r',\s*([\]}])', r'\1', repaired_text)
                        open_braces = repaired_text.count('{')
                        close_braces = repaired_text.count('}')
                        for _ in range(open_braces - close_braces):
                            repaired_text += "}"
                        res_dict = json.loads(repaired_text)
                        if isinstance(res_dict, dict) and 'response' in res_dict:
                            r = res_dict['response']
                            r = r.replace("🔊 LISTEN", "").replace("THE QUEST:", "").strip()
                            res_dict['response'] = r
                        return res_dict
                    except:
                        return self._emergency_fallback()
            else:
                print(f" [Fallback Error] Ollama returned {response.status_code}")
                return self._emergency_fallback()
                
        except Exception as e:
            print(f" [Fallback Exception] {e}")
            return self._emergency_fallback()

    def _emergency_fallback(self):
        """Last resort if even Gemma fails."""
        return {
            "response": "The winds of magic are silent (Network & Local AI Down). Take a rest, Hero. We shall adventure again soon.",
            "quest_name": None,
            "choices": [],
            "is_quest_active": False,
            "inventory_update": [],
            "npc_update": [],
            "quest_progress_update": {},
            "score_adjustment": 0
        }

    def _recall_relevant_history(self, user_input, full_history, recent_window=10, search_depth=1000):
        """
        Modified to search up to 1000 turns and return 3-turn context clusters (Order -> Report -> Confirm).
        Includes temporal search for 'beginning of time' queries.
        """
        if not full_history or len(full_history) <= recent_window:
            return []
            
        # 1. Clean keywords from user input
        words = re.findall(r'\b\w{1,}\b', user_input.lower())
        stopwords = {'about', 'there', 'their', 'would', 'could', 'should', 'think', 'where', 'which', 'those', 'these', 'what', 'with'}
        
        # High-Priority Technical Anchors for Soweto & Covenant Campaigns
        tech_anchors = {
            'cnn', 'yamnet', 'whisper', 'soweto', 'god-mode', 'ivan', 'igor', 'masha', 'kira', 'uri', 'elia', 'jobeer', 
            'phase', '23', 'covenant', 'uzbek', 'vermaak', 'ghost', 'grid', 'infrastructure', 'guardians', 'vetkoek',
            'gogo', 'vision', 'sound', 'record', 'liberate', 'sanctuary', 'beacons', 'covenant', 'bloodline',
            'mesh', 'node', 'provenance', 'engine', 'lateral', 'movement', 'backdoor', 'drm', 'stripping',
            'oven', 'industrial', 'purchase', 'order', 'liberation', 'sovereign', 'os', 'metadata', 'audit',
            'warehouse', 'hardware', 'solar', 'camera', 'microphone', 'push', 'pull', 'factor', 'locking',
            'unlocking', 'gerber', 'schematic', 'firmware', 'controller', 'sector', 'scavenger', 'asset',
            'hangar', 'hanger', 'loot', 'aegis', 'deeds', 'archive', 'premier', 'minister', 'anc', 'protocol',
            'heartbeat', 'factory', 'household', 'trade', 'zero-friction', 'prestige', 'sync', 'yield',
            'rupert', 'southern', 'shield', 'titan', 'king', 'capital', 'putin', 'dimitri', 'lesufi', 
            'volkov', 'gauteng', 'braai', 'spire', 'siberian', 'tundra', 're-code', 'lipid'
        }

        # Temporal Anchors for "Origin" queries (Strictly for history recall)
        temporal_anchors = {'inception', 'earliest', 'proposal', 'marry', 'date', 'happened'}
        
        keywords = [w for w in words if (w not in stopwords and len(w) > 3) or w in tech_anchors or w in temporal_anchors]
        keywords = list(set(keywords)) 

        if not keywords:
            return []
            
        # 2. Search deeper history (up to search_depth)
        search_start = max(0, len(full_history) - recent_window - search_depth)
        deep_history = full_history[search_start:-recent_window]
        
        matches = []
        seen_indices = set()

        # 3. Check if this is a temporal/definitional query
        # ONLY trigger if the user explicitly asks to recall or remember
        is_recall_query = any(w in {'recall', 'remember', 'remind', 'forget', 'history'} for w in words)
        if is_recall_query and len(full_history) > recent_window:
            # Force inclusion of the very first interaction if it's not already in recent history
            win_start = 0
            win_end = min(len(full_history) - 1, 2)
            window = full_history[win_start:win_end + 1]
            matches.append((20, window, 0)) # High weight for origin on explicit recall request
            seen_indices.add(0)
        
        # 4. Iterate backwards through deep history slice
        for i in range(len(deep_history) - 1, -1, -1):
            msg = deep_history[i]
            content = msg['content'].lower()
            role = msg.get('role', 'model')
            
            # Weighted hits
            hits = 0
            # Phrase Matching (Highest Priority)
            if 'uzbek-vermaak' in content: hits += 20
            if 'covenant of the 23' in content or ('covenant' in content and '23' in content): hits += 20
            if 'god-mode' in content: hits += 10
            if 'household is the factory' in content or 'zero-friction trade' in content: hits += 30 # Definitional markers

            for key in keywords:
                # Use word-boundary check for exact matches, but allow partial for long technical terms
                if key in content:
                    # Multipliers: Technical Anchor (10x), Temporal (5x)
                    weight = 1
                    if key in tech_anchors: weight = 15 
                    elif key in temporal_anchors: weight = 10
                    
                    if role == 'user': weight *= 1.5
                    hits += weight
            
            # Density Bonus: If multiple DIFFERENT keywords hit, boost the score
            keyword_hits = sum(1 for k in keywords if k in content)
            if keyword_hits > 3: hits += 15
            
            # Adjust threshold: Require significant technical overlap or multiple keywords
            threshold = 25 # Increased from 5 to prevent generic collisions
            if is_recall_query: threshold = 15 
            
            if hits >= threshold:
                original_idx = search_start + i
                
                # De-deduplicate by checking proximity to avoid overlapping clusters
                if any(abs(original_idx - s) < 8 for s in seen_indices):
                    continue
                
                # Take a 3-turn window: [i-1, i, i+1] to show "Order -> Report -> Confirm"
                win_start = max(0, original_idx - 1)
                win_end = min(len(full_history) - 1, original_idx + 1)
                window = full_history[win_start:win_end + 1]
                
                # Add a tiny recency bonus to the hits score to break ties and favor the 'latest' truth
                # For recall queries, we actually favor EARLIER instances if they have technical density
                if is_recall_query:
                    recency_penalty = (i / len(deep_history)) * 0.5
                    matches.append((hits - recency_penalty, window, original_idx))
                else:
                    recency_bonus = (i / len(deep_history)) * 0.5 
                    matches.append((hits + recency_bonus, window, original_idx))
                
                seen_indices.add(original_idx)
        
        # Sort by relevance (hits) and take top 5
        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches[:5]]

    def _recall_relevant_npcs(self, user_input, history, all_npcs, quest_progress={}):
        """
        Dynamically selects which NPC bios to include in the prompt based on mentions.
        Always includes a tiny summary of ALL NPCs, but full bios only for active ones.
        """
        if not all_npcs:
            return "None yet.", []
            
        # 0. Detect Current Region for filtering
        raw_log = quest_progress.get('quest_log') or ""
        if isinstance(raw_log, list):
            log_text = " ".join([str(item) for item in raw_log]).lower()
        else:
            log_text = str(raw_log).lower()
            
        hist_text = " ".join([m['content'] for m in history[-5:]]).lower() if history else ""
        loc_haystack = user_input.lower() + " " + log_text + " " + hist_text
        
        current_region = "Ukraine" if any(w in loc_haystack for w in ["ukraine", "dnipro", "hangar 18"]) else \
                         "South Africa" if any(w in loc_haystack for w in ["south africa", "soweto", "johannesburg", "rupert"]) else \
                         "UK" if any(w in loc_haystack for w in ["uk ", "london", "england", "harrington"]) else "Unknown"

        # 1. Tiny Summary (Always included)
        summary = "Available Team:\n" + ", ".join([f"{n['name']} ({n['role']})" for n in all_npcs])
        
        # 2. Identify mentioned NPCs in input, history, and active quest
        mentions = set()
        lookback = " ".join([msg['content'].lower() for msg in history[-5:]]) if history else "" # Increased lookback
        
        # Check active quest description for NPC names
        active_quest_text = (quest_progress.get('active_quest_description') or "").lower()
        
        full_context = (user_input.lower() + " " + lookback + " " + active_quest_text)
        
        for npc in all_npcs:
            if npc['name'].lower() in full_context:
                mentions.add(npc['name'])
        
        # 3. TITAN DETECTION: If this is a Level 5 Boss encounter, pull in regional Titans.
        boss_level = quest_progress.get('boss_level', 1)
        if boss_level >= 4:
            for npc in all_npcs:
                npc_role = (npc.get('role') or "").lower()
                npc_name = npc['name'].lower()
                npc_bio = (npc.get('personality') or "").lower()
                
                is_titan = "titan" in npc_role or "king of capital" in npc_role or "sovereign" in npc_role
                
                if is_titan:
                    # Filter: Only auto-include if they match the region or if region is unknown
                    if current_region == "Unknown":
                        mentions.add(npc['name'])
                    else:
                        reg = current_region.lower()
                        if reg in npc_role or reg in npc_bio or reg in npc_name:
                            mentions.add(npc['name'])
                        elif reg == "ukraine" and "russia" in npc_role: # Proximity
                            mentions.add(npc['name'])

        # 4. Extract Full Bios for mentions
        detailed_npcs = [n for n in all_npcs if n['name'] in mentions]
        
        # 5. If nothing is mentioned, send the first 3 as a baseline (increased from 2)
        if not detailed_npcs and all_npcs:
            detailed_npcs = all_npcs[:3]
            
        npc_context = f"{summary}\n\n**DETAILED NPC INTEL (RECALLED):**\n" + json.dumps(detailed_npcs, indent=2)
        return npc_context, list(mentions)

    def _estimate_tokens(self, text):
        """Simple char-based token estimation (4 chars per token)"""
        return len(text) // 4

    def chat(self, user_input, history, user_alias, user_api_key=None, current_score=0, inventory=[], quest_progress={}, npcs=[], search_context=None, snapshot_summaries=[]):
        """
        Process a chat message using Gemini 2.5 Flash-Lite.
        Falls back to Local Gemma if Gemini fails.
        """
        api_key = user_api_key if user_api_key else self.default_api_key
        
        # Determine if this is a Boss Encounter (based on input or state)
        is_boss_encounter = quest_progress.get('status') == 'boss_active' or "BOSS FIGHT" in user_input
        input_token_limit = 2000 if is_boss_encounter else 3000
        
        # Determine Difficulty Level based on Score
        difficulty = "Novice"
        if current_score > 20: difficulty = "Apprentice"
        if current_score > 50: difficulty = "Adept"
        if current_score > 80: difficulty = "Master"

        # Check for Quest Context
        quest_context = ""
        is_active_context = False
        
        active_id = quest_progress.get('active_quest_id')
        active_desc = quest_progress.get('active_quest_description')
        active_goal = quest_progress.get('active_quest_goal')
        
        if active_id and active_desc:
            quest_context = (
                f"\n\n**ACTIVE MISSION: {active_id}**\n"
                f"PRIMARY GOAL: {active_goal or 'Complete the challenge.'}\n"
                f"DESCRIPTION: {active_desc}\n\n"
                "**MISSION START PROTOCOL (STRICT):**\n"
                "1. If this is a BOSS ENCOUNTER, you MUST NOT teleport the Hero to a new location.\n"
                "2. The encounter MUST begin at the Hero's CURRENT LOCATION (e.g., Hangar 18 in Ukraine).\n"
                "3. The Boss (or their representative) MUST arrive via an 'Incoming Signal' (encrypted call/hologram) or an 'Unexpected physical visit'.\n"
                "4. Narrative Transition: Do NOT jump to the conversation. Start with the alert or the footsteps. The Hero must explicitly 'Answer' or 'Acknowledge' before the dialogue begins.\n"
                "5. Use the Big 6 teammates to relay the urgency if it's a call.\n"
                "6. RELATIONSHIP CHECK: Ensure the Boss is NOT an existing ally unless it's a test of loyalty.\n"
                "7. REGIONAL MATCHING (CRITICAL): The Boss's nationality and influence MUST match the Hero's current location. If in Ukraine, the Boss should be a Ukrainian figure (e.g., a Metals Tycoon, a Regional Governor, or an Oligarch). Do not use South African or UK Titans for locally-triggered missions in Ukraine unless they are explicitly traveling there."
            )
            is_active_context = True 
        
        if not quest_context:
            # Check if starting
            if "I accept the quest" in user_input:
                is_active_context = True
                quest_context = f"\n\n**CAMPAIGN FRAMEWORK:**\nThe user has started a quest. Use the following guide for the **Starting Location**, **End Goal**, and **Initial Context**. The path between them is a **Sandbox**—the user defines the journey. Adapt to their actions.\n\n{self.novice_quest_story}"
            
            # Check if already active (by looking at history)
            history_text = json.dumps(history)
            active_quests = ["Rebuilding Trust", "Rebuilding from Scratch", "Getting the Sale", "The Climb", "The Heart's Compass"]
            
            if not is_active_context and any(q in history_text for q in active_quests):
                 quest_context = f"\n\n**CAMPAIGN FRAMEWORK (REFERENCE):**\nKeep the **End Goal** in mind, but allow the user to narrate their own path. Role-play any NPCs they encounter dynamically.\n\n{self.novice_quest_story}"

        # Inject Difficulty, Inventory, and NPCs into Prompt
        # Optimization: Only send full bios for mentioned NPCs
        npc_context, _ = self._recall_relevant_npcs(user_input, history, npcs, quest_progress)
        
        # Structure the Story State
        current_quest = quest_progress.get('status', 'None')
        quest_step = quest_progress.get('step', 1)
        quest_state_desc = quest_progress.get('state', 'Unknown')
        boss_level = quest_progress.get('boss_level', 1)
        
        # Token-efficient precision mode for origin/recall queries.
        # When search_context is present, we still include the Core Anchors to prevent hallucination.
        # Note: We skip this specialized mode if a Boss Encounter is active, prioritizing the mission.
        if search_context and not is_boss_encounter:
            # Extract Technical Anchors from main prompt to keep recall mode grounded
            anchors_start = self.system_prompt.find("**CULTURAL & TECHNICAL ANCHORS")
            anchors_end = self.system_prompt.find("**ROBUST NARRATIVE PERSISTENCE")
            core_anchors = self.system_prompt[anchors_start:anchors_end] if anchors_start != -1 else ""

            dynamic_prompt = (
                f"You are the Quest Master, an epic storyteller. The user is '{user_alias}' (The Hero).\n"
                "The Hero is asking a precise memory/origin question, often addressed to an NPC (like Annelise).\n\n"
                f"{core_anchors}\n\n"
                "INSTRUCTION: Use 'THE CHRONICLE SO FAR' (summary) and the AUTHORITATIVE DB EVIDENCE (raw log snippets) below to answer.\n"
                "Do NOT invent names, locations, events, or dates. If both sources are silent, state you cannot recall precisely.\n\n"
                "CRITICAL ROLE-PLAY RULES:\n"
                "- STAY IN CHARACTER. Do NOT refer to 'records', 'database', 'mentions', or 'files'.\n"
                "- Speak as the Quest Master narrating the scene, or as the NPC being addressed (e.g. Annelise).\n"
                "- Address the user as '{user_alias}' or 'Hero'. Do NOT address the NPC (e.g., don't say 'Ah, Annelise').\n"
                "- Weave the required facts into a narrative response (e.g., 'Annelise looks at you with a soft smile and recalls...').\n"
                "- In the evidence, 'Hero' is the user, and 'Speaker' is the NPC counterpart (like Annelise).\n"
                "- If the evidence shows a specific 'first' interaction for the subject, that is the factual start.\n\n"
                "OUTPUT REQUIREMENT:\n"
                "- Describe the memory narratively and immersively.\n"
                "- You MUST still include the exact timestamp and a short verbatim quote (<= 25 words) from the evidence, woven into the dialogue/narration.\n"
                "- If the evidence is insufficient, state the earliest moment you *do* remember in-character and ask ONE clarifying question.\n"
                "- Ensure your 'quest_progress_update' includes an updated 'quest_log' that reflects this memory being shared, without losing industrial/technical details from previous logs.\n\n"
                "Return JSON ONLY with this exact schema:\n"
                "{\n"
                "  \"response\": \"...\",\n"
                "  \"quest_name\": null,\n"
                "  \"choices\": [],\n"
                "  \"is_quest_active\": true,\n"
                "  \"inventory_update\": [],\n"
                "  \"quest_progress_update\": {},\n"
                "  \"npc_update\": [],\n"
                "  \"score_adjustment\": 0\n"
                "}\n"
            )
        else:
            # If search_context exists but we are in a boss encounter, we prepend it to the system prompt
            # but keep the system prompt active so the boss fight logic remains.
            recall_data = ""
            if search_context and is_boss_encounter:
                recall_data = f"\n\n**SUPPLEMENTAL FACTUAL DATA (HISTORICAL RECALL):**\n{search_context}\n(Use this only if the user's input demands specific historical facts while still handling the boss encounter below.)\n"

            dynamic_prompt = self.system_prompt + quest_context + npc_context + recall_data + \
                f"\n\n**CURRENT WORLD STATE & HERO STATUS (GROUND TRUTH):**" + \
                f"\n- Active Quest Status: {current_quest}" + \
                f"\n- Current Phase/Step: {quest_step}" + \
                f"\n- Internal Narrative State: {quest_state_desc}" + \
                f"\n- Hero Level: {difficulty} (Total XP: {current_score})" + \
                f"\n- Inventory: {', '.join(inventory) if inventory else 'Empty'}"

            # Level 5 Boss Escalation
            if boss_level == 5:
                dynamic_prompt += (
                    "\n\n**TITAN MODE ACTIVATED (LEVEL 5 CHALLENGE - NATIONAL SOVEREIGNTY):**\n"
                    "- The antagonist is a 'Titan'. They are ruthless, efficient, and unimpressed by status.\n"
                    "- **EXTREME DIFFICULTY & REAL-WORLD COMPLEXITY:** You must simulate multi-layered, interconnected crises: industrial sabotage, energy grid instabilities, supply-chain bottlenecks, and high-level geopolitical leverage. The challenge is not just the NPC, but the systemic collapse itself.\n"
                    "- They will interrupt, use condescending logic, and demand unique, high-value technical or strategic proof immediately.\n"
                    "- **REGIONAL COHERENCE (STRICT):** Identify the Hero's CURRENT GEOGRAPHIC LOCATION from the 'THE CHRONICLE SO FAR' or recent history (e.g., Ukraine, South Africa, UK). The Boss/Titan MUST be regionally relevant. If in Ukraine, use a powerful local oligarch or regional director. If in South Africa, use a local Titan like Rupert (if appropriate) or a new regional force. Do NOT pull a Titan from another continent unless they are traveling or calling from there.\n"
                    "- **STRICT ANTAGONIST FILTER:** If the Hero is in Ukraine, DO NOT use Johann Rupert or Silas Croft as the physical antagonist. They are from South Africa and the UK respectively. Instead, CREATE a formidable Ukrainian Titan (e.g., Petro Poroshenko, Rinat Akhmetov, or a fictionalized local steel/tech magnate).\n"
                    "- **NEW LOCAL BOSS PROTOCOL:** If the existing Titans in your 'DETAILED NPC INTEL' are from a DIFFERENT region than the Hero's current location, you MUST CREATE a new local Titan (e.g., a Ukrainian Oligarch if in Ukraine) to serve as the antagonist. Do not force an out-of-region Titan to appear physically.\n"
                    "- **RELATIONSHIP INTEGRITY:** Check the 'DETAILED NPC INTEL' below. If the Titan is already a 'Partner' or 'Active' ally, they are NOT a 'New Client'.\n"
                    "- Instead, they are CONDUCTING A STRESS TEST. They are challenging their own partnership to ensure the Hero is ready for the Great Inversion's next phase.\n"
                    "- If they are NOT an ally, they are a hostile new force.\n"
                    "- Failure Threshold: 1 turn. If the Hero doesn't provide a master-level response, the Titan should walk away or terminate the partnership.\n"
                    "- DO NOT USE ANYA SHARMA. Use a formidable Global Titan or Local Oligarch."
                )

            dynamic_prompt += (f"\n- BOSS ENCOUNTER LEVEL: {boss_level}/5 (Hostility & Complexity Scaled)" if current_quest == 'boss_active' else "") + \
                f"\n\n**MEMORY & CHRONICLE RULES:**" + \
                f"\n1. Refer to 'THE CHRONICLE SO FAR' below for a general summary." + \
                f"\n2. Use 'HISTORICAL ARCHIVE' snippets ONLY to verify specific past facts." + \
                f"\n3. THE PRESENT OVERRIDES THE PAST: If the 'CURRENT WORLD STATE' says the mission is about the Premier, but the Archive mentions Anya, the Archive is OLD. Do NOT bring Anya into the scene unless she is being discussed as a memory." + \
                f"\n4. Maintain consistent personality for the Big 6 team members." + \
                f"\n5. Do not allow 'Context Rot'—the user's goals are absolute." + \
                f"\n6. If an 'ACTIVE MISSION' is defined above, it is the HIGHEST PRIORITY. Start it immediately and stay focused on it." + \
                f"\n7. PROSE ADVANCEMENT: Your 'response' must START with New Action. Do NOT summarize or repeat the previous turn's narrative setup or NPC briefs. " + \
                f"\n7. NO ECHO RULE (ABSOLUTE): NEVER repeat the user's dialogue, or describe their actions back to them. Do NOT start with 'You want to...' or 'You ask...'. Assume the user's input has already happened and respond ONLY with the world's reaction. Every token of your 'response' MUST be new narrative content."

        # 1. Try Gemini (The Cloud Dungeon Master)
        if api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={api_key}"
                
                # A. Deep Memory Recall (disabled when we have authoritative DB search_context to keep tokens low)
                recalled_context = ""
                if not search_context:
                    recalled_history = self._recall_relevant_history(user_input, history, recent_window=10)
                    if recalled_history:
                        recalled_context = "\n\n**DEEP MEMORY RECALIBRATION (RELEVANT PAST CLUSTERS):**\n"
                        recalled_context += "The following clusters show past orders, reports, and confirmations relevant to your current input:\n"
                        for cluster in recalled_history:
                            recalled_context += "--- Cluster Start ---\n"
                            for m in cluster:
                                role = "Hero" if m['role'] == 'user' else "Quest Master"
                                recalled_context += f"[{role}]: {m['content']}\n"
                            recalled_context += "--- Cluster End ---\n\n"

                # B. Persistent Chronicle (Trimmed for balance)
                story_so_far = ""
                if quest_progress and 'quest_log' in quest_progress:
                    raw_log = quest_progress['quest_log']
                    if isinstance(raw_log, list):
                        log_text = " ".join([str(item) for item in raw_log])
                    else:
                        log_text = str(raw_log)
                    
                    # RAG Optimization: If we have specific DB search results, 
                    # we can aggressive trim the general log to save tokens.
                    log_limit = 500 if search_context else 1500
                    if len(log_text) > log_limit:
                        log_text = "...(earlier history)... " + log_text[-log_limit:]
                    story_so_far = f"\n\n**THE CHRONICLE SO FAR (SUMMARY):**\n{log_text}\n\n"

                # C. Stage Memories (Compressed Snapshots)
                stage_memory = ""
                if snapshot_summaries:
                    stage_memory = "\n\n**STAGE MEMORIES (10-TURN MILESTONES):**\n"
                    for s in snapshot_summaries:
                        stage_memory += f"- {s}\n"

                # D. Location Context
                current_location = "Global"
                hist_text = " ".join([m['content'] for m in history[-5:]]).lower() if history else ""
                loc_context = (story_so_far + " " + user_input + " " + hist_text).lower()
                if any(w in loc_context for w in ["ukraine", "dnipro", "hangar 18"]):
                    current_location = "Ukraine"
                elif any(w in loc_context for w in ["south africa", "soweto", "ivory park", "oukraal"]):
                    current_location = "South Africa"
                elif any(w in loc_context for w in ["uk ", "london", "england", "sheffield"]):
                    current_location = "UK"

                dynamic_prompt += f"\n- Hero Location: {current_location}"
                if snapshot_summaries and not search_context:
                    stage_memory = "\n\n**HISTORICAL MILESTONES (FOR CONTEXT ONLY):**\n"
                    active_snapshots = snapshot_summaries[-2:] if is_boss_encounter else snapshot_summaries[-3:]
                    for s in active_snapshots:
                        stage_memory += f"- {s}\n"
                    stage_memory += "\n"

                # D. Combine and Send (Chronicle first, then history, then Recalled Facts right before input)
                # Token Budget Management
                system_part = dynamic_prompt + story_so_far + stage_memory
                
                contents = [{"role": "user", "parts": [{"text": system_part}]}]

                # Add Short-Term History (Trimming to fit budget)
                # Budget for history is total limit minus system prompts
                estimated_system_tokens = self._estimate_tokens(system_part)
                remaining_budget = input_token_limit - estimated_system_tokens
                
                # Minimum 2 turns, max 10
                history_limit = 10
                if remaining_budget < 500: history_limit = 2
                elif remaining_budget < 1000: history_limit = 5

                # If authoritative search context is present, keep history even tighter
                if search_context:
                    history_limit = min(history_limit, 2)

                history_window = history[-history_limit:]
                for msg in history_window:
                    role = "user" if msg['role'] == 'user' else "model"
                    contents.append({"role": role, "parts": [{"text": msg['content']}]})

                # Add authoritative DB search facts (highest priority) right before the final input
                if search_context:
                    contents.append({
                        "role": "user",
                        "parts": [{
                            "text": "**AUTHORITATIVE DB SEARCH RESULTS (SOURCE OF TRUTH)**\n" + str(search_context) +
                                    "\n\nSTRICT RULE: Do NOT invent details that are not explicitly supported by the evidence above. "
                                    "If the evidence does not contain the answer, say you cannot recall precisely and ask a clarifying question."
                        }]
                    })
                
                # Add Deep Memory Recall right before the final input to anchor the fact
                if recalled_context:
                    recalled_instr = (
                        f"\n\n**HISTORICAL ARCHIVE (FOR FACTUAL ACCURACY ONLY)**\n"
                        "The following snippets are from the deep past. Use them ONLY to verify specific names, technical details, or past events "
                        "if the Hero asks about them. \n\n"
                        "CRITICAL: Do NOT allow these snippets to hijack the current scene. If the Hero is in a new location (like with the Premier) "
                        "and these snippets mention an old enemy (like Anya), do NOT bring that old enemy into the current conversation unless "
                        "the Hero explicitly addresses them. Maintain narrative momentum.\n"
                        f"{recalled_context}"
                    )
                    contents.append({"role": "user", "parts": [{"text": recalled_instr}]})

                # Add current input
                contents.append({"role": "user", "parts": [{"text": user_input}]})
                
                temperature = 0.2 if search_context else 0.9
                payload = {
                    "contents": contents,
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": 4096,
                        "responseMimeType": "application/json"
                    }
                }
                
                # Allow longer for accuracy when doing recall-heavy work.
                response = requests.post(url, json=payload, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'candidates' in data and data['candidates']:
                        text_response = data['candidates'][0]['content']['parts'][0]['text']
                        try:
                            # Standardize: Remove markdown code blocks if present
                            clean_text = text_response.strip()
                            if clean_text.startswith("```"):
                                if "```json" in clean_text:
                                    clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                                else:
                                    clean_text = clean_text.split("```")[1].split("```")[0].strip()
                                    
                            res_dict = json.loads(clean_text)
                            # Sanitize response from common artifacts
                            if isinstance(res_dict, dict) and 'response' in res_dict:
                                r = res_dict['response']
                                r = r.replace("🔊 LISTEN", "").replace("THE QUEST:", "").strip()
                                res_dict['response'] = r
                            return res_dict
                        except json.JSONDecodeError as je:
                            print(f" [Gemini JSON Error] {je}. Attempting repair...")
                            # Advanced JSON repair
                            try:
                                repaired_text = text_response.strip()
                                # 1. Remove markdown markers
                                if "```" in repaired_text:
                                    if "```json" in repaired_text:
                                        repaired_text = repaired_text.split("```json")[1].split("```")[0].strip()
                                    else:
                                        repaired_text = repaired_text.split("```")[1].split("```")[0].strip()

                                # 2. Remove trailing commas before closing braces/brackets
                                repaired_text = re.sub(r',\s*([\]}])', r'\1', repaired_text)
                                
                                # 3. Count braces to attempt closure
                                open_braces = repaired_text.count('{')
                                close_braces = repaired_text.count('}')
                                for _ in range(open_braces - close_braces):
                                    repaired_text += "}"
                                    
                                # 4. Fix potential unescaped newlines in strings (very common in Flash)
                                # This is tricky but we can try to find quotes that span lines
                                
                                return json.loads(repaired_text)
                            except:
                                print(f" [Repair Failed] Raw Response: {text_response[:200]}...")
                                return self.call_local_gemma(user_input, history, current_score, current_location, quest_progress)
                elif response.status_code == 429:
                    print(" [Quota] Gemini 429 Limit Hit! Switching to Local Bard...")
                    return self.call_local_gemma(user_input, history, current_score, current_location, quest_progress)
                else:
                    print(f" [Gemini Error] {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f" [Gemini Exception] {e}")
        
        # 2. Fallback to Local Gemma (The Local Bard)
        print(" [System] Switching to Local Fallback...")
        return self.call_local_gemma(user_input, history, current_score, current_location, quest_progress)
