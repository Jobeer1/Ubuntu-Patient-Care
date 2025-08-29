"""
Offline Voice Command Processor for Medical Reporting Module
Handles voice commands for template selection and system control without internet
"""

import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class CommandType(Enum):
    """Voice command types"""
    TEMPLATE_LOAD = "template_load"
    NAVIGATION = "navigation"
    DICTATION_CONTROL = "dictation_control"
    SYSTEM_CONTROL = "system_control"
    QUICK_FILL = "quick_fill"

@dataclass
class VoiceCommand:
    """Voice command result"""
    command_id: str
    command_type: CommandType
    action: str
    parameter: Optional[str] = None
    template_id: Optional[str] = None
    confidence: float = 0.0
    original_text: str = ""

class OfflineVoiceCommandProcessor:
    """Processes voice commands offline for medical reporting"""
    
    def __init__(self):
        self.command_patterns: Dict[str, Dict[str, Any]] = {}
        self.template_mappings: Dict[str, str] = {}
        self.confidence_threshold = 0.7
        
        self._initialize_command_patterns()
        self._initialize_template_mappings()
        
        logger.info("Offline voice command processor initialized")
    
    def _initialize_command_patterns(self):
        """Initialize voice command patterns for offline recognition"""
        self.command_patterns = {
            # Template loading patterns
            "template_load": {
                "patterns": [
                    r"load\s+(.*?)\s+template",
                    r"use\s+(.*?)\s+template", 
                    r"open\s+(.*?)\s+template",
                    r"switch\s+to\s+(.*?)\s+template",
                    r"start\s+(.*?)\s+template",
                    r"begin\s+(.*?)\s+template"
                ],
                "command_type": CommandType.TEMPLATE_LOAD,
                "action": "load_template",
                "extract_parameter": True
            },
            
            # Navigation patterns
            "navigation": {
                "patterns": [
                    r"go\s+to\s+(.*?)(?:\s+section)?",
                    r"move\s+to\s+(.*?)(?:\s+section)?",
                    r"jump\s+to\s+(.*?)(?:\s+section)?",
                    r"navigate\s+to\s+(.*?)(?:\s+section)?",
                    r"show\s+(.*?)(?:\s+section)?"
                ],
                "command_type": CommandType.NAVIGATION,
                "action": "navigate_section",
                "extract_parameter": True
            },
            
            # Dictation control patterns
            "dictation_control": {
                "patterns": [
                    r"(start|begin|resume)\s+dictation",
                    r"(stop|end|finish)\s+dictation",
                    r"(pause|hold)\s+dictation",
                    r"(clear|delete)\s+dictation"
                ],
                "command_type": CommandType.DICTATION_CONTROL,
                "action": "dictation_control",
                "extract_parameter": True
            },
            
            # System control patterns
            "system_control": {
                "patterns": [
                    r"(save|store)\s+report",
                    r"(submit|send)\s+report",
                    r"(delete|remove)\s+report",
                    r"(new|create)\s+report",
                    r"(undo|revert)\s+last",
                    r"(repeat|say\s+again)\s+last"
                ],
                "command_type": CommandType.SYSTEM_CONTROL,
                "action": "system_control",
                "extract_parameter": True
            },
            
            # Quick fill patterns for common medical phrases
            "quick_fill": {
                "patterns": [
                    r"normal\s+(.*?)(?:\s+study|\s+exam|\s+examination)?",
                    r"no\s+acute\s+(.*?)",
                    r"within\s+normal\s+limits",
                    r"unremarkable\s+(.*?)",
                    r"consistent\s+with\s+(.*?)",
                    r"suggestive\s+of\s+(.*?)",
                    r"impression\s+(.*?)",
                    r"findings\s+(.*?)"
                ],
                "command_type": CommandType.QUICK_FILL,
                "action": "quick_fill",
                "extract_parameter": True
            }
        }
    
    def _initialize_template_mappings(self):
        """Initialize template name mappings for South African medical context"""
        self.template_mappings = {
            # Chest imaging (high priority in SA due to TB)
            "chest x-ray": "chest_xray_template",
            "chest xray": "chest_xray_template", 
            "cxr": "chest_xray_template",
            "chest radiograph": "chest_xray_template",
            "chest film": "chest_xray_template",
            
            "ct chest": "ct_chest_template",
            "chest ct": "ct_chest_template",
            "computed tomography chest": "ct_chest_template",
            "chest scan": "ct_chest_template",
            
            # TB screening (very important in SA)
            "tb screening": "tb_screening_template",
            "tuberculosis": "tb_screening_template",
            "tb study": "tb_screening_template",
            "tuberculosis screening": "tb_screening_template",
            
            # Occupational lung disease (mining context)
            "silicosis": "silicosis_template",
            "pneumoconiosis": "pneumoconiosis_template",
            "dust lung": "pneumoconiosis_template",
            "miners lung": "silicosis_template",
            "occupational lung": "pneumoconiosis_template",
            
            # Abdominal imaging
            "abdominal x-ray": "abdominal_xray_template",
            "abd xray": "abdominal_xray_template",
            "kub": "kub_template",
            "kidney ureter bladder": "kub_template",
            
            "ct abdomen": "ct_abdomen_template",
            "abdominal ct": "ct_abdomen_template",
            "ct pelvis": "ct_pelvis_template",
            
            # Musculoskeletal (trauma common in SA)
            "bone x-ray": "bone_xray_template",
            "orthopedic": "orthopedic_template",
            "fracture": "fracture_template",
            "trauma": "trauma_template",
            "accident": "trauma_template",
            
            # Neurological
            "ct head": "ct_head_template",
            "head ct": "ct_head_template",
            "brain ct": "ct_brain_template",
            "ct brain": "ct_brain_template",
            
            # Cardiac
            "chest pain": "chest_pain_template",
            "cardiac": "cardiac_template",
            "heart": "cardiac_template",
            
            # General templates
            "general": "general_template",
            "basic": "basic_template",
            "standard": "standard_template"
        }
    
    def process_command(self, text: str) -> Optional[VoiceCommand]:
        """Process text for voice commands offline"""
        try:
            text_lower = text.lower().strip()
            
            # Remove common filler words that might interfere
            text_lower = re.sub(r'\b(um|uh|er|ah)\b', '', text_lower)
            text_lower = re.sub(r'\s+', ' ', text_lower).strip()
            
            for command_group, config in self.command_patterns.items():
                for pattern in config["patterns"]:
                    match = re.search(pattern, text_lower)
                    if match:
                        command = VoiceCommand(
                            command_id=str(uuid.uuid4()),
                            command_type=config["command_type"],
                            action=config["action"],
                            original_text=text,
                            confidence=0.9  # High confidence for pattern matches
                        )
                        
                        if config.get("extract_parameter") and match.groups():
                            parameter = match.group(1).strip()
                            command.parameter = parameter
                            
                            # Map template names for template loading commands
                            if command.command_type == CommandType.TEMPLATE_LOAD:
                                template_id = self._find_template_match(parameter)
                                if template_id:
                                    command.template_id = template_id
                                    command.confidence = 0.95  # Higher confidence for known templates
                        
                        logger.info(f"Detected offline voice command: {command.action} - {command.parameter}")
                        return command
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to process voice command offline: {e}")
            return None
    
    def _find_template_match(self, parameter: str) -> Optional[str]:
        """Find best template match for parameter"""
        try:
            parameter_lower = parameter.lower().strip()
            
            # Direct match
            if parameter_lower in self.template_mappings:
                return self.template_mappings[parameter_lower]
            
            # Partial match - find best match
            best_match = None
            best_score = 0
            
            for template_name, template_id in self.template_mappings.items():
                # Check if parameter contains template name words
                template_words = template_name.split()
                parameter_words = parameter_lower.split()
                
                matches = sum(1 for word in template_words if word in parameter_words)
                score = matches / len(template_words)
                
                if score > best_score and score >= 0.5:  # At least 50% word match
                    best_score = score
                    best_match = template_id
            
            return best_match
            
        except Exception as e:
            logger.error(f"Failed to find template match: {e}")
            return None
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get list of available templates for voice commands"""
        try:
            templates = []
            for template_name, template_id in self.template_mappings.items():
                templates.append({
                    "name": template_name,
                    "id": template_id,
                    "command_example": f"Load {template_name} template"
                })
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get available templates: {e}")
            return []
    
    def get_command_examples(self) -> List[Dict[str, Any]]:
        """Get examples of voice commands"""
        try:
            examples = []
            
            # Template loading examples
            examples.extend([
                {"command": "Load chest x-ray template", "type": "Template Loading"},
                {"command": "Use TB screening template", "type": "Template Loading"},
                {"command": "Open fracture template", "type": "Template Loading"}
            ])
            
            # Navigation examples
            examples.extend([
                {"command": "Go to findings section", "type": "Navigation"},
                {"command": "Move to impression", "type": "Navigation"},
                {"command": "Jump to conclusion", "type": "Navigation"}
            ])
            
            # Dictation control examples
            examples.extend([
                {"command": "Start dictation", "type": "Dictation Control"},
                {"command": "Stop dictation", "type": "Dictation Control"},
                {"command": "Pause dictation", "type": "Dictation Control"}
            ])
            
            # System control examples
            examples.extend([
                {"command": "Save report", "type": "System Control"},
                {"command": "Submit report", "type": "System Control"},
                {"command": "New report", "type": "System Control"}
            ])
            
            # Quick fill examples
            examples.extend([
                {"command": "Normal chest study", "type": "Quick Fill"},
                {"command": "No acute findings", "type": "Quick Fill"},
                {"command": "Within normal limits", "type": "Quick Fill"}
            ])
            
            return examples
            
        except Exception as e:
            logger.error(f"Failed to get command examples: {e}")
            return []
    
    def add_custom_template(self, template_name: str, template_id: str) -> bool:
        """Add a custom template mapping"""
        try:
            template_name_lower = template_name.lower().strip()
            self.template_mappings[template_name_lower] = template_id
            
            logger.info(f"Added custom template mapping: '{template_name}' -> '{template_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add custom template: {e}")
            return False
    
    def remove_template(self, template_name: str) -> bool:
        """Remove a template mapping"""
        try:
            template_name_lower = template_name.lower().strip()
            if template_name_lower in self.template_mappings:
                del self.template_mappings[template_name_lower]
                logger.info(f"Removed template mapping: '{template_name}'")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove template: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get command processor statistics"""
        try:
            return {
                "total_command_patterns": sum(len(config["patterns"]) for config in self.command_patterns.values()),
                "template_mappings": len(self.template_mappings),
                "confidence_threshold": self.confidence_threshold,
                "command_types": [ct.value for ct in CommandType]
            }
            
        except Exception as e:
            logger.error(f"Failed to get command processor stats: {e}")
            return {}

# Global offline voice command processor instance
offline_voice_commands = OfflineVoiceCommandProcessor()