# Implementation Plan: Quest Stage & Boss Mechanics

## 1. Problem Statement
The Quest Agent is currently overwhelmed by ~800 turns of history, leading to "Broken RAG" where facts are lost or context rot occurs. To improve accuracy and introduce gameplay depth, we will implement **Stage Mechanics** (checkpoints) and **Boss Mechanics** (scaling challenges).

## 2. Stage Mechanics: Turn-Based Snapshots
We will implement an automated "Checkpoint" system to ensure the game state is preserved and can be used for deep memory grounding.

### 2.1 Technical Implementation
- **New Database Model:** `QuestSnapshot`
    - `user_id` (String)
    - `turn_number` (Integer)
    - `state_data` (Text/JSON): Complete snapshot of `inventory`, `quest_progress` (including `quest_log`), `npc_data`, and `integrity_score`.
    - `timestamp` (DateTime)
- **Snapshot Trigger:** 
    - A turn counter will be maintained in the `User.quest_progress`.
    - Every **10 turns**, the backend will automatically serialize the current state and save it to `QuestSnapshot`.
- **Utility:** 
    - Allows a "Redo" function for Boss Fights without losing the entire campaign.
    - Provides a "Grounding Point" for RAG. If keywords aren't found in recent history, we can pull the latest 10-turn snapshot summary.

## 3. Boss Mechanics: Scaling Encounters
Bosses will be high-stakes, multi-turn interactions that test specific skills learned during the "Novice" phases.

### 3.1 Boss Hierarchy & Scaling
Each boss scales in Prerequisites (XP/Items), Risk (XP loss/Status), and Rewards.

| Order | Boss Title | Skill Tested | Reward | Risk |
|-------|------------|--------------|--------|------|
| 1 | **Difficult Client (v1)** | Basic Negotiation | 20 XP + "Satisfied Client" | -5 XP |
| 2 | **Difficult Client (v2)** | Conflict Resolution | 40 XP + "Preferred Partner" | -10 XP |
| 3 | **New Supplier** | Trust Building | 30 XP + "Supply Chain Unlocked" | Delay in Quest |
| 4 | **Difficult Supplier** | Leveraged Negotiation | 50 XP + "Resource Moat" | Loss of Inventory |
| 5 | **Mutiny of Team Member** | Leadership & MOATs | 70 XP + "Ubreakable Loyalty" | Loss of a Big 6 NPC |
| 6 | **New Team Member** | Strategic Recruitment | 40 XP + "New Architect" | Hiring "The Saboteur" |
| 7 | **Red Tape Official** | System Navigation | 80 XP + "Sovereign Status" | Legal Shut Down |
| 8 | **Difficult Family Member**| Boundary Setting | 60 XP + "Legacy Clarity" | Emotional Damage (Debuff) |
| 9 | **Community Agitator** | Social Engineering | 90 XP + "District Founder" | Public Reputation Loss |
| 10 | **Difficult Spouse** | Ultimate Covenant | 150 XP + "Dynasty Founder" | Game Over / Divorce |

### 3.2 Interaction Protocol
- **Boss Encounter Mode:** When a Boss is triggered, the AI receives a specialized "Boss Prompt" that increases hostility and technical/emotional requirements for success.
- **Prerequisites:** Bosses 5-10 require specific items in `inventory` (e.g., "Provenance Engine" for Red Tape, "Trust Topology" for Mutiny).

## 4. Fixing "Broken RAG" & Context Rot (2000 Token Optimization)
To keep input tokens at a **strict maximum of 2000 tokens** while ensuring accuracy:

### 4.1 Robust Indexing & Stage Memory
1.  **Tier 1: Recent Context (Last 5 Turns):** Full detail of the current interaction (~800 tokens).
2.  **Tier 2: Current World State:** The most recent snapshot summary for immediate continuity (~400 tokens).
3.  **Tier 3: Semantic Stage Memory:** Up to 3 historical snapshots retrieved via **Tag-Based Semantic Search** (NPCs, Storylines, Tech) (~600 tokens).
4.  **Tier 4: Authoritative DB Snippets:** Precise keyword matches for dates/names (~200 tokens).

### 4.2 Stage Compression & Indexing Logic
- Every 10 turns, the Quest Master MUST generate a **"Robust Stage Index"**.
- This includes a **Tactical Summary** and a set of **Indexing Tags** (NPCs, items, events).
- The Retrieval Engine matches keywords from the user's input against these tags to pull "Lost Memories" from Turn 1 to Turn 1000 without bloating the prompt.

## 5. Next Steps
1.  **Modify `backend/models.py`** to include `QuestSnapshot`.
2.  **Update `backend/routes/agents.py`** to handle turn counting and snapshot triggering.
3.  **Update `agent_quest.py`** system prompt to understand "Boss Encounters" and use Snapshot Summaries.
4.  **Implement "Redo" Logic** (Optional/Phase 2).
