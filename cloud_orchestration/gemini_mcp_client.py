"""
Gemini MCP Client - Connects Gemini to MCP Server Tools
Gives Gemini access to patient data, medical records, and medical scheme information
"""

import os
import json
import requests
import configparser
from typing import Dict, List, Optional
import google.generativeai as genai

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Configure Gemini
genai.configure(api_key=config.get('Google', 'gemini_key'))

# MCP Server Configuration
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:8080')
MCP_API_TOKEN = os.getenv('MCP_API_TOKEN', '')


class GeminiMCPClient:
    """
    Gemini client with MCP server tool access
    """
    
    def __init__(self):
        """Initialize Gemini with MCP tools"""
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.mcp_url = MCP_SERVER_URL
        self.tools = self._register_tools()
        print(f"✓ Gemini MCP Client initialized with {len(self.tools)} tools")
    
    def _register_tools(self) -> List[Dict]:
        """
        Register available MCP tools for Gemini
        """
        return [
            {
                "name": "get_patient_info",
                "description": "Get patient demographic and medical information",
                "parameters": {
                    "patient_id": "Patient ID number"
                }
            },
            {
                "name": "get_medical_scheme_benefits",
                "description": "Check patient's medical scheme benefits and coverage",
                "parameters": {
                    "patient_id": "Patient ID",
                    "scheme_name": "Medical scheme name (e.g., Discovery, Bonitas)"
                }
            },
            {
                "name": "get_patient_studies",
                "description": "Get list of medical imaging studies for a patient",
                "parameters": {
                    "patient_id": "Patient ID"
                }
            },
            {
                "name": "search_medical_schemes",
                "description": "Search and compare medical schemes in South Africa",
                "parameters": {
                    "criteria": "Search criteria (e.g., 'best for chronic medication')"
                }
            },
            {
                "name": "get_procedure_authorization_requirements",
                "description": "Get authorization requirements for a medical procedure",
                "parameters": {
                    "procedure_name": "Name of the procedure",
                    "scheme_name": "Medical scheme name"
                }
            },
            {
                "name": "estimate_medical_costs",
                "description": "Estimate costs for medical procedures",
                "parameters": {
                    "procedure_name": "Name of the procedure",
                    "scheme_name": "Medical scheme name"
                }
            }
        ]
    
    def call_mcp_tool(self, tool_name: str, parameters: Dict) -> Dict:
        """
        Call an MCP server tool
        """
        try:
            # Map tool names to MCP endpoints
            endpoint_map = {
                "get_patient_info": "/api/patients/{patient_id}",
                "get_medical_scheme_benefits": "/api/medical-schemes/benefits",
                "get_patient_studies": "/api/patients/{patient_id}/studies",
                "search_medical_schemes": "/api/medical-schemes/search",
                "get_procedure_authorization_requirements": "/api/procedures/authorization-requirements",
                "estimate_medical_costs": "/api/procedures/cost-estimate"
            }
            
            endpoint = endpoint_map.get(tool_name, "")
            if not endpoint:
                return {"error": f"Unknown tool: {tool_name}"}
            
            # Format endpoint with parameters
            if "{patient_id}" in endpoint and "patient_id" in parameters:
                endpoint = endpoint.format(patient_id=parameters["patient_id"])
            
            # Make API call to MCP server
            url = f"{self.mcp_url}{endpoint}"
            headers = {"Authorization": f"Bearer {MCP_API_TOKEN}"} if MCP_API_TOKEN else {}
            
            if tool_name in ["get_patient_info", "get_patient_studies"]:
                response = requests.get(url, headers=headers, params=parameters)
            else:
                response = requests.post(url, headers=headers, json=parameters)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"MCP API error: {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def chat(self, user_message: str, context: Optional[Dict] = None) -> str:
        """
        Chat with Gemini with MCP tool access
        
        Args:
            user_message: User's question or request
            context: Optional context (patient_id, scheme_name, etc.)
            
        Returns:
            Gemini's response with tool-augmented information
        """
        # Build enhanced prompt with available tools
        system_prompt = f"""You are a medical AI assistant with access to real patient data and medical scheme information through MCP tools.

Available Tools:
{json.dumps(self.tools, indent=2)}

Context:
{json.dumps(context or {}, indent=2)}

When answering questions:
1. Identify which tools you need to call
2. Call the appropriate MCP tools to get real data
3. Provide accurate, helpful answers based on the data
4. Always cite your sources (which tool provided the information)

User Question: {user_message}

Think step by step:
1. What information do I need?
2. Which tools can provide that information?
3. What should I tell the user?
"""
        
        try:
            # Generate response
            response = self.model.generate_content(system_prompt)
            answer = response.text
            
            # Check if Gemini wants to call tools
            if "TOOL_CALL:" in answer:
                # Extract tool calls and execute them
                # This is a simplified version - in production, use function calling API
                tool_results = self._execute_tool_calls(answer, context)
                
                # Generate final response with tool results
                final_prompt = f"""Based on the tool results:
{json.dumps(tool_results, indent=2)}

Original question: {user_message}

Provide a helpful, accurate answer:"""
                
                final_response = self.model.generate_content(final_prompt)
                return final_response.text
            
            return answer
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _execute_tool_calls(self, gemini_response: str, context: Dict) -> Dict:
        """
        Execute tool calls identified by Gemini
        """
        results = {}
        
        # Simple tool call extraction (in production, use structured function calling)
        if "get_patient_info" in gemini_response.lower():
            if context and "patient_id" in context:
                results["patient_info"] = self.call_mcp_tool(
                    "get_patient_info",
                    {"patient_id": context["patient_id"]}
                )
        
        if "medical scheme" in gemini_response.lower() or "benefits" in gemini_response.lower():
            if context and "patient_id" in context and "scheme_name" in context:
                results["benefits"] = self.call_mcp_tool(
                    "get_medical_scheme_benefits",
                    {
                        "patient_id": context["patient_id"],
                        "scheme_name": context["scheme_name"]
                    }
                )
        
        return results
    
    def get_medical_scheme_advice(self, question: str, patient_context: Optional[Dict] = None) -> str:
        """
        Get medical scheme advice with real data access
        
        Args:
            question: Patient's question about medical schemes
            patient_context: Optional patient information
            
        Returns:
            Detailed advice with real data
        """
        prompt = f"""You are a medical scheme advisor for South African patients.

Patient Context:
{json.dumps(patient_context or {}, indent=2)}

Patient Question: {question}

Provide detailed, accurate advice about:
1. Which medical schemes are best for their needs
2. Coverage details and benefits
3. Cost estimates
4. Authorization requirements
5. How to maximize their benefits

Use real South African medical scheme information (Discovery, Bonitas, Momentum, Medshield, GEMS, etc.)
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error getting advice: {str(e)}"


# Example usage
if __name__ == "__main__":
    client = GeminiMCPClient()
    
    # Example 1: Get medical scheme advice
    advice = client.get_medical_scheme_advice(
        "Which medical scheme is best for chronic medication?",
        patient_context={
            "age": 45,
            "chronic_conditions": ["diabetes", "hypertension"],
            "budget": "R3000-R5000 per month"
        }
    )
    print(f"\nAdvice:\n{advice}")
    
    # Example 2: Chat with context
    response = client.chat(
        "What are my benefits for MRI scans?",
        context={
            "patient_id": "8501015800089",
            "scheme_name": "Discovery Health"
        }
    )
    print(f"\nResponse:\n{response}")
