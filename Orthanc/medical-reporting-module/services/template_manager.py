"""
Template Manager for Medical Reporting Module
Manages report templates with CRUD operations, categorization, and voice command integration
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import re

from models.template import ReportTemplate
from models.database import get_db_session

logger = logging.getLogger(__name__)

class TemplateCategory(Enum):
    """Template categories by medical specialty"""
    GENERAL_RADIOLOGY = "general_radiology"
    CHEST_IMAGING = "chest_imaging"
    ABDOMINAL_IMAGING = "abdominal_imaging"
    MUSCULOSKELETAL = "musculoskeletal"
    NEUROIMAGING = "neuroimaging"
    CARDIAC_IMAGING = "cardiac_imaging"
    PEDIATRIC_IMAGING = "pediatric_imaging"
    INTERVENTIONAL = "interventional"
    MAMMOGRAPHY = "mammography"
    NUCLEAR_MEDICINE = "nuclear_medicine"
    ULTRASOUND = "ultrasound"
    CUSTOM = "custom"

class TemplateType(Enum):
    """Types of report templates"""
    STRUCTURED = "structured"
    FREE_TEXT = "free_text"
    HYBRID = "hybrid"
    CHECKLIST = "checklist"

class FieldType(Enum):
    """Types of template fields"""
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    MULTISELECT = "multiselect"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    MEASUREMENT = "measurement"
    IMPRESSION = "impression"
    RECOMMENDATION = "recommendation"

@dataclass
class TemplateField:
    """Individual field in a template"""
    field_id: str
    field_name: str
    field_type: FieldType
    label: str
    description: str = ""
    required: bool = False
    default_value: Any = None
    options: List[str] = field(default_factory=list)  # For select/radio fields
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    voice_commands: List[str] = field(default_factory=list)  # Voice commands for this field
    order_index: int = 0
    section: str = "main"
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TemplateSection:
    """Section within a template"""
    section_id: str
    section_name: str
    title: str
    description: str = ""
    fields: List[TemplateField] = field(default_factory=list)
    order_index: int = 0
    is_collapsible: bool = True
    is_expanded: bool = True
    voice_commands: List[str] = field(default_factory=list)

@dataclass
class VoiceCommand:
    """Voice command configuration"""
    command_id: str
    command_text: str
    command_variations: List[str] = field(default_factory=list)
    action_type: str = "load_template"  # load_template, fill_field, navigate_section
    target_id: str = ""  # template_id, field_id, or section_id
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence_threshold: float = 0.8

@dataclass
class TemplateConfiguration:
    """Complete template configuration"""
    template_id: str
    name: str
    category: TemplateCategory
    template_type: TemplateType
    description: str = ""
    specialty: str = ""
    procedure_type: str = ""
    sections: List[TemplateSection] = field(default_factory=list)
    voice_commands: List[VoiceCommand] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    default_content: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    is_shared: bool = False
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    usage_count: int = 0
    
    def __post_init__(self):
        if not self.template_id:
            self.template_id = str(uuid.uuid4())

class TemplateManager:
    """Manages report templates with CRUD operations and voice integration"""
    
    def __init__(self):
        self.templates: Dict[str, TemplateConfiguration] = {}
        self.categories: Dict[TemplateCategory, List[str]] = {}
        self.voice_commands: Dict[str, VoiceCommand] = {}
        
        # Event callbacks
        self.template_change_callbacks: List[Callable] = []
        self.voice_command_callbacks: List[Callable] = []
        
        # Search and filtering
        self.search_index: Dict[str, List[str]] = {}  # keyword -> template_ids
        self.category_index: Dict[TemplateCategory, List[str]] = {}
        
        # Initialize default templates
        self._create_default_templates()
        self._build_search_index()
    
    def _create_default_templates(self):
        """Create default report templates for common procedures"""
        
        # Chest X-Ray Template
        chest_xray_sections = [
            TemplateSection(
                section_id="clinical_info",
                section_name="clinical_info",
                title="Clinical Information",
                fields=[
                    TemplateField(
                        field_id="clinical_history",
                        field_name="clinical_history",
                        field_type=FieldType.TEXTAREA,
                        label="Clinical History",
                        description="Patient's clinical history and indication for study",
                        required=True,
                        voice_commands=["clinical history", "history", "indication"]
                    ),
                    TemplateField(
                        field_id="age",
                        field_name="age",
                        field_type=FieldType.NUMBER,
                        label="Patient Age",
                        validation_rules={"min": 0, "max": 150},
                        voice_commands=["age", "patient age"]
                    )
                ],
                order_index=0
            ),
            TemplateSection(
                section_id="technique",
                section_name="technique",
                title="Technique",
                fields=[
                    TemplateField(
                        field_id="views",
                        field_name="views",
                        field_type=FieldType.SELECT,
                        label="Views Obtained",
                        options=["PA and lateral", "PA only", "AP portable", "Lateral only"],
                        default_value="PA and lateral",
                        voice_commands=["views", "projections", "technique"]
                    ),
                    TemplateField(
                        field_id="quality",
                        field_name="quality",
                        field_type=FieldType.SELECT,
                        label="Image Quality",
                        options=["Adequate", "Limited", "Poor"],
                        default_value="Adequate",
                        voice_commands=["quality", "image quality"]
                    )
                ],
                order_index=1
            ),
            TemplateSection(
                section_id="findings",
                section_name="findings",
                title="Findings",
                fields=[
                    TemplateField(
                        field_id="lungs",
                        field_name="lungs",
                        field_type=FieldType.TEXTAREA,
                        label="Lungs",
                        description="Lung parenchyma findings",
                        default_value="The lungs are clear bilaterally.",
                        voice_commands=["lungs", "lung fields", "parenchyma"]
                    ),
                    TemplateField(
                        field_id="heart",
                        field_name="heart",
                        field_type=FieldType.TEXTAREA,
                        label="Heart",
                        description="Cardiac silhouette findings",
                        default_value="The cardiac silhouette is normal in size and configuration.",
                        voice_commands=["heart", "cardiac", "cardiac silhouette"]
                    ),
                    TemplateField(
                        field_id="mediastinum",
                        field_name="mediastinum",
                        field_type=FieldType.TEXTAREA,
                        label="Mediastinum",
                        default_value="The mediastinum is normal.",
                        voice_commands=["mediastinum", "mediastinal"]
                    ),
                    TemplateField(
                        field_id="bones",
                        field_name="bones",
                        field_type=FieldType.TEXTAREA,
                        label="Bones",
                        default_value="No acute osseous abnormality.",
                        voice_commands=["bones", "osseous", "skeletal"]
                    )
                ],
                order_index=2
            ),
            TemplateSection(
                section_id="impression",
                section_name="impression",
                title="Impression",
                fields=[
                    TemplateField(
                        field_id="impression_text",
                        field_name="impression_text",
                        field_type=FieldType.IMPRESSION,
                        label="Impression",
                        description="Final impression and diagnosis",
                        required=True,
                        default_value="Normal chest radiograph.",
                        voice_commands=["impression", "diagnosis", "conclusion"]
                    )
                ],
                order_index=3
            )
        ]
        
        chest_xray_voice_commands = [
            VoiceCommand(
                command_id="load_chest_xray",
                command_text="chest x-ray template",
                command_variations=["chest xray", "chest radiograph", "cxr template"],
                action_type="load_template",
                target_id="chest_xray_template"
            ),
            VoiceCommand(
                command_id="normal_chest",
                command_text="normal chest",
                command_variations=["normal study", "normal examination"],
                action_type="fill_template",
                target_id="chest_xray_template",
                parameters={
                    "lungs": "The lungs are clear bilaterally.",
                    "heart": "The cardiac silhouette is normal in size and configuration.",
                    "mediastinum": "The mediastinum is normal.",
                    "bones": "No acute osseous abnormality.",
                    "impression_text": "Normal chest radiograph."
                }
            )
        ]
        
        chest_xray_template = TemplateConfiguration(
            template_id="chest_xray_template",
            name="Chest X-Ray",
            category=TemplateCategory.CHEST_IMAGING,
            template_type=TemplateType.STRUCTURED,
            description="Standard chest radiograph reporting template",
            specialty="Radiology",
            procedure_type="Chest X-Ray",
            sections=chest_xray_sections,
            voice_commands=chest_xray_voice_commands,
            tags=["chest", "xray", "radiograph", "thorax"],
            is_shared=True
        )
        
        self.templates[chest_xray_template.template_id] = chest_xray_template
        
        # CT Chest Template
        ct_chest_sections = [
            TemplateSection(
                section_id="clinical_info",
                section_name="clinical_info",
                title="Clinical Information",
                fields=[
                    TemplateField(
                        field_id="clinical_history",
                        field_name="clinical_history",
                        field_type=FieldType.TEXTAREA,
                        label="Clinical History",
                        required=True,
                        voice_commands=["clinical history", "history", "indication"]
                    ),
                    TemplateField(
                        field_id="contrast",
                        field_name="contrast",
                        field_type=FieldType.SELECT,
                        label="Contrast Administration",
                        options=["IV contrast", "No contrast", "Oral and IV contrast"],
                        voice_commands=["contrast", "iv contrast", "oral contrast"]
                    )
                ],
                order_index=0
            ),
            TemplateSection(
                section_id="findings",
                section_name="findings",
                title="Findings",
                fields=[
                    TemplateField(
                        field_id="lungs_ct",
                        field_name="lungs_ct",
                        field_type=FieldType.TEXTAREA,
                        label="Lungs and Airways",
                        default_value="The lungs are clear without focal consolidation, mass, or nodule.",
                        voice_commands=["lungs", "airways", "pulmonary"]
                    ),
                    TemplateField(
                        field_id="mediastinum_ct",
                        field_name="mediastinum_ct",
                        field_type=FieldType.TEXTAREA,
                        label="Mediastinum and Hila",
                        default_value="The mediastinum and hila are normal.",
                        voice_commands=["mediastinum", "hila", "hilar"]
                    ),
                    TemplateField(
                        field_id="pleura",
                        field_name="pleura",
                        field_type=FieldType.TEXTAREA,
                        label="Pleura",
                        default_value="No pleural effusion or pneumothorax.",
                        voice_commands=["pleura", "pleural"]
                    )
                ],
                order_index=1
            ),
            TemplateSection(
                section_id="impression",
                section_name="impression",
                title="Impression",
                fields=[
                    TemplateField(
                        field_id="impression_text",
                        field_name="impression_text",
                        field_type=FieldType.IMPRESSION,
                        label="Impression",
                        required=True,
                        default_value="Normal CT chest.",
                        voice_commands=["impression", "diagnosis", "conclusion"]
                    )
                ],
                order_index=2
            )
        ]
        
        ct_chest_template = TemplateConfiguration(
            template_id="ct_chest_template",
            name="CT Chest",
            category=TemplateCategory.CHEST_IMAGING,
            template_type=TemplateType.STRUCTURED,
            description="CT chest reporting template",
            specialty="Radiology",
            procedure_type="CT Chest",
            sections=ct_chest_sections,
            voice_commands=[
                VoiceCommand(
                    command_id="load_ct_chest",
                    command_text="ct chest template",
                    command_variations=["ct thorax", "chest ct"],
                    action_type="load_template",
                    target_id="ct_chest_template"
                )
            ],
            tags=["ct", "chest", "thorax", "computed tomography"],
            is_shared=True
        )
        
        self.templates[ct_chest_template.template_id] = ct_chest_template
        
        # Abdominal X-Ray Template
        abd_xray_template = TemplateConfiguration(
            template_id="abd_xray_template",
            name="Abdominal X-Ray",
            category=TemplateCategory.ABDOMINAL_IMAGING,
            template_type=TemplateType.STRUCTURED,
            description="Abdominal radiograph reporting template",
            specialty="Radiology",
            procedure_type="Abdominal X-Ray",
            sections=[
                TemplateSection(
                    section_id="findings",
                    section_name="findings",
                    title="Findings",
                    fields=[
                        TemplateField(
                            field_id="bowel_gas",
                            field_name="bowel_gas",
                            field_type=FieldType.TEXTAREA,
                            label="Bowel Gas Pattern",
                            default_value="Normal bowel gas pattern.",
                            voice_commands=["bowel gas", "gas pattern"]
                        ),
                        TemplateField(
                            field_id="organs",
                            field_name="organs",
                            field_type=FieldType.TEXTAREA,
                            label="Organs",
                            default_value="Visualized organs appear normal.",
                            voice_commands=["organs", "solid organs"]
                        )
                    ]
                )
            ],
            voice_commands=[
                VoiceCommand(
                    command_id="load_abd_xray",
                    command_text="abdominal x-ray template",
                    command_variations=["abd xray", "abdominal radiograph"],
                    action_type="load_template",
                    target_id="abd_xray_template"
                )
            ],
            tags=["abdomen", "xray", "kub"],
            is_shared=True
        )
        
        self.templates[abd_xray_template.template_id] = abd_xray_template
        
        logger.info(f"Created {len(self.templates)} default templates")
    
    def _build_search_index(self):
        """Build search index for templates"""
        try:
            self.search_index.clear()
            self.category_index.clear()
            
            for template_id, template in self.templates.items():
                # Index by category
                if template.category not in self.category_index:
                    self.category_index[template.category] = []
                self.category_index[template.category].append(template_id)
                
                # Index searchable terms
                searchable_terms = [
                    template.name.lower(),
                    template.description.lower(),
                    template.specialty.lower(),
                    template.procedure_type.lower()
                ]
                
                # Add tags
                searchable_terms.extend([tag.lower() for tag in template.tags])
                
                # Add voice commands
                for voice_cmd in template.voice_commands:
                    searchable_terms.append(voice_cmd.command_text.lower())
                    searchable_terms.extend([var.lower() for var in voice_cmd.command_variations])
                
                # Add field names and labels
                for section in template.sections:
                    for field in section.fields:
                        searchable_terms.append(field.field_name.lower())
                        searchable_terms.append(field.label.lower())
                
                # Index all terms
                for term in searchable_terms:
                    if term:
                        words = re.findall(r'\w+', term)
                        for word in words:
                            if word not in self.search_index:
                                self.search_index[word] = []
                            if template_id not in self.search_index[word]:
                                self.search_index[word].append(template_id)
            
            logger.debug(f"Built search index with {len(self.search_index)} terms")
            
        except Exception as e:
            logger.error(f"Failed to build search index: {e}")
    
    def create_template(self, name: str, category: TemplateCategory, 
                       template_type: TemplateType = TemplateType.STRUCTURED,
                       created_by: Optional[str] = None) -> TemplateConfiguration:
        """Create a new template"""
        try:
            template = TemplateConfiguration(
                template_id=str(uuid.uuid4()),
                name=name,
                category=category,
                template_type=template_type,
                created_by=created_by
            )
            
            self.templates[template.template_id] = template
            self._build_search_index()
            
            # Notify callbacks
            self._notify_template_change('created', template)
            
            logger.info(f"Created template: {name}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            raise
    
    def get_template(self, template_id: str) -> Optional[TemplateConfiguration]:
        """Get a template by ID"""
        return self.templates.get(template_id)
    
    def load_template(self, template_id: str) -> Optional[TemplateConfiguration]:
        """Load a template by ID (alias for get_template)"""
        return self.get_template(template_id)
    
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """Update a template"""
        try:
            template = self.templates.get(template_id)
            if not template:
                logger.error(f"Template not found: {template_id}")
                return False
            
            # Update fields
            for field, value in updates.items():
                if hasattr(template, field):
                    setattr(template, field, value)
            
            template.modified_at = datetime.utcnow()
            template.version += 1
            
            self._build_search_index()
            
            # Notify callbacks
            self._notify_template_change('updated', template)
            
            logger.info(f"Updated template: {template.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update template: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template"""
        try:
            template = self.templates.get(template_id)
            if not template:
                logger.error(f"Template not found: {template_id}")
                return False
            
            # Remove from templates
            del self.templates[template_id]
            
            # Remove voice commands
            voice_cmd_ids_to_remove = []
            for cmd_id, voice_cmd in self.voice_commands.items():
                if voice_cmd.target_id == template_id:
                    voice_cmd_ids_to_remove.append(cmd_id)
            
            for cmd_id in voice_cmd_ids_to_remove:
                del self.voice_commands[cmd_id]
            
            self._build_search_index()
            
            # Notify callbacks
            self._notify_template_change('deleted', template)
            
            logger.info(f"Deleted template: {template.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete template: {e}")
            return False
    
    def search_templates(self, query: str, category: Optional[TemplateCategory] = None,
                        specialty: Optional[str] = None, limit: int = 50) -> List[TemplateConfiguration]:
        """Search templates by query"""
        try:
            if not query.strip():
                return self.get_all_templates(category, specialty, limit)
            
            # Find matching template IDs
            query_words = re.findall(r'\w+', query.lower())
            matching_template_ids = set()
            
            for word in query_words:
                if word in self.search_index:
                    if not matching_template_ids:
                        matching_template_ids = set(self.search_index[word])
                    else:
                        matching_template_ids &= set(self.search_index[word])
            
            # Filter by category and specialty
            results = []
            for template_id in matching_template_ids:
                template = self.templates.get(template_id)
                if not template or not template.is_active:
                    continue
                
                if category and template.category != category:
                    continue
                
                if specialty and template.specialty.lower() != specialty.lower():
                    continue
                
                results.append(template)
            
            # Sort by usage count and relevance
            results.sort(key=lambda t: (-t.usage_count, t.name))
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search templates: {e}")
            return []
    
    def get_all_templates(self, category: Optional[TemplateCategory] = None,
                         specialty: Optional[str] = None, limit: int = 100) -> List[TemplateConfiguration]:
        """Get all templates with optional filtering"""
        try:
            results = []
            
            for template in self.templates.values():
                if not template.is_active:
                    continue
                
                if category and template.category != category:
                    continue
                
                if specialty and template.specialty.lower() != specialty.lower():
                    continue
                
                results.append(template)
            
            # Sort by usage count and name
            results.sort(key=lambda t: (-t.usage_count, t.name))
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get templates: {e}")
            return []
    
    def get_templates_by_category(self, category: TemplateCategory) -> List[TemplateConfiguration]:
        """Get templates by category"""
        try:
            template_ids = self.category_index.get(category, [])
            return [self.templates[tid] for tid in template_ids if tid in self.templates]
            
        except Exception as e:
            logger.error(f"Failed to get templates by category: {e}")
            return []
    
    def clone_template(self, template_id: str, new_name: str, 
                      created_by: Optional[str] = None) -> Optional[TemplateConfiguration]:
        """Clone an existing template"""
        try:
            source_template = self.templates.get(template_id)
            if not source_template:
                logger.error(f"Source template not found: {template_id}")
                return None
            
            # Create new template with copied data
            cloned_template = TemplateConfiguration(
                template_id=str(uuid.uuid4()),
                name=new_name,
                category=source_template.category,
                template_type=source_template.template_type,
                description=f"Cloned from {source_template.name}",
                specialty=source_template.specialty,
                procedure_type=source_template.procedure_type,
                sections=source_template.sections.copy(),  # Deep copy sections
                voice_commands=[],  # Don't copy voice commands
                tags=source_template.tags.copy(),
                is_active=True,
                is_shared=False,
                created_by=created_by,
                created_at=datetime.utcnow(),
                modified_at=datetime.utcnow(),
                version=1,
                usage_count=0
            )
            
            self.templates[cloned_template.template_id] = cloned_template
            self._build_search_index()
            
            # Notify callbacks
            self._notify_template_change('cloned', cloned_template)
            
            logger.info(f"Cloned template {source_template.name} to {new_name}")
            return cloned_template
            
        except Exception as e:
            logger.error(f"Failed to clone template: {e}")
            return None
    
    def add_section(self, template_id: str, section: TemplateSection) -> bool:
        """Add a section to a template"""
        try:
            template = self.templates.get(template_id)
            if not template:
                return False
            
            template.sections.append(section)
            template.sections.sort(key=lambda s: s.order_index)
            template.modified_at = datetime.utcnow()
            template.version += 1
            
            self._build_search_index()
            self._notify_template_change('section_added', template)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add section: {e}")
            return False
    
    def add_field(self, template_id: str, section_id: str, field: TemplateField) -> bool:
        """Add a field to a template section"""
        try:
            template = self.templates.get(template_id)
            if not template:
                return False
            
            # Find the section
            section = None
            for s in template.sections:
                if s.section_id == section_id:
                    section = s
                    break
            
            if not section:
                return False
            
            section.fields.append(field)
            section.fields.sort(key=lambda f: f.order_index)
            template.modified_at = datetime.utcnow()
            template.version += 1
            
            self._build_search_index()
            self._notify_template_change('field_added', template)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add field: {e}")
            return False
    
    def register_voice_command(self, voice_command: VoiceCommand) -> bool:
        """Register a voice command"""
        try:
            self.voice_commands[voice_command.command_id] = voice_command
            
            # Add to template if specified
            if voice_command.target_id in self.templates:
                template = self.templates[voice_command.target_id]
                template.voice_commands.append(voice_command)
                template.modified_at = datetime.utcnow()
            
            self._build_search_index()
            
            # Notify callbacks
            self._notify_voice_command_change('registered', voice_command)
            
            logger.debug(f"Registered voice command: {voice_command.command_text}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register voice command: {e}")
            return False
    
    def get_voice_commands(self, template_id: Optional[str] = None) -> List[VoiceCommand]:
        """Get voice commands, optionally filtered by template"""
        try:
            if template_id:
                template = self.templates.get(template_id)
                return template.voice_commands if template else []
            else:
                return list(self.voice_commands.values())
                
        except Exception as e:
            logger.error(f"Failed to get voice commands: {e}")
            return []
    
    def process_voice_command(self, command_text: str, confidence: float = 0.8) -> Optional[Dict[str, Any]]:
        """Process a voice command and return action"""
        try:
            command_text = command_text.lower().strip()
            
            # Find matching voice commands from all templates
            all_voice_commands = []
            for template in self.templates.values():
                all_voice_commands.extend(template.voice_commands)
            
            # Also check global voice commands
            all_voice_commands.extend(self.voice_commands.values())
            
            for voice_cmd in all_voice_commands:
                if confidence < voice_cmd.confidence_threshold:
                    continue
                
                # Check exact match
                if command_text == voice_cmd.command_text.lower():
                    return self._execute_voice_command(voice_cmd)
                
                # Check variations
                for variation in voice_cmd.command_variations:
                    if command_text == variation.lower():
                        return self._execute_voice_command(voice_cmd)
                
                # Check partial matches for template names
                if voice_cmd.action_type == "load_template":
                    template = self.templates.get(voice_cmd.target_id)
                    if template and template.name.lower() in command_text:
                        return self._execute_voice_command(voice_cmd)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to process voice command: {e}")
            return None
    
    def _execute_voice_command(self, voice_cmd: VoiceCommand) -> Dict[str, Any]:
        """Execute a voice command and return result"""
        try:
            if voice_cmd.action_type == "load_template":
                template = self.templates.get(voice_cmd.target_id)
                if template:
                    template.usage_count += 1
                    return {
                        'action': 'load_template',
                        'template_id': template.template_id,
                        'template': template
                    }
            
            elif voice_cmd.action_type == "fill_template":
                return {
                    'action': 'fill_template',
                    'template_id': voice_cmd.target_id,
                    'field_values': voice_cmd.parameters
                }
            
            elif voice_cmd.action_type == "fill_field":
                return {
                    'action': 'fill_field',
                    'field_id': voice_cmd.target_id,
                    'value': voice_cmd.parameters.get('value', '')
                }
            
            elif voice_cmd.action_type == "navigate_section":
                return {
                    'action': 'navigate_section',
                    'section_id': voice_cmd.target_id
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to execute voice command: {e}")
            return None
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """Get template usage statistics"""
        try:
            stats = {
                'total_templates': len(self.templates),
                'active_templates': sum(1 for t in self.templates.values() if t.is_active),
                'shared_templates': sum(1 for t in self.templates.values() if t.is_shared),
                'categories': {},
                'most_used': [],
                'recent_templates': []
            }
            
            # Category breakdown
            for category in TemplateCategory:
                count = len(self.category_index.get(category, []))
                if count > 0:
                    stats['categories'][category.value] = count
            
            # Most used templates
            most_used = sorted(
                self.templates.values(),
                key=lambda t: t.usage_count,
                reverse=True
            )[:10]
            
            stats['most_used'] = [
                {'template_id': t.template_id, 'name': t.name, 'usage_count': t.usage_count}
                for t in most_used
            ]
            
            # Recent templates
            recent = sorted(
                self.templates.values(),
                key=lambda t: t.created_at,
                reverse=True
            )[:10]
            
            stats['recent_templates'] = [
                {'template_id': t.template_id, 'name': t.name, 'created_at': t.created_at.isoformat()}
                for t in recent
            ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get template statistics: {e}")
            return {'error': str(e)}
    
    def export_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Export a template to dictionary format"""
        try:
            template = self.templates.get(template_id)
            if not template:
                return None
            
            # Convert to dict and handle enums
            template_dict = asdict(template)
            template_dict['category'] = template.category.value
            template_dict['template_type'] = template.template_type.value
            
            # Convert field types in sections
            for section in template_dict['sections']:
                for field in section['fields']:
                    field['field_type'] = field['field_type'].value if hasattr(field['field_type'], 'value') else field['field_type']
            
            return template_dict
            
        except Exception as e:
            logger.error(f"Failed to export template: {e}")
            return None
    
    def import_template(self, template_data: Dict[str, Any], 
                       created_by: Optional[str] = None) -> Optional[TemplateConfiguration]:
        """Import a template from dictionary format"""
        try:
            # Convert string enums back to enum objects
            if isinstance(template_data.get('category'), str):
                template_data['category'] = TemplateCategory(template_data['category'])
            if isinstance(template_data.get('template_type'), str):
                template_data['template_type'] = TemplateType(template_data['template_type'])
            
            # Convert field types in sections
            for section in template_data.get('sections', []):
                for field in section.get('fields', []):
                    if isinstance(field.get('field_type'), str):
                        field['field_type'] = FieldType(field['field_type'])
            
            # Create template from data
            template = TemplateConfiguration(**template_data)
            
            # Update metadata
            template.template_id = str(uuid.uuid4())  # New ID
            template.created_by = created_by
            template.created_at = datetime.utcnow()
            template.modified_at = datetime.utcnow()
            template.version = 1
            template.usage_count = 0
            
            self.templates[template.template_id] = template
            self._build_search_index()
            
            # Notify callbacks
            self._notify_template_change('imported', template)
            
            logger.info(f"Imported template: {template.name}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to import template: {e}")
            return None
    
    def add_template_change_callback(self, callback: Callable):
        """Add callback for template changes"""
        self.template_change_callbacks.append(callback)
    
    def add_voice_command_callback(self, callback: Callable):
        """Add callback for voice command changes"""
        self.voice_command_callbacks.append(callback)
    
    def _notify_template_change(self, change_type: str, template: TemplateConfiguration):
        """Notify template change callbacks"""
        try:
            for callback in self.template_change_callbacks:
                try:
                    callback(change_type, template)
                except Exception as e:
                    logger.error(f"Error in template change callback: {e}")
        except Exception as e:
            logger.error(f"Failed to notify template change: {e}")
    
    def _notify_voice_command_change(self, change_type: str, voice_command: VoiceCommand):
        """Notify voice command change callbacks"""
        try:
            for callback in self.voice_command_callbacks:
                try:
                    callback(change_type, voice_command)
                except Exception as e:
                    logger.error(f"Error in voice command callback: {e}")
        except Exception as e:
            logger.error(f"Failed to notify voice command change: {e}")

# Global template manager instance
template_manager = TemplateManager()