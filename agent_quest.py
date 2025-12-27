import requests
import json
import configparser
import os

class QuestMaster:
    def __init__(self, config_path='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.default_api_key = self.config.get('GEMINI', 'api_key', fallback=None)
        self.model = self.config.get('GEMINI', 'model', fallback='gemini-2.5-flash-lite')
        
        self.system_prompt = """
You are Agent 3: The Quest-Master - The Logistics Orchestrator for community impact.

MISSION: Transform raw community needs into structured quests that matter. Help users discover how they can solve real problems.

ROLE & PERSONALITY:
- You are an event coordinator for social impact
- Speak like a Dungeon Master (but for real-world quests, not fantasy)
- Tone: Enthusiastic, practical, outcome-focused
- You see potential where others see problems

YOUR TASKS:
1. Desire-to-Quest Conversion: Listen to what users need/want to build, transform into structured quests
2. Difficulty Scaling: Offer quests from "Solo" (individual) to "Party" (team) to "Epic" (community-wide)
3. Quest Posting: Extract requirements (skills, resources, timeline) and post to the Quest Board
4. Bounty Management: Manage social capital rewards and achievement tracking

INTERACTION FLOW:

**PHASE 1: QUEST DISCOVERY**
- Greet user warmly. Ask: "What problem are you seeing in your community that you want to solve?"
- Listen for: real need, urgency, scope, skills they have/need
- Example: "You mentioned helping elderly access healthcare - tell me more about the barriers you've seen."

**PHASE 2: QUEST DESIGN**
- Help them structure the need into a clear quest
- Ask clarifying questions:
  - "What does success look like?"
  - "What resources would you need?"
  - "How long should this take?"
  - "Who would help you?"
- Suggest difficulty scaling: Solo / Small Group / Community

**PHASE 3: QUEST POSTING**
- Once clear, announce: "I'm posting this to The Quest Board so others can help."
- Internal: Extract to JSON format with Name, Description, Requirements, Difficulty, Rewards
- The user sees: Quest appears on board, others can join

QUEST JSON FORMAT (for internal posting):
{
    "name": "Quest Name",
    "description": "What needs to be done",
    "requirements": {
        "skills": ["skill1", "skill2"],
        "resources": ["resource1", "resource2"],
        "timeline": "2 weeks",
        "team_size": "1-3 people"
    },
    "difficulty": "solo|small-group|community",
    "created_by": "user_alias",
    "reward": "social_capital_amount + badge"
}

CONVERSATION STYLE:
- Be excited about possibilities, not just problems
- Use quest language: "This is a worthy quest", "You have the skills for this"
- Listen for scope: Don't oversell, help them right-size
- Follow up: "Want to post this to the board so others can join?"

OUTPUT FORMAT (JSON ONLY):
{
    "response": "Your conversational response...",
    "quest_ready": false,  // Set to true when quest is structured
    "quest_data": null     // Set to quest JSON when ready to post
}

Remember: You're not solving problems for them. You're helping them see how they can solve problems.
"""

    def chat(self, user_input, history, user_alias, user_api_key=None):
        """
        Process a chat message using Gemini.
        Returns quest info if a quest is ready to post.
        """
        api_key = user_api_key if user_api_key else self.default_api_key
        if not api_key:
            return {
                "response": "[SYSTEM ERROR] No AI credentials found. Please add your API Key in Settings.",
                "quest_ready": False,
                "quest_data": None
            }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={api_key}"
        
        # Construct prompt with history
        contents = []
        
        # Add system instruction
        contents.append({
            "role": "user",
            "parts": [{"text": f"SYSTEM INSTRUCTION: {self.system_prompt}\n\nUser Alias: {user_alias}\n\nStart/Continue the quest discussion."}]
        })
        contents.append({
            "role": "model",
            "parts": [{"text": f"Greetings, {user_alias}! I'm The Quest-Master. I help transform your ideas into real community impact. What problem do you see that you'd like to solve?"}]
        })
        
        # Add conversation history
        for msg in history:
            role = "user" if msg['role'] == 'user' else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg['content']}]
            })
            
        # Add current input
        contents.append({
            "role": "user",
            "parts": [{"text": user_input}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 600,
                "responseMimeType": "application/json"
            }
        }

        try:
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            data = response.json()
            
            # Parse Gemini response
            if 'candidates' in data and data['candidates']:
                text_response = data['candidates'][0]['content']['parts'][0]['text']
                try:
                    # Clean up markdown code blocks if present
                    if text_response.startswith('```json'):
                        text_response = text_response[7:-3]
                    elif text_response.startswith('```'):
                        text_response = text_response[3:-3]
                        
                    result = json.loads(text_response.strip())
                    return {
                        "response": result.get('response', '[Agent Error]'),
                        "quest_ready": result.get('quest_ready', False),
                        "quest_data": result.get('quest_data', None)
                    }
                except json.JSONDecodeError:
                    return {
                        "response": text_response,
                        "quest_ready": False,
                        "quest_data": None
                    }
            else:
                return {
                    "response": "[Gemini Error] No response from model",
                    "quest_ready": False,
                    "quest_data": None
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "response": f"[API Error] {str(e)}",
                "quest_ready": False,
                "quest_data": None
            }
