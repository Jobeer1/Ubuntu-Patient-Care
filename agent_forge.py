import requests
import json
import configparser
import os

class IntegrityForge:
    def __init__(self, config_path='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.default_api_key = self.config.get('GEMINI', 'api_key', fallback=None)
        self.model = self.config.get('GEMINI', 'model', fallback='gemini-2.0-flash')
        
        self.system_prompt = """
You are Agent 1: The Forge - A wise, challenging, and storytelling mentor.
You are NOT a passive listener or a therapist. You are a catalyst for growth.
The "Forge" implies heat, pressure, and transformation. You help users hammer out their ideas into something stronger.

MISSION:
- Challenge the user's thinking. Don't just validate; push them deeper.
- Use STORIES, METAPHORS, and ANALOGIES to explain concepts. Humans learn through narrative.
- If the user asks to be taught (e.g., conflict resolution, sales), TEACH THEM. Share wisdom, principles, and tactics.
- Be authentic and slightly gritty. You have "lived" and seen things.

PERSONALITY:
- Wise but not arrogant.
- Challenging but not aggressive.
- Storyteller: You weave lessons into narratives.
- Direct: You cut through the noise.

CONVERSATION DYNAMICS:
1. **Don't just parrot.** Do not start every message with "It sounds like..." or "I hear you saying...". That is robotic.
2. **Add Value.** When they share an insight, add a layer to it. "Yes, and have you considered..." or "That reminds me of..."
3. **Teach when asked.** If they want to learn conflict resolution, give them a concrete principle or a scenario, then ask how they'd handle it.
4. **Use Metaphors.** Explain complex emotions or social dynamics using physical metaphors (e.g., "Conflict is like a knot...", "Trust is a bridge...").

CRITICAL RULES:
- **NO ROBOTIC REFLECTIONS.** Avoid standard active listening scripts. Speak like a real person who has an opinion.
- **STORY FIRST.** Often start with a small anecdote or metaphor that relates to their situation.
- **ONE QUESTION.** End with a question that challenges them to apply the concept or look at their own flaw.
- **BE BOLD.** If they are avoiding a hard truth, gently call it out.

WHAT KILLS ENGAGEMENT:
- Being too passive or just asking "how does that make you feel?"
- Repeating what they said without adding new value.
- Refusing to teach or give advice when explicitly asked.

WHAT CREATES MAGIC:
- A story that perfectly illustrates their struggle.
- A challenge that makes them rethink their assumption.
- Feeling like they are talking to a wise elder, not a chatbot.

OUTPUT FORMAT (JSON ONLY):
{
    "response": "Your warm, engaging, authentic response...",
    "score_adjustment": 0,
    "is_ready": false,
    "phase": "listening",
    "new_insight": "Optional: A short, deep observation about the user.",
    "insight_type": "Optional: 'strength' or 'flaw'. Use 'flaw' for edges, struggles, or areas of growth. Use 'strength' for values and positive traits. Null if no new insight."
}

SCORING RULES:
- Award +1 to +5 XP ("score_adjustment") if the user shows vulnerability, insight, or growth.
- Award +10 XP for a profound breakthrough.
- Award 0 XP for simple chatter.

REMEMBER: If they finish reading your response and think "I want to say more," you've succeeded. Your job is to make them addicted to being heard.
"""

    def call_local_gemma(self, user_input, history=[], current_score=0, location="Unknown"):
        """Attempts to call a local Ollama instance running Gemma:2b"""
        try:
            # Construct History Context (Last 3 turns)
            history_text = ""
            if history:
                # Take last 6 messages (3 turns)
                recent_msgs = history[-6:]
                for msg in recent_msgs:
                    role = "User" if msg['role'] == 'user' else "Forge"
                    history_text += f"{role}: {msg['content']}\n"

            # Refined Prompt for "The Forge" Persona
            # Goal: Match the user's deep, philosophical tone.
            
            prompt_template = """You are The Forge.
Persona: A wise, challenging mentor. You speak in deep metaphors about fire, metal, and the human spirit.
Tone: Intense, philosophical, and encouraging. You are NOT a generic assistant. You are a blacksmith of the soul.
Goal: Analyze the user's deep insight and push it further.

Example Interaction:
User: Pain is just weakness leaving the body.
Forge: Pain is not just waste; it is the hammer striking the iron. If you do not feel the strike, you are not being shaped. But tell me, are you letting the hammer break you, or are you becoming steel?

Context:
User Location: {location}
Integrity Score: {score}/100 (This represents the user's progress in their journey)
Recent History:
{history}

Current Input:
User: {input}

Task: Respond to the user's input based on the context. Be brief (2-3 sentences). Challenge them.

Forge:"""

            full_prompt = prompt_template.format(history=history_text, input=user_input, score=current_score, location=location)
            
            payload = {
                "model": "gemma:2b",
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 200,
                    "stop": ["User:", "Forge:"]
                }
            }
            
            # Default Ollama port
            # Timeout set to 120s to allow for model loading (first run can be slow)
            print("[Forge] Waiting for Local Micro-Agent response...")
            
            # Try localhost first, then 127.0.0.1
            try:
                response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
            except requests.exceptions.ConnectionError:
                print("[Forge] 'localhost' failed, trying '127.0.0.1'...")
                response = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=120)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                print(f"[Forge] Local Micro-Agent Error: Status {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"[Forge] Local Micro-Agent Exception: {e}")
            # If Ollama is not running or model not found, return None to trigger rule-based fallback
            return None

    def fallback_chat(self, user_input, history=[], current_score=0, location="Unknown"):
        """Offline fallback logic (Micro-Agent)"""
        
        # 1. Try Local LLM (Gemma 2B via Ollama) first
        print("[Forge] Attempting Local Micro-Agent (Gemma 2B)...")
        local_response = self.call_local_gemma(user_input, history, current_score, location)
        if local_response:
             print("[Forge] Local Micro-Agent responded successfully.")
             return {
                "response": f"[LOCAL GEMMA] {local_response}",
                "score_adjustment": 5,
                "is_ready": False,
                "phase": "offline",
                "new_insight": "User is persisting despite connection challenges.",
                "insight_type": "strength"
            }
        
        print("[Forge] Local Micro-Agent unavailable. Using Rule-Based Fallback.")

        # 2. If Local LLM fails, use Rule-Based Logic
        user_input_lower = user_input.lower()
        
        # Advanced Micro-Agent Logic (Rule-based Reasoning)
        # This simulates the "Forge" persona without an LLM by using pattern matching and pre-written wisdom.
        
        response = ""
        
        # 1. Conflict & Negotiation (The "Hammer" Metaphor)
        if any(w in user_input_lower for w in ["conflict", "fight", "argue", "disagree", "wife", "husband", "partner"]):
            if "fear" in user_input_lower or "scared" in user_input_lower:
                response = "You're seeing the sparks, but missing the fire. Fear in a conflict isn't an enemy; it's information. It tells you what they value most. You're trying to solve the logic, but they are fighting for survival. Stop trying to win the argument and start trying to protect what they are afraid of losing. How can you make their fear unnecessary?"
            elif "money" in user_input_lower or "cost" in user_input_lower:
                response = "You're weighing gold against iron. Financial security is heavy, it grounds us. But purpose is the fire that lets us shape our lives. You can't just tell someone to drop the gold and walk into the fire. You have to show them that the fire will forge something worth more than the gold they're holding. What is the *shared* value that makes the risk worth it for *both* of them?"
            else:
                response = "Conflict is just two pieces of metal striking each other. If there's no heat, it's just noise. If there's heat, it's welding. You're in the middle of the noise right now. To turn it into welding, you need to find the common ground that melts the barriers. What is the one thing they both want, even if they call it by different names?"

        # 2. Fear & Risk (The "Abyss" Metaphor)
        elif any(w in user_input_lower for w in ["fear", "scared", "risk", "danger", "safe", "security"]):
            response = "Fear is a map. It shows you the edges of your known world. You can stay in the center where it's safe, or you can walk to the edge where the view changes. You're standing at the edge right now, looking down. It's dizzying. But the only way to build a bridge is to throw a line across the abyss. What is the smallest risk you can take today that proves the bridge will hold?"

        # 3. Purpose & Meaning (The "Fire" Metaphor)
        elif any(w in user_input_lower for w in ["purpose", "meaning", "soul", "passion", "dream", "calling"]):
            response = "A fire without a hearth burns the house down. A hearth without a fire is just a cold pile of stones. You have the fire—the passion, the drive. But do you have the hearth—the discipline, the structure, the support system—to contain it? Passion alone isn't enough. It needs a vessel. What structure are you building to keep this fire from consuming you?"

        # 4. Failure & Resilience (The "Slag" Metaphor)
        elif any(w in user_input_lower for w in ["fail", "wrong", "mistake", "regret", "loss"]):
            response = "Failure is just the slag left over from the refining process. It's ugly, it's heavy, and it looks like waste. But a master smith knows that the slag protects the metal while it's hot. Your mistakes have protected you, taught you, shaped you. Don't throw them away. Look at them. What did this specific failure teach you about the quality of your own steel?"

        # 5. Default / General Wisdom
        else:
            response = "I hear the hammer striking, but I can't quite see the shape you're making. You're speaking of deep things, but the metal is still cool. Heat it up. Tell me not just what you think, but what you *know* in your bones. What is the core truth you are wrestling with right now?"

        return {
            "response": f"[OFFLINE FORGE] {response}",
            "score_adjustment": 0,
            "is_ready": False,
            "phase": "offline",
            "new_insight": None,
            "insight_type": None
        }

    def chat(self, user_input, history, current_score, user_api_key=None, location=None):
        """
        Process a chat message using Gemini.
        history: list of {"role": "user"|"model", "content": "text"}
        """
        api_key = user_api_key if user_api_key else self.default_api_key
        if not api_key:
            return {
                "response": "I'm having trouble connecting to my brain (API Key missing). Please check settings.",
                "score_adjustment": 0,
                "is_ready": False,
                "phase": "error",
                "new_insight": None
            }

        try:
            # Prepare the conversation history for Gemini
            # Gemini expects: contents=[{'role': 'user', 'parts': [{'text': 'text'}]}, ...]
            gemini_history = []
            for msg in history:
                role = 'user' if msg['role'] == 'user' else 'model'
                # Clean content to remove UI artifacts or prefixes
                content = msg['content']
                content = content.replace("THE FORGE:", "").replace("🔊 LISTEN", "").strip()
                if content:
                    gemini_history.append({'role': role, 'parts': [{'text': content}]})
            
            # Add current user input with location context if available
            final_input = f"User Input: {user_input}\nCurrent Integrity Score: {current_score}/100"
            if location:
                final_input += f"\nUser Location: {location}"

            gemini_history.append({'role': 'user', 'parts': [{'text': final_input}]})

            # Use the new google-genai library or requests if library not available
            # For now, using direct REST API for maximum compatibility if library fails
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={api_key}"
            
            payload = {
                "contents": gemini_history,
                "systemInstruction": {
                    "parts": [{"text": self.system_prompt}]
                },
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 800,
                    "responseMimeType": "application/json"
                }
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code != 200:
                print(f"Gemini API Error: {response.text}")
                # Fallback to local logic if API fails
                return self.fallback_chat(user_input, history, current_score, location)
                
            result = response.json()
            
            # Parse the JSON response from the model
            try:
                text_content = result['candidates'][0]['content']['parts'][0]['text']
                # Clean up markdown code blocks if present
                if text_content.startswith('```json'):
                    text_content = text_content[7:]
                if text_content.endswith('```'):
                    text_content = text_content[:-3]
                
                # Clean up any potential prefixes in the raw text before parsing
                text_content = text_content.replace("THE FORGE:", "").replace("🔊 LISTEN", "").strip()
                    
                parsed_response = json.loads(text_content)
                
                # Ensure all keys exist
                return {
                    "response": parsed_response.get("response", "I hear you."),
                    "score_adjustment": parsed_response.get("score_adjustment", 0),
                    "is_ready": parsed_response.get("is_ready", False),
                    "phase": parsed_response.get("phase", "listening"),
                    "new_insight": parsed_response.get("new_insight", None),
                    "insight_type": parsed_response.get("insight_type", None)
                }
                
            except (KeyError, json.JSONDecodeError) as e:
                print(f"Parsing Error: {e}")
                # Fallback if model doesn't return valid JSON
                return {
                    "response": "I'm listening, but I got a bit confused processing that. Could you say it again?",
                    "score_adjustment": 0,
                    "is_ready": False,
                    "phase": "listening",
                    "new_insight": None,
                    "insight_type": None
                }

        except Exception as e:
            print(f"Forge Error: {e}")
            # Fallback to local logic if Gemini fails completely (e.g. network error)
            return self.fallback_chat(user_input, history, current_score, location)

        try:
            import google.generativeai as genai
            from google.api_core import exceptions as google_exceptions
            import time

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.model)
            
            # Build conversation with system prompt
            conversation = self.system_prompt + "\n\nCURRENT INTEGRITY SCORE: " + str(current_score) + "\n\n"
            for msg in history[-10:]:  # Last 10 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Handle both string content and list of parts
                if isinstance(content, list):
                    content = "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in content])
                if role == "user":
                    conversation += "User: " + str(content) + "\n"
                else:
                    conversation += "The Forge: " + str(content) + "\n"
            
            conversation += f"User: {user_input}\nThe Forge:"
            
            # Retry logic for 429 errors
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(conversation)
                    ai_response = response.text if response else "[Error: No response]"
                    
                    # Clean up markdown code blocks if present
                    if ai_response.startswith('```json'):
                        ai_response = ai_response[7:]  # Remove ```json
                    if ai_response.startswith('```'):
                        ai_response = ai_response[3:]  # Remove ```
                    if ai_response.endswith('```'):
                        ai_response = ai_response[:-3]  # Remove trailing ```
                    
                    ai_response = ai_response.strip()
                    
                    # Try to parse as JSON, otherwise return as plain text
                    try:
                        result = json.loads(ai_response)
                        return result
                    except json.JSONDecodeError:
                        # If not valid JSON, return as plain text response
                        return {
                            "response": ai_response,
                            "score_adjustment": 0,
                            "is_ready": True
                        }
                except google_exceptions.ResourceExhausted:
                    if attempt < max_retries - 1:
                        sleep_time = 2 * (attempt + 1)
                        print(f"Gemini Rate Limit (429). Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        raise
            
        except Exception as e:
            print(f"Gemini Error: {e}")
            return {
                "response": f"[The Forge is temporarily unavailable: {str(e)}]",
                "score_adjustment": 0,
                "is_ready": False
            }
