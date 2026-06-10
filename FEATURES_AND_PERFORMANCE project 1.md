# SDOH-Chat Feature & Performance Report

## 1. Feature Analysis: Base vs. V7 (Current)

| Feature | Base Version (Legacy) | V7 / Current Branch |
| :--- | :--- | :--- |
| **Data Layer** | `sdoh.db` (Standard Auth) | `sdoh_chat_v7.db` (NPC Persistence) |
| **Logic Engine** | Basic Q&A / Chat | Multi-Agent "Big 6" Coordination |
| **RAG** | Simple history lookup | **Authoritative Double-Anchor Search** |
| **Security** | PIN-based login | Ghost-Protocol & Legacy Metadata Stripping |
| **Narrative** | Linear conversation | **Open-World Sandbox Simulation** |
| **NPCs** | Static personalities | Dynamic `integrity_score` & Memory |

## 2. Quest Agent RAG Robustness

The history recall system has been upgraded from "context searching" to **"Tactical Evidence Retrieval"**:

*   **Intelligent Triggers**: Detects intent through sequential keywords (e.g., `where next`, `after X`) and named entities (`Willem`, `Oukraal`, `Hangar 4`).
*   **Double-Anchor Logic**: To prevent hallucinations caused by early "plans," the system fetches both the **Earliest** mention (the Plan) and the **Latest** mention (the Action) for every keyword.
*   **Source Hierarchy**:
    1.  **User Correction**: If the user says "No, you're wrong," the agent immediately overrides its memory.
    2.  **DB Evidence**: Raw transaction logs from the database are treated as the Absolute Truth and can override the agent's internal summary.
    3.  **The Chronicle**: Used only for high-level continuity when specific details aren't in the DB window.
*   **Validation**: The system now verifies sequence (e.g., *Plan: Gilded Lily* -> *Action: Willem -> War Room -> Oukraal*) to ensure the agent doesn't double-down on discarded plot points.

## 3. Token Context Analysis (Per Turn)

These estimates are based on the current implementation in `agent_quest.py` using `gemini-2.0-flash-lite`:

| Component | Standard Turn | Recall/Correction Turn |
| :--- | :--- | :--- |
| **System Prompt** | ~2,800 tokens | ~3,100 tokens (Incl. Integrity Check) |
| **Chronicle So Far** | ~800 tokens | ~800 tokens |
| **Short-Term History** | ~1,500 tokens (10 msgs) | ~400 tokens (Last 2 msgs) |
| **DB Recall Evidence** | 0 tokens | ~2,500 tokens (Authoritative Chunks) |
| **TOTAL INPUT** | **~5,100 Tokens** | **~6,800 Tokens** |

### Usage Optimization
*   When **Authoritative Evidence** is detected, the short-term history window is automatically shrunk to 2 messages. This prioritizes the "Truth Snippets" over the noisy chat history, saving ~1,000 tokens while significantly increasing accuracy.
