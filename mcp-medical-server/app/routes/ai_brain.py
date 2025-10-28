"""
AI Brain API Routes
Exposes AI-powered medical query processing via REST API
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.ai_brain_service import AIBrainService
from config.settings import Settings
import os

router = APIRouter()

# Initialize AI Brain (load API key from environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4")

if not OPENAI_API_KEY:
    print("⚠️  WARNING: OPENAI_API_KEY not set. AI Brain features disabled.")
    print("   Set OPENAI_API_KEY in .env to enable AI features")

ai_brain = AIBrainService(api_key=OPENAI_API_KEY, model=AI_MODEL) if OPENAI_API_KEY else None


# Request/Response Models

class QueryRequest(BaseModel):
    """Natural language medical query"""
    query: str
    context: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Is patient 1234567890 enrolled in Discovery?",
                "context": {"patient_id": "P12345"}
            }
        }


class OptimizePreAuthRequest(BaseModel):
    """Pre-authorization optimization request"""
    patient_id: str
    procedure: str
    clinical_indication: str
    context: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "patient_id": "P12345",
                "procedure": "CT Head",
                "clinical_indication": "Severe headache",
                "context": {
                    "age": 45,
                    "symptoms": "Acute onset, photophobia"
                }
            }
        }


class ConsultRequest(BaseModel):
    """Medical consultation request"""
    query: str
    context: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Should patient with severe headache get imaging?",
                "context": {
                    "patient_id": "P12345",
                    "age": 45,
                    "symptoms": "Severe headache, photophobia, neck stiffness"
                }
            }
        }


# API Endpoints

@router.post("/query", tags=["AI Brain"])
async def process_medical_query(request: QueryRequest):
    """
    Process natural language medical query using AI
    
    The AI Brain will:
    1. Understand your question
    2. Call appropriate MCP tools
    3. Combine results intelligently
    4. Return a comprehensive answer
    
    Example queries:
    - "Is patient 1234567890 enrolled in Discovery?"
    - "What will CT Head cost for member 1234567890?"
    - "Create pre-auth for patient 12345 for MRI Brain"
    """
    
    if not ai_brain:
        raise HTTPException(
            status_code=503,
            detail="AI Brain not configured. Set OPENAI_API_KEY in environment."
        )
    
    try:
        result = await ai_brain.process_query(request.query, request.context)
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")


@router.post("/optimize-preauth", tags=["AI Brain"])
async def optimize_preauth(request: OptimizePreAuthRequest):
    """
    Use AI to optimize pre-authorization justification
    
    The AI will:
    1. Analyze your clinical indication
    2. Add relevant medical context
    3. Cite guidelines when applicable
    4. Improve approval likelihood
    
    Returns:
    - Optimized clinical justification
    - Estimated approval likelihood (0.0-1.0)
    - Confidence score
    """
    
    if not ai_brain:
        raise HTTPException(
            status_code=503,
            detail="AI Brain not configured. Set OPENAI_API_KEY in environment."
        )
    
    try:
        result = await ai_brain.optimize_preauth(
            patient_id=request.patient_id,
            procedure=request.procedure,
            clinical_indication=request.clinical_indication,
            context=request.context
        )
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.post("/consult", tags=["AI Brain"])
async def medical_consultation(request: ConsultRequest):
    """
    Get AI medical consultation with clinical reasoning
    
    The AI will:
    1. Analyze the clinical scenario
    2. Provide evidence-based recommendations
    3. Consider patient context
    4. Flag any concerns
    
    Use this for:
    - Clinical decision support
    - Procedure recommendations
    - Risk assessment
    """
    
    if not ai_brain:
        raise HTTPException(
            status_code=503,
            detail="AI Brain not configured. Set OPENAI_API_KEY in environment."
        )
    
    try:
        result = await ai_brain.process_query(request.query, request.context)
        
        return {
            "consultation": result["response"],
            "confidence": result["confidence"],
            "tools_used": [t["tool"] for t in result.get("tool_results", [])],
            "timestamp": result["timestamp"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consultation failed: {str(e)}")


@router.get("/health", tags=["AI Brain"])
async def ai_brain_health():
    """
    Check if AI Brain is configured and operational
    """
    
    if not ai_brain:
        return {
            "status": "disabled",
            "message": "AI Brain not configured. Set OPENAI_API_KEY in environment.",
            "model": None
        }
    
    return {
        "status": "operational",
        "message": "AI Brain ready",
        "model": AI_MODEL,
        "tools_available": len(ai_brain.tools)
    }


@router.get("/tools", tags=["AI Brain"])
async def list_available_tools():
    """
    List all MCP tools available to the AI Brain
    """
    
    if not ai_brain:
        raise HTTPException(
            status_code=503,
            detail="AI Brain not configured"
        )
    
    return {
        "tools": ai_brain.tools,
        "count": len(ai_brain.tools)
    }
