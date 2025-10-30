"""
AWS Bedrock Integration Service for Claude 4 Sonnet
Provides intelligent medical AI brain functionality
"""

import boto3
import json
import configparser
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ClaudeBedrockService:
    """Claude 4 Sonnet integration via AWS Bedrock"""
    
    def __init__(self, config_path: str = None):
        self.config = configparser.ConfigParser()
        
        if config_path and os.path.exists(config_path):
            self.config.read(config_path)
        else:
            # Default config from environment or hardcoded values
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'aws_config.ini')
            if os.path.exists(config_path):
                self.config.read(config_path)
        
        # AWS Configuration
        self.aws_access_key = self.config.get('AWS', 'aws_access_key_id', fallback=os.getenv('AWS_ACCESS_KEY_ID'))
        self.aws_secret_key = self.config.get('AWS', 'aws_secret_access_key', fallback=os.getenv('AWS_SECRET_ACCESS_KEY'))
        self.aws_region = self.config.get('AWS', 'aws_region', fallback='us-east-1')
        
        # Bedrock Configuration
        self.model_id = self.config.get('AWS', 'bedrock_model_id', fallback='us.anthropic.claude-sonnet-4-20250514-v1:0')
        self.bedrock_region = self.config.get('AWS', 'bedrock_region', fallback='us-east-1')
        self.max_tokens = self.config.getint('AWS', 'bedrock_max_tokens', fallback=4096)
        self.temperature = self.config.getfloat('AWS', 'bedrock_temperature', fallback=0.1)
        
        # Initialize Bedrock client
        self._init_bedrock_client()
        
    def _init_bedrock_client(self):
        """Initialize AWS Bedrock client"""
        try:
            session = boto3.Session(
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.bedrock_region
            )
            
            self.bedrock_client = session.client(
                service_name='bedrock-runtime',
                region_name=self.bedrock_region
            )
            
            logger.info(f"✅ AWS Bedrock client initialized successfully for region: {self.bedrock_region}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Bedrock client: {str(e)}")
            self.bedrock_client = None
    
    async def analyze_medical_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze medical queries using Claude 4 Sonnet
        
        Args:
            query: The medical question or request
            context: Additional context (patient data, procedure info, etc.)
            
        Returns:
            Dict with analysis results, recommendations, and confidence scores
        """
        
        if not self.bedrock_client:
            return {
                "error": "Bedrock client not initialized",
                "status": "error",
                "recommendation": "Check AWS credentials and connection"
            }
        
        try:
            # Build the prompt for Claude
            system_prompt = """You are an expert medical AI assistant specializing in South African healthcare systems, medical aid schemes, and clinical decision support. 

Your expertise includes:
- South African medical aid schemes (Discovery, Momentum, Bonitas, etc.)
- NRPL procedure codes and ICD-10 classifications
- Pre-authorization requirements and processes
- Clinical protocols and best practices
- Cost estimation and benefit calculations
- Regulatory compliance (HPCSA, CMS guidelines)

Provide accurate, evidence-based responses with:
1. Clear recommendations
2. Confidence levels (0-100%)
3. Risk assessments
4. Next steps or actions needed
5. Compliance considerations

Always prioritize patient safety and regulatory compliance."""

            user_prompt = f"""
Medical Query: {query}

Context Information:
{json.dumps(context, indent=2) if context else "No additional context provided"}

Please analyze this medical query and provide:
1. Clinical assessment
2. Recommendations  
3. Risk factors
4. Pre-authorization requirements (if applicable)
5. Estimated costs (if applicable)
6. Confidence score (0-100%)

Format your response as structured JSON.
"""

            # Prepare the request body for Claude 4 Sonnet
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            }
            
            # Make the API call to Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse the response
            response_body = json.loads(response['body'].read())
            
            # Extract Claude's response
            claude_response = response_body.get('content', [{}])[0].get('text', '')
            
            # Try to parse as JSON, fallback to text response
            try:
                parsed_response = json.loads(claude_response)
            except json.JSONDecodeError:
                parsed_response = {
                    "analysis": claude_response,
                    "confidence": 85,
                    "status": "success"
                }
            
            # Add metadata
            parsed_response.update({
                "timestamp": datetime.now().isoformat(),
                "model": self.model_id,
                "query": query,
                "status": "success"
            })
            
            logger.info(f"✅ Claude analysis completed successfully for query: {query[:50]}...")
            return parsed_response
            
        except Exception as e:
            logger.error(f"❌ Claude analysis failed: {str(e)}")
            return {
                "error": str(e),
                "status": "error",
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "recommendation": "Please check your AWS Bedrock configuration and try again"
            }
    
    async def validate_preauth_decision(self, preauth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Claude to validate pre-authorization decisions
        
        Args:
            preauth_data: Pre-authorization request data
            
        Returns:
            Validation results with recommendations
        """
        
        query = f"""
        Validate this pre-authorization request:
        
        Patient: {preauth_data.get('patient_id', 'Unknown')}
        Procedure: {preauth_data.get('procedure_code', 'Unknown')}
        Clinical Indication: {preauth_data.get('clinical_indication', 'Not provided')}
        Scheme: {preauth_data.get('scheme_code', 'Unknown')}
        Urgency: {preauth_data.get('urgency', 'routine')}
        ICD-10 Codes: {', '.join(preauth_data.get('icd10_codes', []))}
        
        Please validate:
        1. Is the clinical indication appropriate for the procedure?
        2. Are the ICD-10 codes correctly matched?
        3. What is the likelihood of approval?
        4. Are there any missing requirements?
        5. Risk assessment and recommendations
        """
        
        return await self.analyze_medical_query(query, preauth_data)
    
    async def suggest_procedure_alternatives(self, procedure_code: str, clinical_indication: str) -> Dict[str, Any]:
        """
        Suggest alternative procedures using Claude's medical knowledge
        
        Args:
            procedure_code: NRPL procedure code
            clinical_indication: Clinical reason for procedure
            
        Returns:
            Alternative procedures and recommendations
        """
        
        query = f"""
        For procedure code {procedure_code} with clinical indication: {clinical_indication}
        
        Please suggest:
        1. Alternative procedures that might be more cost-effective
        2. Conservative treatment options
        3. Diagnostic procedures that should be done first
        4. Risk-benefit analysis of each option
        5. Typical approval rates for each alternative
        
        Consider South African medical aid scheme preferences and cost constraints.
        """
        
        return await self.analyze_medical_query(query, {
            "procedure_code": procedure_code,
            "clinical_indication": clinical_indication
        })
    
    async def estimate_approval_probability(self, member_data: Dict[str, Any], procedure_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Claude to estimate approval probability based on historical patterns
        
        Args:
            member_data: Member information (scheme, plan, utilization)
            procedure_data: Procedure information
            
        Returns:
            Probability estimates and factors affecting approval
        """
        
        query = f"""
        Estimate approval probability for this pre-authorization:
        
        Member Details:
        - Scheme: {member_data.get('scheme_code', 'Unknown')}
        - Plan: {member_data.get('plan_code', 'Unknown')}
        - Annual Utilization: {member_data.get('annual_utilization', 'Unknown')}
        
        Procedure Details:
        - Code: {procedure_data.get('procedure_code', 'Unknown')}
        - Cost: R{procedure_data.get('estimated_cost', 'Unknown')}
        - Urgency: {procedure_data.get('urgency', 'routine')}
        - Clinical Indication: {procedure_data.get('clinical_indication', 'Not provided')}
        
        Please provide:
        1. Approval probability (0-100%)
        2. Key factors affecting approval
        3. Strategies to improve approval chances  
        4. Typical processing time
        5. Alternative approaches if likely to be rejected
        """
        
        context = {**member_data, **procedure_data}
        return await self.analyze_medical_query(query, context)
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the Claude Bedrock service"""
        
        return {
            "service": "Claude 4 Sonnet via AWS Bedrock",
            "model_id": self.model_id,
            "region": self.bedrock_region,
            "client_initialized": self.bedrock_client is not None,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "status": "ready" if self.bedrock_client else "error"
        }