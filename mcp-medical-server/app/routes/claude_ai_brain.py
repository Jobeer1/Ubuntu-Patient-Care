"""
API routes for Claude AI Brain integration
Provides intelligent medical analysis using AWS Bedrock Claude 4 Sonnet
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import logging
from app.services.claude_bedrock_service import ClaudeBedrockService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Claude service
claude_service = ClaudeBedrockService()

class AnalysisRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None

class PreAuthValidationRequest(BaseModel):
    patient_id: str
    member_number: str
    scheme_code: str
    procedure_code: str
    clinical_indication: str
    icd10_codes: Optional[List[str]] = None
    urgency: str = "routine"

class ProcedureAlternativeRequest(BaseModel):
    procedure_code: str
    clinical_indication: str

class ApprovalProbabilityRequest(BaseModel):
    member_data: Dict[str, Any]
    procedure_data: Dict[str, Any]

@router.get("/status")
async def get_claude_status():
    """Get Claude AI service status"""
    try:
        status = claude_service.get_service_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get Claude status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_medical_query(request: AnalysisRequest):
    """
    Analyze medical queries using Claude 4 Sonnet
    
    This endpoint provides intelligent medical analysis including:
    - Clinical assessment and recommendations
    - Risk factor analysis  
    - Pre-authorization requirements
    - Cost estimations
    - Regulatory compliance guidance
    """
    try:
        logger.info(f"Processing Claude analysis request: {request.query[:50]}...")
        
        result = await claude_service.analyze_medical_query(
            query=request.query,
            context=request.context
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Claude analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/validate-preauth")
async def validate_preauth_decision(request: PreAuthValidationRequest):
    """
    Use Claude to validate pre-authorization decisions
    
    Analyzes pre-authorization requests for:
    - Clinical appropriateness
    - ICD-10 code accuracy
    - Approval likelihood
    - Missing requirements
    - Risk assessment
    """
    try:
        preauth_data = {
            "patient_id": request.patient_id,
            "member_number": request.member_number,
            "scheme_code": request.scheme_code,
            "procedure_code": request.procedure_code,
            "clinical_indication": request.clinical_indication,
            "icd10_codes": request.icd10_codes or [],
            "urgency": request.urgency
        }
        
        result = await claude_service.validate_preauth_decision(preauth_data)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Validation failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pre-auth validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.post("/suggest-alternatives")
async def suggest_procedure_alternatives(request: ProcedureAlternativeRequest):
    """
    Suggest alternative procedures using Claude's medical knowledge
    
    Provides:
    - Cost-effective alternatives
    - Conservative treatment options
    - Required diagnostic procedures
    - Risk-benefit analysis
    - Approval rate estimates
    """
    try:
        result = await claude_service.suggest_procedure_alternatives(
            procedure_code=request.procedure_code,
            clinical_indication=request.clinical_indication
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Suggestion failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alternative suggestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Suggestion failed: {str(e)}")

@router.post("/estimate-approval-probability")
async def estimate_approval_probability(request: ApprovalProbabilityRequest):
    """
    Use Claude to estimate approval probability based on historical patterns
    
    Analyzes:
    - Member utilization patterns
    - Procedure approval rates
    - Clinical factors
    - Scheme-specific requirements
    - Processing timeframes
    """
    try:
        result = await claude_service.estimate_approval_probability(
            member_data=request.member_data,
            procedure_data=request.procedure_data
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Estimation failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approval probability estimation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Estimation failed: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint for Claude AI service"""
    try:
        status = claude_service.get_service_status()
        
        if status.get("client_initialized"):
            return {
                "status": "healthy",
                "service": "Claude AI Brain",
                "model": status.get("model_id"),
                "region": status.get("region"),
                "timestamp": status.get("timestamp")
            }
        else:
            return {
                "status": "unhealthy", 
                "service": "Claude AI Brain",
                "error": "Bedrock client not initialized",
                "timestamp": status.get("timestamp")
            }
            
    except Exception as e:
        logger.error(f"Claude health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "Claude AI Brain", 
            "error": str(e)
        }

# Enhanced medical analysis endpoints
@router.post("/clinical-decision-support")
async def clinical_decision_support(request: AnalysisRequest):
    """
    Provide clinical decision support using Claude AI
    
    Specialized for:
    - Treatment recommendations
    - Diagnostic pathways
    - Risk stratification
    - Evidence-based guidelines
    - Drug interactions and contraindications
    """
    try:
        # Enhance the query with clinical decision support context
        enhanced_query = f"""
        Clinical Decision Support Request:
        {request.query}
        
        Please provide:
        1. Evidence-based treatment recommendations
        2. Risk factors and contraindications
        3. Alternative treatment pathways
        4. Diagnostic considerations
        5. Follow-up recommendations
        6. Cost-effectiveness analysis
        7. Patient safety considerations
        
        Base recommendations on current South African clinical guidelines and international best practices.
        """
        
        result = await claude_service.analyze_medical_query(
            query=enhanced_query,
            context=request.context
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Clinical decision support failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Clinical decision support failed: {str(e)}")

@router.post("/regulatory-compliance-check")
async def regulatory_compliance_check(request: AnalysisRequest):
    """
    Check regulatory compliance using Claude AI
    
    Covers:
    - HPCSA guidelines
    - CMS requirements
    - Medical scheme regulations
    - Documentation standards
    - Audit trail requirements
    """
    try:
        enhanced_query = f"""
        Regulatory Compliance Analysis:
        {request.query}
        
        Please analyze compliance with:
        1. HPCSA (Health Professions Council of South Africa) guidelines
        2. CMS (Council for Medical Schemes) requirements
        3. Medical aid scheme specific regulations
        4. Documentation and record-keeping standards
        5. Patient privacy and consent requirements
        6. Audit trail and reporting obligations
        
        Identify any compliance gaps and provide remediation recommendations.
        """
        
        result = await claude_service.analyze_medical_query(
            query=enhanced_query,
            context=request.context
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Regulatory compliance check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Compliance check failed: {str(e)}")

@router.get("/analytics/usage")
async def get_usage_analytics():
    """Get Claude AI usage analytics"""
    try:
        # This would typically come from a database or monitoring service
        # For now, return mock data
        return {
            "total_queries": 1247,
            "queries_today": 89,
            "average_response_time": "2.3s",
            "success_rate": "98.2%",
            "most_common_topics": [
                {"topic": "Pre-authorization analysis", "count": 324},
                {"topic": "Clinical decision support", "count": 298},
                {"topic": "Cost estimation", "count": 267}, 
                {"topic": "Regulatory compliance", "count": 201},
                {"topic": "Alternative treatments", "count": 157}
            ],
            "claude_model": claude_service.model_id,
            "bedrock_region": claude_service.bedrock_region
        }
    except Exception as e:
        logger.error(f"Failed to get usage analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))