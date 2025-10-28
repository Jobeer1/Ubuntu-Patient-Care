"""
AI Brain Service - Intelligent Medical Query Router
Connects LLMs (GPT-4, Claude, etc.) to MCP medical tools
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai  # or anthropic for Claude


class AIBrainService:
    """
    AI Brain that understands medical questions and routes them to MCP tools
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        Initialize AI Brain
        
        Args:
            api_key: OpenAI API key (or Anthropic for Claude)
            model: Model to use (gpt-4, gpt-3.5-turbo, claude-3, etc.)
        """
        self.api_key = api_key
        self.model = model
        openai.api_key = api_key
        
        # Available MCP tools
        self.tools = [
            {
                "name": "validate_medical_aid",
                "description": "Validate if a patient is enrolled in medical aid",
                "parameters": {
                    "member_number": "string",
                    "scheme_code": "string (DISCOVERY, MOMENTUM, BONITAS)",
                    "id_number": "string (optional)"
                }
            },
            {
                "name": "validate_preauth_requirements",
                "description": "Check if a procedure requires pre-authorization",
                "parameters": {
                    "scheme_code": "string",
                    "plan_code": "string",
                    "procedure_code": "string (NRPL code)"
                }
            },
            {
                "name": "estimate_patient_cost",
                "description": "Calculate what patient and medical aid will pay",
                "parameters": {
                    "member_number": "string",
                    "scheme_code": "string",
                    "procedure_code": "string (NRPL code)"
                }
            },
            {
                "name": "create_preauth_request",
                "description": "Create a pre-authorization request",
                "parameters": {
                    "patient_id": "string",
                    "member_number": "string",
                    "scheme_code": "string",
                    "procedure_code": "string",
                    "clinical_indication": "string",
                    "icd10_codes": "array of strings (optional)",
                    "urgency": "string (routine/urgent/emergency)"
                }
            },
            {
                "name": "check_preauth_status",
                "description": "Check status of a pre-authorization",
                "parameters": {
                    "preauth_id": "string"
                }
            },
            {
                "name": "list_pending_preauths",
                "description": "List all pending pre-authorizations",
                "parameters": {
                    "status": "string (queued/submitted/approved/rejected)"
                }
            }
        ]
    
    async def process_query(self, user_query: str, context: Optional[Dict] = None) -> Dict:
        """
        Process a natural language medical query
        
        Args:
            user_query: Natural language question from user
            context: Optional context (patient_id, member_number, etc.)
        
        Returns:
            Dict with AI response and tool calls made
        """
        
        # Step 1: Classify the query and extract parameters
        classification = await self._classify_query(user_query, context)
        
        # Step 2: Call appropriate MCP tools
        tool_results = await self._execute_tools(classification["tools_to_call"])
        
        # Step 3: Generate intelligent response
        response = await self._generate_response(user_query, tool_results, context)
        
        return {
            "query": user_query,
            "classification": classification,
            "tool_results": tool_results,
            "response": response,
            "confidence": classification.get("confidence", 0.0),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _classify_query(self, query: str, context: Optional[Dict]) -> Dict:
        """
        Use AI to classify query and determine which tools to call
        """
        
        system_prompt = f"""You are a medical AI assistant that routes queries to appropriate tools.

Available tools:
{json.dumps(self.tools, indent=2)}

Analyze the user's query and determine:
1. Which tools to call (in order)
2. What parameters to extract from the query
3. Confidence level (0.0-1.0)

Return JSON format:
{{
    "query_type": "MEMBER_VALIDATION | COST_ESTIMATION | PREAUTH_CREATION | STATUS_CHECK",
    "tools_to_call": [
        {{
            "tool": "tool_name",
            "parameters": {{"param": "value"}}
        }}
    ],
    "confidence": 0.95,
    "reasoning": "Why these tools were selected"
}}
"""
        
        user_prompt = f"""Query: {query}

Context: {json.dumps(context or {}, indent=2)}

Classify this query and determine which tools to call."""
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            classification = json.loads(response.choices[0].message.content)
            return classification
        
        except Exception as e:
            return {
                "error": f"Classification failed: {str(e)}",
                "tools_to_call": [],
                "confidence": 0.0
            }
    
    async def _execute_tools(self, tools_to_call: List[Dict]) -> List[Dict]:
        """
        Execute MCP tools via your server
        """
        results = []
        
        for tool_call in tools_to_call:
            try:
                # Import your MCP tool handlers
                from server import (
                    validate_medical_aid,
                    validate_preauth_requirements,
                    estimate_patient_cost,
                    create_preauth_request,
                    check_preauth_status,
                    list_pending_preauths
                )
                
                tool_name = tool_call["tool"]
                parameters = tool_call["parameters"]
                
                # Call the appropriate tool
                if tool_name == "validate_medical_aid":
                    result = validate_medical_aid(parameters)
                elif tool_name == "validate_preauth_requirements":
                    result = validate_preauth_requirements(parameters)
                elif tool_name == "estimate_patient_cost":
                    result = estimate_patient_cost(parameters)
                elif tool_name == "create_preauth_request":
                    result = create_preauth_request(parameters)
                elif tool_name == "check_preauth_status":
                    result = check_preauth_status(parameters)
                elif tool_name == "list_pending_preauths":
                    result = list_pending_preauths(parameters)
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
                
                results.append({
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": result,
                    "success": "error" not in result
                })
            
            except Exception as e:
                results.append({
                    "tool": tool_call.get("tool", "unknown"),
                    "error": str(e),
                    "success": False
                })
        
        return results
    
    async def _generate_response(
        self, 
        query: str, 
        tool_results: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """
        Generate intelligent natural language response
        """
        
        system_prompt = """You are a medical AI assistant helping with medical scheme authorizations.

Your role:
1. Interpret tool results in plain language
2. Provide clinical context when relevant
3. Suggest next steps
4. Flag any issues or concerns

Be concise, accurate, and helpful."""
        
        tool_results_str = json.dumps(tool_results, indent=2)
        
        user_prompt = f"""User asked: "{query}"

Tool results:
{tool_results_str}

Context: {json.dumps(context or {}, indent=2)}

Provide a clear, helpful response to the user's question."""
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    async def optimize_preauth(
        self,
        patient_id: str,
        procedure: str,
        clinical_indication: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Use AI to optimize pre-authorization justification for higher approval rates
        """
        
        system_prompt = """You are a medical AI that optimizes pre-authorization requests.

Your goal: Improve clinical justification to maximize approval likelihood.

Guidelines:
1. Add relevant clinical context
2. Cite medical guidelines when applicable
3. Emphasize medical necessity
4. Include red flags or urgent indicators
5. Use proper medical terminology

Return JSON:
{
    "optimized_justification": "Enhanced clinical indication",
    "approval_likelihood": 0.97,
    "confidence": 0.92,
    "reasoning": "Why this improves approval chances"
}
"""
        
        user_prompt = f"""Optimize this pre-authorization request:

Patient ID: {patient_id}
Procedure: {procedure}
Original indication: {clinical_indication}

Context: {json.dumps(context or {}, indent=2)}

Provide an optimized clinical justification."""
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )
            
            optimization = json.loads(response.choices[0].message.content)
            return optimization
        
        except Exception as e:
            return {
                "error": f"Optimization failed: {str(e)}",
                "optimized_justification": clinical_indication,
                "approval_likelihood": 0.75,
                "confidence": 0.0
            }


# Example usage
async def example_usage():
    """Example of how to use the AI Brain"""
    
    # Initialize AI Brain (use your OpenAI API key)
    brain = AIBrainService(api_key="your-openai-api-key", model="gpt-4")
    
    # Example 1: Natural language query
    result = await brain.process_query(
        "Is patient 1234567890 enrolled in Discovery and what will CT Head cost?",
        context={"patient_id": "P12345"}
    )
    
    print("AI Response:", result["response"])
    print("Tools Called:", [t["tool"] for t in result["tool_results"]])
    print("Confidence:", result["confidence"])
    
    # Example 2: Optimize pre-auth
    optimization = await brain.optimize_preauth(
        patient_id="P12345",
        procedure="CT Head",
        clinical_indication="Severe headache",
        context={
            "age": 45,
            "symptoms": "Acute onset, photophobia, neck stiffness"
        }
    )
    
    print("\nOptimized Justification:", optimization["optimized_justification"])
    print("Approval Likelihood:", f"{optimization['approval_likelihood']:.0%}")


if __name__ == "__main__":
    asyncio.run(example_usage())
