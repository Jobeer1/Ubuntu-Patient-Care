# Forge Agent Current Behavior

## What Forge Does Now
Forge is the system's challenge-and-growth mentor. It is designed to push the user past shallow reflection and into clearer thinking, practical insight, and action.

## Current Inputs
- User message content.
- Chat history (last 10 messages for context, or last 6 messages for local Gemma).
- Current integrity score.
- Optional user location.
- Optional user API key (overrides config.ini).

## Current Response Style
- Uses stories, metaphors, and direct challenges.
- Avoids robotic active-listening language.
- Ends with a single question that pushes the user to think deeper.
- Returns JSON-shaped results to the rest of the app.
- Speaks as "The Forge" - a blacksmith of the soul, wise but not arrogant.

## Current Behavior Path
1. It first tries the configured Gemini model using the `GEMINI` API key from `config.ini`.
2. If Gemini fails (API error or network error), it falls back to the `fallback_chat` method.
3. The `fallback_chat` method first attempts a local Ollama instance running `gemma:2b`:
   - Tries `localhost:11434` first, then `127.0.0.1:11434` if connection fails.
   - If local Gemma responds, wraps it as a local response with +5 XP bonus and "offline" phase.
4. If the local model fails, it uses rule-based offline logic with predefined metaphors:
   - "Hammer" metaphor for conflict and negotiation.
   - "Abyss" metaphor for fear and risk.
   - "Fire" metaphor for purpose and meaning.
   - "Slag" metaphor for failure and resilience.
   - Default wisdom response for general topics.

## Offline Fallback Chain
### Local LLM Attempt (Gemma 2B via Ollama)
- Endpoint: `http://localhost:11434/api/generate` (with fallback to `127.0.0.1`)
- Timeout: 120 seconds (allows for model loading on first run)
- Model: `gemma:2b`
- Temperature: 0.7
- Max tokens: 200
- Stop sequences: `["User:", "Forge:"]`

### Rule-Based Logic
- Pattern matching on keywords in user input.
- Returns `[OFFLINE FORGE]` prefixed response.
- Score adjustment: 0 XP.
- Phase: "offline".

## Output Shape
Forge currently returns JSON with fields:
- `response` - The mentor's response text (may be prefixed with `[LOCAL GEMMA]` or `[OFFLINE FORGE]`).
- `score_adjustment` - XP points awarded (0-5 for regular, 10 for breakthrough, +5 for local Gemma).
- `is_ready` - Boolean indicating if user is ready to proceed (default: false, true for plain text responses).
- `phase` - Current phase ("listening", "offline", "error", or as returned by model).
- `new_insight` - A short, deep observation about the user (null if none).
- `insight_type` - Either "strength" or "flaw" (null if no new insight).

## Scoring Rules
- Award +1 to +5 XP (`score_adjustment`) if the user shows vulnerability, insight, or growth.
- Award +10 XP for a profound breakthrough.
- Award 0 XP for simple chatter.
- +5 XP bonus when using local Gemma fallback.
- Award 0 XP for rule-based offline fallback.

## Gemini API Configuration
- Model: `gemini-2.5-flash-lite` (configurable via `config.ini`).
- Dual API approach: REST API (primary) with `google-genai` library (secondary).
- Temperature: 0.7
- Max output tokens: 500
- Response MIME type: `application/json`
- Retry logic: 3 attempts with exponential backoff for 429 (rate limit) errors.

## Error Handling
- Missing API key: Returns error response with "API Key missing" message.
- Gemini API failure (non-200 status): Falls back to `fallback_chat`.
- Gemini parsing error (invalid JSON): Falls back to generic response.
- Network/connection errors: Falls back to `fallback_chat`.
- Rate limiting (429): Retries with 2s, 4s, 6s delays.

## Practical Limitations
- Forge is not a therapy agent.
- It is not a generic assistant.
- It is strongest when the user wants blunt feedback, a hard truth, or a reframed way to think about a problem.
- Local Gemma 2B has a 120-second timeout which may cause delays on first interaction.