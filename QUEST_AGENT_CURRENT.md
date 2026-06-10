# Quest Agent Current Behavior

## What Quest Does Now
Quest is the story-driven skill-transfer agent. It turns the user's situation into an interactive narrative with quests, NPCs, consequences, and XP.

## Current Inputs
- User message content.
- Recent dialogue history.
- Current user alias.
- Current score.
- Inventory state.
- Quest progress state.
- NPC roster.
- Snapshot summaries and recall context.

## Current Response Style
- Narrative-first and highly role-played.
- Uses the user as the Hero and keeps NPCs in character.
- Emphasizes realism unless the quest is explicitly fantasy or sci-fi.
- Keeps a quest log moving forward turn by turn.

## Current Behavior Path
1. It loads the active quest story and current quest state.
2. It builds context from history, quest progress, NPCs, and snapshots.
3. It routes special recall cases through deeper history search.
4. It calls Gemini as the primary model.
5. If Gemini fails, it falls back to local Ollama `gemma:2b`.
6. If that also fails, it returns a minimal emergency fallback.

## Core Quest Mechanics It Currently Uses
- The Big 6 NPC team: Igor, Masha, Kira, Uri, Elia, and Jobeer.
- Quest state tracking with `quest_progress`.
- Inventory updates and removals.
- NPC creation and updates.
- Story publishing through `publish_story`.
- Snapshot checkpoints every 10 turns.
- Boss encounter logic with location-aware constraints.
- Regional and thematic consistency for different campaign theatres.

## Output Shape
Quest currently returns JSON with fields like:
- `response`
- `quest_name`
- `choices`
- `is_quest_active`
- `inventory_update`
- `inventory_remove`
- `quest_progress_update`
- `npc_update`
- `score_adjustment`
- `new_insight`
- `insight_type`
- `publish_story`

## Practical Limitations
- Quest is not a freeform assistant.
- It is not meant to reset the story each turn.
- It strongly expects the user to narrate actions, while Quest simulates the consequences and the world reaction.
