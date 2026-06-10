# SDOH-Chat Project Analysis: File Structure & Feature Set

## 1. Exact File Structure
```text
SDOH-CHAT/
├── agent_forge.py          # Integrity Forge (Agent 1) Logic
├── agent_quest.py          # Fantasy Quest Master (Agent 2) Logic
├── bootstrap_summaries.py   # Utility for historical context bootstrapping
├── check_progress.py       # Progress evaluation scripts
├── cloudflared_config.yml   # Tunnel configuration for remote access
├── config.ini               # Central configuration (API keys, models, DB paths)
├── flask_app.py            # Main entry point for the Flask server
├── local_tts.py            # Local Text-to-Speech integration (Whisper/Gemma fallback)
├── NOVICE_QUEST_STORY.md    # Reference narrative for the Quest Master
├── Quest_Master_Interactions_Jobeer_Full.md # Dataset/Log of interactions
├── QUEST_MECHANICS_PLAN.md  # Design document for XP and Stage mechanics
├── README.md                # Project overview
├── requirements.txt         # Python dependencies
├── run.py                   # Convenience script to start the server
├── backend/
│   ├── auth_utils.py       # Authentication helper functions
│   ├── db.py               # Database initialization
│   ├── extensions.py       # Flask extensions (SQLAlchemy)
│   ├── integration.py      # Third-party service integration
│   ├── models.py           # Database models (User, Message, Quest, NPC, etc.)
│   ├── schemas.py           # Data validation schemas
│   ├── utils.py            # General utility functions
│   └── routes/
│       ├── agents.py       # API endpoints for AI Agents (Forge & Quest)
│       ├── auth.py         # Login/Registration endpoints
│       ├── chat.py         # Standard messaging endpoints
│       ├── moderation.py   # AI & Human moderation routes
│       ├── sdoh_auth.py    # specific SDOH auth logic
│       ├── sdoh_contacts.py# Contact management
│       ├── sdoh_groups.py  # Group management
│       ├── sdoh_messages.py# Messaging system
│       ├── social.py       # Social features (referrals, invites)
│       └── voice.py        # Voice note handling
├── frontend/
│   ├── dashboard.html      # Main user interface
│   ├── index.html          # Landing/Login page
│   ├── css/
│   │   └── dashboard.css   # Main styles
│   └── js/
│       └── modules/
│           ├── api.js      # Backend API wrapper
│           ├── chat.js     # Chat UI logic
│           ├── config.js   # Client-side configuration
│           ├── contacts.js  # Contact UI logic
│           ├── forge.js    # Forge Agent UI integration
│           ├── main.js     # App initialization
│           ├── tts.js      # Text-to-speech UI logic
│           ├── ui.js       # General UI helpers
│           ├── utils.js    # Client-side utilities
│           └── voice_input.js # Voice recording logic
└── data/
    └── nas_dicom_files.txt  # Placeholder/Reference data
```

---

## 2. Feature Comparison: Integrity Forge vs. Quest Master

| Feature | Integrity Forge (Agent 1) | Quest Master (Agent 2) |
| :--- | :--- | :--- |
| **Persona** | Wise, philosophical mentor ("The Blacksmith"). | Gritty Dungeon Master ("Master of the Invisible"). |
| **Core Goal** | Challenge thinking, hammer out ideas, teach values. | Skill transfer via immersive real-world simulations. |
| **Logic Mode** | **Reflective Mode:** Direct, direct, value-added feedback. | **Sandbox Mode:** Dynamic NPC roleplay & consequence engine. |
| **Narrative Style**| Metaphors of fire, iron, and growth. | Visceral, sensory descriptions of "Realms" & "Monsters". |
| **XP System** | 1-5 XP for vulnerability/insight; 10 XP for breakthroughs. | Goal-based; 50-100 XP for quest completion + Titles. |
| **Memory Sync** | Last 20 turns in `forge_history`. | Deep Recall (1000 turns) + Authoritative DB Evidence. |
| **Fallback** | Rule-based "Offline Forge" + Gemma 2b. | Local Gemma 2b "Local Bard" fallback. |

### Narrative Versioning (Quest Master Phases)
The Quest Master supports distinct "Versions" of narrative world-building:
- **REALISM MODE:** Strictly enforces real-world physics and consequences (Default).
- **FANTASY/SCIFI MODE:** Allows magic/tech but enforces internal narrative consistency.
- **PHASE 1 (SOWETO):** Focus on infrastructure liberation and "God-Mode" edge-node networking.
- **PHASE 2 (COVENANT OF THE 23):** Focus on the "Uzbek-Vermaak Protocol", heritage preservation, and sovereign dynasty building.

---

## 3. Quest Agent Search Robustness
The search logic is **Highly Robust**, utilizing a three-layer "Triangulation" approach:

1.  **Authoritative DB Recall:**
    *   Triggered by "Origin" queries (e.g., "When did we first meet?").
    *   Regex-based detection scans for met, talked, first, etc.
    *   Pulls **15-message windows** (5 before, 10 after) around keyword matches directly from the database (up to 1000 messages deep).
    *   Explicitly instructs the AI: "Source of Truth - do not invent names."

2.  **In-Memory Deep Memory Recall:**
    *   Keyword-based search across the last 1000 turns.
    *   **Weighting Engine:** Technical Anchors (5x), Temporal Anchors (3x), and User Messages (2x) are prioritized.
    *   Returns **3-turn context clusters** (Order -> Report -> Confirm) rather than single messages, preserving dialogue flow.

3.  **NPC Bio Retrieval:**
    *   Dynamically injects full bios only for NPCs mentioned in the last 2 turns, keeping context lean while maintaining character consistency.

---

## 4. Token Usage & Context Management
The system is built for **Gemini 2.5 Flash-Lite**, optimizing for low-latency and context stability.

*   **Input Token Limits:**
    *   **Standard:** 3,000 tokens.
    *   **Boss Encounters:** 2,000 tokens (tightens logic for high stakes).
*   **Budgeting Strategy:**
    1.  **System Prompt + Chronicle:** Primary "Mission Statement" and high-level summary.
    2.  **Stage Memory:** Last 3-5 "snapshots" (10-turn summaries) are added.
    3.  **Dynamic History:** Remaining budget is filled with message history (min 2, max 10 turns).
    4.  **Authoritative Evidence:** If a recall query is active, evidence snippets are placed directly before the final user input to maximize attention weight.
*   **Estimation:** The system uses a character-based estimator (~4 chars/token) to pre-trim history before sending to the API, preventing truncation errors.
