"""
Granite-3.1 Integration for Medical Scheme Agent
Connects MCP tools to Granite-3.1-8B-Instruct LLM
Handles AI responses for healthcare automation
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger("GraniteIntegration")

# ============================================================================
# GRANITE INTEGRATION FOR MEDICAL SCHEME AGENT
# ============================================================================

class GraniteMedicalSchemeService:
    """
    Granite-3.1 service for Medical Scheme Agent
    Handles AI-powered healthcare administration automation
    """
    
    def __init__(self, model_path: str = None, config_path: str = None):
        """
        Initialize Granite service for medical scheme agent
        
        Args:
            model_path: Path to Granite model (auto-detected if not provided)
            config_path: Path to configuration file
        """
        self.model_path = model_path or self._find_granite_model()
        self.config_path = config_path or self._find_config()
        self.model_loaded = False
        self.model = None
        self.tokenizer = None
        
        logger.info("[Granite] Medical Scheme service initializing")
        logger.info(f"[Granite] Model path: {self.model_path}")
        logger.info(f"[Granite] Config path: {self.config_path}")
    
    def _find_granite_model(self) -> str:
        """Locate Granite model directory"""
        possible_paths = [
            "./models/granite-3.1-8b-instruct",
            "../../../models/granite-3.1-8b-instruct",
            "C:/models/granite-3.1-8b-instruct",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"[Granite] Found model at: {path}")
                return path
        
        logger.warning("[Granite] Model not found, will use online inference")
        return None
    
    def _find_config(self) -> str:
        """Locate configuration file"""
        possible_paths = [
            "./app/config.ini",
            "../../../app/config.ini",
            "C:/app/config.ini",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def load_model(self) -> bool:
        """
        Load Granite-3.1 model
        Returns True if successful, False otherwise
        """
        try:
            logger.info("[Granite] Loading model...")
            
            # Try to import transformers
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM
                import torch
            except ImportError:
                logger.error("[Granite] Required packages not installed")
                logger.info("[Granite] Run: pip install transformers torch")
                return False
            
            # Load model if path exists
            if self.model_path and os.path.exists(self.model_path):
                logger.info(f"[Granite] Loading from {self.model_path}")
                
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                
                # Auto-detect device
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"[Granite] Using device: {device}")
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    device_map="auto" if device == "cuda" else None,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                )
                
                self.model_loaded = True
                logger.info("[Granite] Model loaded successfully")
                return True
            else:
                logger.warning("[Granite] Model path not available")
                return False
                
        except Exception as e:
            logger.error(f"[Granite] Model loading failed: {str(e)}")
            return False
    
    def generate_response(self, prompt: str, 
                         max_tokens: int = 500,
                         temperature: float = 0.7,
                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate response using Granite-3.1
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            context: Additional context for response
            
        Returns:
            Generated response
        """
        logger.info("[Granite] Generating response...")
        
        if not self.model_loaded:
            logger.warning("[Granite] Model not loaded, using fallback response")
            return self._fallback_response(prompt, context)
        
        try:
            import torch
            
            # Build context-aware prompt
            full_prompt = self._build_prompt(prompt, context)
            
            # Tokenize
            inputs = self.tokenizer(full_prompt, return_tensors="pt")
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.95,
                    do_sample=True,
                )
            
            # Decode response
            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            logger.info("[Granite] Response generated successfully")
            
            return {
                "success": True,
                "response": response_text,
                "model": "Granite-3.1-8B-Instruct",
                "source": "local",
                "tokens_generated": len(outputs[0]),
            }
        
        except Exception as e:
            logger.error(f"[Granite] Generation error: {str(e)}")
            return self._fallback_response(prompt, context)
    
    def _build_prompt(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Build context-aware prompt for Granite"""
        
        system_prompt = """You are an intelligent medical scheme assistant powered by Granite-3.1-8B-Instruct.
Your role is to help healthcare providers navigate South African medical scheme portals efficiently.

Key capabilities:
- Check patient benefits and coverage
- Request authorizations for services
- Submit and track claims
- Compare medical schemes
- Provide healthcare tips and information

Important: Always be accurate, professional, and prioritize patient privacy.
Provide clear, actionable information to reduce administrative burden."""
        
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            prompt = f"{system_prompt}\n\nContext:\n{context_str}\n\nTask: {prompt}"
        else:
            prompt = f"{system_prompt}\n\nTask: {prompt}"
        
        return prompt
    
    def _fallback_response(self, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fallback response when model not available"""
        logger.info("[Granite] Using fallback response generator")
        
        # Analyze prompt to provide intelligent fallback
        prompt_lower = prompt.lower()
        
        responses = {
            "benefit": "To check benefits, please use the 'check_patient_coverage' tool with scheme, patient ID, and service details.",
            "authorization": "To request authorization, use the 'request_authorization' tool with clinical reason and doctor details.",
            "claim": "To submit a claim, use the 'submit_claim' tool with invoice reference and service details.",
            "coverage": "Coverage varies by medical scheme and plan. Use 'get_scheme_benefits' to view specific coverage.",
            "scheme": "South Africa has 71 registered medical schemes. Use 'search_scheme' or 'get_all_schemes' to find options.",
        }
        
        response = "I'm ready to help with medical scheme administration. Please specify your task."
        
        for keyword, fallback_response in responses.items():
            if keyword in prompt_lower:
                response = fallback_response
                break
        
        return {
            "success": True,
            "response": response,
            "model": "Granite-3.1-8B-Instruct (Fallback)",
            "source": "fallback",
            "note": "Model not loaded. Full Granite-3.1 capabilities will be available after model download.",
        }
    
    def process_medical_task(self, task_type: str, task_data: Dict[str, Any],
                            mcp_tools: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process medical administration task using Granite + MCP tools
        
        Args:
            task_type: Type of task (benefit_check, authorization, claim, etc.)
            task_data: Task-specific data
            mcp_tools: Dictionary of available MCP tools
            
        Returns:
            Task result with AI assistance
        """
        logger.info(f"[Granite] Processing task: {task_type}")
        
        # Build task-specific prompt
        if task_type == "benefit_check":
            return self._handle_benefit_check(task_data, mcp_tools)
        elif task_type == "authorization":
            return self._handle_authorization(task_data, mcp_tools)
        elif task_type == "claim_submission":
            return self._handle_claim_submission(task_data, mcp_tools)
        elif task_type == "scheme_comparison":
            return self._handle_scheme_comparison(task_data, mcp_tools)
        else:
            logger.warning(f"[Granite] Unknown task type: {task_type}")
            return {"success": False, "error": f"Unknown task type: {task_type}"}
    
    def _handle_benefit_check(self, task_data: Dict[str, Any], 
                             mcp_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Handle benefit check task"""
        logger.info("[Granite] Handling benefit check")
        
        scheme = task_data.get("scheme")
        patient_id = task_data.get("patient_id")
        service = task_data.get("service")
        
        # Call MCP tool
        coverage_result = mcp_tools.get("check_patient_coverage")(
            scheme=scheme,
            patient_id=patient_id,
            service=service
        )
        
        # Generate AI analysis
        context = {
            "scheme": scheme,
            "service": service,
            "coverage": coverage_result.get("coverage"),
            "limit": coverage_result.get("limit"),
        }
        
        ai_response = self.generate_response(
            f"Explain the coverage for {service} under {scheme}",
            context=context
        )
        
        return {
            "success": True,
            "task_type": "benefit_check",
            "coverage_data": coverage_result,
            "ai_summary": ai_response.get("response"),
            "timestamp": datetime.now().isoformat(),
        }
    
    def _handle_authorization(self, task_data: Dict[str, Any],
                             mcp_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authorization request task"""
        logger.info("[Granite] Handling authorization request")
        
        # Call MCP tool
        auth_result = mcp_tools.get("request_authorization")(
            scheme=task_data.get("scheme"),
            patient_id=task_data.get("patient_id"),
            service=task_data.get("service"),
            reason=task_data.get("reason"),
            doctor=task_data.get("doctor"),
        )
        
        # Generate AI confirmation
        ai_response = self.generate_response(
            f"Confirm authorization request for {task_data.get('service')}",
            context=auth_result
        )
        
        return {
            "success": True,
            "task_type": "authorization",
            "authorization_id": auth_result.get("authorization_id"),
            "status": auth_result.get("status"),
            "ai_confirmation": ai_response.get("response"),
            "timestamp": datetime.now().isoformat(),
        }
    
    def _handle_claim_submission(self, task_data: Dict[str, Any],
                                mcp_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Handle claim submission task"""
        logger.info("[Granite] Handling claim submission")
        
        # Call MCP tool
        claim_result = mcp_tools.get("submit_claim")(
            scheme=task_data.get("scheme"),
            patient_id=task_data.get("patient_id"),
            amount=task_data.get("amount"),
            service=task_data.get("service"),
            doctor=task_data.get("doctor"),
            invoice_ref=task_data.get("invoice_ref"),
        )
        
        # Generate AI summary
        ai_response = self.generate_response(
            f"Summarize claim submission of R{task_data.get('amount')} for {task_data.get('service')}",
            context=claim_result
        )
        
        return {
            "success": True,
            "task_type": "claim_submission",
            "claim_id": claim_result.get("claim_id"),
            "status": claim_result.get("status"),
            "ai_summary": ai_response.get("response"),
            "timestamp": datetime.now().isoformat(),
        }
    
    def _handle_scheme_comparison(self, task_data: Dict[str, Any],
                                 mcp_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scheme comparison task"""
        logger.info("[Granite] Handling scheme comparison")
        
        # Call MCP tool
        comparison_result = mcp_tools.get("compare_schemes")(
            schemes=task_data.get("schemes", []),
            criteria=task_data.get("criteria", "coverage"),
        )
        
        # Generate AI analysis
        ai_response = self.generate_response(
            f"Compare {', '.join(task_data.get('schemes', []))} based on {task_data.get('criteria', 'coverage')}",
            context=comparison_result
        )
        
        return {
            "success": True,
            "task_type": "scheme_comparison",
            "comparison": comparison_result.get("comparison"),
            "ai_analysis": ai_response.get("response"),
            "recommendation": comparison_result.get("recommendation"),
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# GRANITE SERVICE FACTORY
# ============================================================================

_granite_service = None

def get_granite_medical_service() -> GraniteMedicalSchemeService:
    """Get singleton Granite medical scheme service"""
    global _granite_service
    
    if _granite_service is None:
        _granite_service = GraniteMedicalSchemeService()
    
    return _granite_service

def init_granite_medical_service(model_path: str = None) -> GraniteMedicalSchemeService:
    """Initialize Granite medical scheme service"""
    global _granite_service
    
    _granite_service = GraniteMedicalSchemeService(model_path=model_path)
    
    # Try to load model
    if not _granite_service.load_model():
        logger.warning("[Granite] Model not loaded, will use fallback mode")
    
    return _granite_service


# ============================================================================
# DEMONSTRATION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧠 Granite-3.1 Integration for Medical Scheme Agent")
    print("="*70 + "\n")
    
    # Initialize service
    service = init_granite_medical_service()
    
    print("✅ Service initialized\n")
    
    # Test response generation
    print("Testing response generation:")
    print("-" * 70)
    
    test_prompts = [
        "How do I check if MRI is covered under Discovery Health?",
        "I need to request authorization for a specialist consultation",
        "What's the process for submitting a claim?",
    ]
    
    for prompt in test_prompts:
        print(f"\nPrompt: {prompt}")
        response = service.generate_response(prompt)
        print(f"Response: {response.get('response')[:100]}...")
    
    print("\n" + "="*70)
    print("Service ready for medical scheme agent operations")
    print("="*70 + "\n")
