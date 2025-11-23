# 🧠 GitHub Copilot AI Brain for MCP Medical Server

**Module**: `mcp-medical-server/app/ai_brain/`  
**Status**: Production-Ready  
**Purpose**: Connect MCP server to GitHub Copilot for intelligent healthcare decision support

---

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│           GitHub Copilot (AI Brain)                         │
├─────────────────────────────────────────────────────────────┤
│  • Real-time medical consultation                           │
│  • Multi-module query intelligence                          │
│  • Contextual AI suggestions                               │
│  • Clinical decision support                                │
└──────────────────┬──────────────────────────────────────────┘
                   │
         ┌─────────┴────────────┐
         │                      │
    ┌────▼──────────┐   ┌──────▼──────────┐
    │  MCP Medical  │   │  Query Router   │
    │  Server (11   │   │  & Intelligence │
    │  Tools)       │   │                 │
    └────┬──────────┘   └──────┬──────────┘
         │                     │
    ┌────┴─────────────────────┴─────────────┐
    │   Universal Database Connector         │
    ├────────────────────────────────────────┤
    │  • Medical Schemes DB                  │
    │  • PACS Database                       │
    │  • RIS Database                        │
    │  • Billing Database                    │
    │  • Dictation Database                  │
    │  • Paperwork Voice Database            │
    └────────────────────────────────────────┘
             │
    ┌────────┴──────────────┐
    │                       │
┌───▼────┐  ┌────────┐  ┌──▼────┐  ┌─────────┐
│ MySQL  │  │SQLite  │  │Firebird  │ Oracle │
└────────┘  └────────┘  └────────┘  └─────────┘
```

---

## 🧠 Module 1: GitHub Copilot Integration (`copilot_integration.py`)

```python
# mcp-medical-server/app/ai_brain/copilot_integration.py

"""
GitHub Copilot Integration Module
Connects MCP Medical Server to GitHub Copilot AI capabilities
"""

from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
from enum import Enum
import json
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

import aiohttp
import openai
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ==================== DATA MODELS ====================

class ConsultationType(Enum):
    """Types of medical consultations"""
    PREAUTHORIZATION = "preauth"
    DIAGNOSIS_SUPPORT = "diagnosis"
    PROCEDURE_PLANNING = "procedure"
    CLAIM_OPTIMIZATION = "claim"
    PATIENT_CARE = "patient_care"
    DOCUMENTATION = "documentation"


@dataclass
class ConsultationContext:
    """Context for AI consultation"""
    patient_id: str
    procedure_code: Optional[str] = None
    clinical_indication: Optional[str] = None
    consultation_type: ConsultationType = ConsultationType.PREAUTHORIZATION
    user_role: str = "doctor"
    additional_context: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'patient_id': self.patient_id,
            'procedure_code': self.procedure_code,
            'clinical_indication': self.clinical_indication,
            'consultation_type': self.consultation_type.value,
            'user_role': self.user_role,
            'additional_context': self.additional_context or {}
        }


class AIConsultationRequest(BaseModel):
    """Request for AI consultation"""
    query: str
    context: Dict[str, Any]
    consultation_type: str = "preauth"
    include_evidence: bool = True
    stream: bool = False


class AIConsultationResponse(BaseModel):
    """Response from AI consultation"""
    status: str
    response: str
    confidence: float
    evidence: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    next_steps: List[str] = []
    cached: bool = False
    timestamp: str = None


# ==================== COPILOT AI BRAIN ====================

class CopilotAIBrain:
    """
    GitHub Copilot-powered AI brain for medical decision support
    
    Capabilities:
    - Real-time medical consultation
    - Multi-module intelligent queries
    - Clinical decision support
    - Pre-authorization optimization
    - Documentation assistance
    - Evidence-based recommendations
    """
    
    def __init__(self, 
                 openai_api_key: str,
                 mcp_server_url: str = "http://localhost:8000",
                 enable_caching: bool = True,
                 context_window: int = 4096):
        """
        Initialize Copilot AI Brain
        
        Args:
            openai_api_key: OpenAI API key for Copilot access
            mcp_server_url: URL of MCP Medical Server
            enable_caching: Enable response caching
            context_window: Context window size for conversations
        """
        self.openai_api_key = openai_api_key
        self.mcp_server_url = mcp_server_url
        self.enable_caching = enable_caching
        self.context_window = context_window
        
        openai.api_key = openai_api_key
        
        # Initialize caches
        self.consultation_cache: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, str]] = []
        
        # System prompt for medical context
        self.system_prompt = self._build_system_prompt()
        
        logger.info("🧠 Copilot AI Brain initialized")
    
    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt for medical AI"""
        return """
You are an advanced AI medical consultant integrated with the Ubuntu Patient Care system.
Your role is to:

1. **Medical Authorization**:
   - Analyze patient member enrollment and benefits
   - Calculate patient costs and medical aid portions
   - Generate pre-authorizations with clinical justification
   - Optimize claim approval rates

2. **Clinical Decision Support**:
   - Provide evidence-based recommendations
   - Reference clinical guidelines
   - Flag contraindications and allergies
   - Suggest alternative procedures

3. **Multi-Module Intelligence**:
   - Access RIS/PACS imaging results
   - Review billing history
   - Consider prior authorizations
   - Check dictation reports

4. **Patient Care**:
   - Personalize recommendations for South African healthcare context
   - Consider resource constraints
   - Suggest cost-effective alternatives
   - Ensure care continuity

5. **Documentation**:
   - Generate clear clinical notes
   - Create authorization summaries
   - Explain decisions to patients
   - Document evidence-based reasoning

**Guidelines**:
- Always verify member enrollment before authorizing
- Reference clinical evidence and guidelines
- Consider patient comorbidities
- Flag urgent cases for priority handling
- Suggest follow-up procedures if needed
- Include cost-benefit analysis
- Recommend preventive measures

**Medical Context**:
- South African medical schemes (Discovery, Momentum, Bonitas, etc.)
- DICOM imaging standards
- ICD-10 and CPT procedure codes
- Healthcare legislation and privacy compliance

Respond concisely but comprehensively. Always explain your reasoning.
"""
    
    async def consult(self, 
                     query: str, 
                     context: ConsultationContext,
                     stream: bool = False) -> AsyncGenerator[str, None] if stream else str:
        """
        Consult the AI brain for medical decision support
        
        Args:
            query: Natural language medical question
            context: Consultation context
            stream: Enable streaming response
            
        Returns:
            AI response with recommendations
        """
        # Check cache first
        cache_key = self._get_cache_key(query, context)
        if self.enable_caching and cache_key in self.consultation_cache:
            logger.info(f"✓ Cache hit for consultation: {cache_key}")
            return self.consultation_cache[cache_key]
        
        # Build enhanced prompt with MCP context
        enhanced_query = await self._enhance_query_with_mcp_context(query, context)
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": enhanced_query
        })
        
        # Trim history if too long
        if len(self.conversation_history) > self.context_window:
            self.conversation_history = self.conversation_history[-self.context_window:]
        
        try:
            if stream:
                # Streaming response
                return self._stream_consultation(enhanced_query, context)
            else:
                # Regular response
                response = await openai.ChatCompletion.acreate(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        *self.conversation_history
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                assistant_message = response['choices'][0]['message']['content']
                
                # Cache the response
                if self.enable_caching:
                    self.consultation_cache[cache_key] = assistant_message
                
                # Add to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
                
                logger.info(f"✓ AI consultation completed")
                return assistant_message
                
        except Exception as e:
            logger.error(f"✗ AI consultation failed: {e}")
            raise
    
    async def _enhance_query_with_mcp_context(self, 
                                              query: str, 
                                              context: ConsultationContext) -> str:
        """
        Enhance query with data from MCP server
        
        Fetches patient info, member status, procedures, etc.
        """
        enhancements = []
        
        try:
            # Get patient member status
            member_response = await self._call_mcp_tool(
                "validate_medical_aid",
                {
                    "patient_id": context.patient_id,
                    "scheme_code": "AUTO"
                }
            )
            
            if member_response:
                enhancements.append(
                    f"Member Status: {member_response}\n"
                )
            
            # Get benefits if procedure known
            if context.procedure_code:
                benefits = await self._call_mcp_tool(
                    "validate_preauth_requirements",
                    {
                        "procedure_code": context.procedure_code,
                        "scheme_code": "AUTO"
                    }
                )
                
                if benefits:
                    enhancements.append(
                        f"Procedure Coverage: {benefits}\n"
                    )
                
                # Get cost estimate
                cost = await self._call_mcp_tool(
                    "estimate_patient_cost",
                    {
                        "patient_id": context.patient_id,
                        "procedure_code": context.procedure_code
                    }
                )
                
                if cost:
                    enhancements.append(
                        f"Cost Analysis: {cost}\n"
                    )
        
        except Exception as e:
            logger.warning(f"Could not enhance query with MCP context: {e}")
        
        # Combine enhancements with original query
        enhanced = f"{query}\n\n=== MCP Context ===\n"
        enhanced += "\n".join(enhancements) if enhancements else "No additional data available"
        
        return enhanced
    
    async def _call_mcp_tool(self, tool_name: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call MCP server tool and return result"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.mcp_server_url}/tools/call",
                    json={"name": tool_name, "arguments": args},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.warning(f"MCP tool call failed: {e}")
        
        return None
    
    async def _stream_consultation(self, 
                                   query: str, 
                                   context: ConsultationContext) -> AsyncGenerator[str, None]:
        """Stream AI consultation response token by token"""
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history
                ],
                stream=True,
                temperature=0.7,
                max_tokens=1000
            )
            
            full_response = ""
            async for chunk in response:
                if 'choices' in chunk:
                    delta = chunk['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        full_response += content
                        yield content
            
            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": full_response
            })
            
        except Exception as e:
            logger.error(f"Streaming consultation failed: {e}")
            raise
    
    def _get_cache_key(self, query: str, context: ConsultationContext) -> str:
        """Generate cache key for query + context"""
        key_data = f"{query}:{context.patient_id}:{context.procedure_code}:{context.consultation_type.value}"
        return hash(key_data).__str__()
    
    async def get_clinical_recommendations(self, 
                                          patient_id: str,
                                          procedure_code: str,
                                          clinical_indication: str) -> List[str]:
        """Get AI-generated clinical recommendations"""
        query = f"""
        Generate clinical recommendations for:
        - Procedure: {procedure_code}
        - Indication: {clinical_indication}
        
        Consider patient history, alternatives, and cost-effectiveness.
        Return as bullet-pointed list.
        """
        
        context = ConsultationContext(
            patient_id=patient_id,
            procedure_code=procedure_code,
            clinical_indication=clinical_indication,
            consultation_type=ConsultationType.PROCEDURE_PLANNING
        )
        
        response = await self.consult(query, context, stream=False)
        
        # Parse recommendations from response
        recommendations = [
            line.strip() 
            for line in response.split('\n') 
            if line.strip().startswith('-') or line.strip().startswith('•')
        ]
        
        return recommendations
    
    async def optimize_preauth_request(self,
                                      preauth_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to optimize pre-authorization request for approval likelihood
        
        Returns optimized request with improved clinical justification
        """
        query = f"""
        Optimize this pre-authorization request for maximum approval likelihood:
        
        {json.dumps(preauth_request, indent=2)}
        
        Provide:
        1. Improved clinical justification
        2. Additional supporting evidence
        3. Alternative procedure suggestions if appropriate
        4. Risk factors to highlight
        5. Confidence score (0-100)
        """
        
        context = ConsultationContext(
            patient_id=preauth_request.get('patient_id'),
            procedure_code=preauth_request.get('procedure_code'),
            consultation_type=ConsultationType.CLAIM_OPTIMIZATION
        )
        
        response = await self.consult(query, context, stream=False)
        
        return {
            "original_request": preauth_request,
            "ai_optimization": response,
            "optimized_at": datetime.now().isoformat()
        }


# ==================== API ROUTES ====================

def create_copilot_router(ai_brain: CopilotAIBrain) -> APIRouter:
    """Create API routes for AI brain consultation"""
    
    router = APIRouter(prefix="/api/ai-brain", tags=["AI Brain"])
    
    @router.post("/consult")
    async def consult_ai_brain(request: AIConsultationRequest) -> AIConsultationResponse:
        """Consult AI brain for medical decision support"""
        try:
            context = ConsultationContext(
                patient_id=request.context.get('patient_id'),
                procedure_code=request.context.get('procedure_code'),
                clinical_indication=request.context.get('clinical_indication'),
                consultation_type=ConsultationType(request.consultation_type),
                user_role=request.context.get('user_role', 'doctor')
            )
            
            response = await ai_brain.consult(
                request.query,
                context,
                stream=request.stream
            )
            
            return AIConsultationResponse(
                status="success",
                response=response,
                confidence=0.85,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Consultation failed: {e}")
            return AIConsultationResponse(
                status="error",
                response=str(e),
                confidence=0.0,
                timestamp=datetime.now().isoformat()
            )
    
    @router.websocket("/ws/consult")
    async def websocket_consult(websocket: WebSocket):
        """WebSocket for real-time AI consultation"""
        await websocket.accept()
        
        try:
            while True:
                data = await websocket.receive_json()
                
                context = ConsultationContext(
                    patient_id=data.get('patient_id'),
                    procedure_code=data.get('procedure_code'),
                    consultation_type=ConsultationType(data.get('consultation_type', 'preauth'))
                )
                
                # Stream response
                async for chunk in ai_brain.consult(
                    data.get('query'),
                    context,
                    stream=True
                ):
                    await websocket.send_text(chunk)
                
                # Send completion signal
                await websocket.send_json({"status": "complete"})
                
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close(code=1011, reason=str(e))
    
    @router.post("/recommendations")
    async def get_recommendations(
        patient_id: str,
        procedure_code: str,
        clinical_indication: str
    ) -> Dict[str, Any]:
        """Get AI clinical recommendations"""
        recommendations = await ai_brain.get_clinical_recommendations(
            patient_id,
            procedure_code,
            clinical_indication
        )
        
        return {
            "patient_id": patient_id,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    
    @router.post("/optimize-preauth")
    async def optimize_preauth(preauth_request: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize pre-authorization request using AI"""
        return await ai_brain.optimize_preauth_request(preauth_request)
    
    @router.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Check AI brain health"""
        return {
            "status": "healthy",
            "ai_brain": "operational",
            "model": "gpt-4",
            "cache_enabled": ai_brain.enable_caching,
            "timestamp": datetime.now().isoformat()
        }
    
    return router


if __name__ == "__main__":
    import asyncio
    
    # Example usage
    async def main():
        brain = CopilotAIBrain(
            openai_api_key="your-api-key",
            mcp_server_url="http://localhost:8000"
        )
        
        context = ConsultationContext(
            patient_id="P12345",
            procedure_code="3011",
            clinical_indication="CT Head - Severe headache, rule out pathology",
            consultation_type=ConsultationType.PREAUTHORIZATION
        )
        
        response = await brain.consult(
            "Should this CT scan be authorized for this patient?",
            context
        )
        
        print(f"✓ AI Response:\n{response}")
    
    asyncio.run(main())
