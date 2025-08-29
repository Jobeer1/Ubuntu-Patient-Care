"""
Template Repository for Medical Reporting Module
Handles database persistence of report templates
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from models.database import get_db_session
from models.template import ReportTemplate
from services.template_manager import (
    TemplateConfiguration, TemplateCategory, TemplateType, 
    TemplateSection, TemplateField, VoiceCommand, FieldType
)

logger = logging.getLogger(__name__)

class TemplateRepository:
    """Repository for template database operations"""
    
    def __init__(self):
        self.cache: Dict[str, TemplateConfiguration] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_timeout_minutes = 30
    
    def save_template(self, template_config: TemplateConfiguration) -> bool:
        """Save a template configuration to the database"""
        try:
            with get_db_session() as session:
                # Check if template already exists
                existing_template = session.query(ReportTemplate).filter(
                    ReportTemplate.template_id == template_config.template_id
                ).first()
                
                if existing_template:
                    # Update existing template
                    existing_template.name = template_config.name
                    existing_template.category = template_config.category.value
                    existing_template.template_type = template_config.template_type.value
                    existing_template.description = template_config.description
                    existing_template.specialty = template_config.specialty
                    existing_template.procedure_type = template_config.procedure_type
                    existing_template.template_data = self._serialize_template_config(template_config)
                    existing_template.tags = json.dumps(template_config.tags)
                    existing_template.is_active = template_config.is_active
                    existing_template.is_shared = template_config.is_shared
                    existing_template.created_by = template_config.created_by
                    existing_template.modified_at = datetime.utcnow()
                    existing_template.version = template_config.version
                    existing_template.usage_count = template_config.usage_count
                    
                    logger.info(f"Updated existing template: {template_config.name}")
                else:
                    # Create new template
                    new_template = ReportTemplate(
                        template_id=template_config.template_id,
                        name=template_config.name,
                        category=template_config.category.value,
                        template_type=template_config.template_type.value,
                        description=template_config.description,
                        specialty=template_config.specialty,
                        procedure_type=template_config.procedure_type,
                        template_data=self._serialize_template_config(template_config),
                        tags=json.dumps(template_config.tags),
                        is_active=template_config.is_active,
                        is_shared=template_config.is_shared,
                        created_by=template_config.created_by,
                        created_at=template_config.created_at,
                        modified_at=template_config.modified_at,
                        version=template_config.version,
                        usage_count=template_config.usage_count
                    )
                    
                    session.add(new_template)
                    logger.info(f"Created new template: {template_config.name}")
                
                session.commit()
                
                # Update cache
                self.cache[template_config.template_id] = template_config
                self.cache_expiry[template_config.template_id] = datetime.utcnow()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to save template: {e}")
            return False
    
    def load_template(self, template_id: str) -> Optional[TemplateConfiguration]:
        """Load a template configuration from the database"""
        try:
            # Check cache first
            if self._is_cached(template_id):
                return self.cache[template_id]
            
            with get_db_session() as session:
                template_record = session.query(ReportTemplate).filter(
                    ReportTemplate.template_id == template_id
                ).first()
                
                if not template_record:
                    logger.warning(f"Template not found: {template_id}")
                    return None
                
                # Deserialize configuration
                template_config = self._deserialize_template_config(template_record)
                
                # Update cache
                self.cache[template_id] = template_config
                self.cache_expiry[template_id] = datetime.utcnow()
                
                logger.info(f"Loaded template: {template_config.name}")
                return template_config
                
        except Exception as e:
            logger.error(f"Failed to load template: {e}")
            return None
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template from the database"""
        try:
            with get_db_session() as session:
                template_record = session.query(ReportTemplate).filter(
                    ReportTemplate.template_id == template_id
                ).first()
                
                if not template_record:
                    logger.warning(f"Template not found for deletion: {template_id}")
                    return False
                
                session.delete(template_record)
                session.commit()
                
                # Remove from cache
                if template_id in self.cache:
                    del self.cache[template_id]
                if template_id in self.cache_expiry:
                    del self.cache_expiry[template_id]
                
                logger.info(f"Deleted template: {template_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete template: {e}")
            return False
    
    def get_user_templates(self, user_id: str, include_shared: bool = True) -> List[TemplateConfiguration]:
        """Get all templates for a specific user"""
        try:
            with get_db_session() as session:
                query = session.query(ReportTemplate)
                
                if include_shared:
                    query = query.filter(
                        or_(
                            ReportTemplate.created_by == user_id,
                            ReportTemplate.is_shared == True
                        )
                    )
                else:
                    query = query.filter(ReportTemplate.created_by == user_id)
                
                query = query.filter(ReportTemplate.is_active == True)
                query = query.order_by(desc(ReportTemplate.usage_count), ReportTemplate.name)
                
                template_records = query.all()
                
                templates = []
                for record in template_records:
                    try:
                        template_config = self._deserialize_template_config(record)
                        templates.append(template_config)
                        
                        # Update cache
                        self.cache[template_config.template_id] = template_config
                        self.cache_expiry[template_config.template_id] = datetime.utcnow()
                        
                    except Exception as e:
                        logger.error(f"Failed to deserialize template {record.template_id}: {e}")
                        continue
                
                logger.info(f"Retrieved {len(templates)} templates for user {user_id}")
                return templates
                
        except Exception as e:
            logger.error(f"Failed to get user templates: {e}")
            return []
    
    def search_templates(self, query: str, category: Optional[str] = None,
                        specialty: Optional[str] = None, user_id: Optional[str] = None,
                        limit: int = 50) -> List[TemplateConfiguration]:
        """Search templates in the database"""
        try:
            with get_db_session() as session:
                db_query = session.query(ReportTemplate).filter(
                    ReportTemplate.is_active == True
                )
                
                # Text search
                if query.strip():
                    search_term = f"%{query.lower()}%"
                    db_query = db_query.filter(
                        or_(
                            ReportTemplate.name.ilike(search_term),
                            ReportTemplate.description.ilike(search_term),
                            ReportTemplate.specialty.ilike(search_term),
                            ReportTemplate.procedure_type.ilike(search_term),
                            ReportTemplate.tags.ilike(search_term)
                        )
                    )
                
                # Category filter
                if category:
                    db_query = db_query.filter(ReportTemplate.category == category)
                
                # Specialty filter
                if specialty:
                    db_query = db_query.filter(ReportTemplate.specialty.ilike(f"%{specialty}%"))
                
                # User filter (user's templates + shared templates)
                if user_id:
                    db_query = db_query.filter(
                        or_(
                            ReportTemplate.created_by == user_id,
                            ReportTemplate.is_shared == True
                        )
                    )
                
                # Order by usage and name
                db_query = db_query.order_by(
                    desc(ReportTemplate.usage_count),
                    ReportTemplate.name
                ).limit(limit)
                
                template_records = db_query.all()
                
                templates = []
                for record in template_records:
                    try:
                        template_config = self._deserialize_template_config(record)
                        templates.append(template_config)
                    except Exception as e:
                        logger.error(f"Failed to deserialize template {record.template_id}: {e}")
                        continue
                
                logger.info(f"Found {len(templates)} templates for query: {query}")
                return templates
                
        except Exception as e:
            logger.error(f"Failed to search templates: {e}")
            return []
    
    def get_templates_by_category(self, category: str, user_id: Optional[str] = None) -> List[TemplateConfiguration]:
        """Get templates filtered by category"""
        try:
            with get_db_session() as session:
                query = session.query(ReportTemplate).filter(
                    and_(
                        ReportTemplate.category == category,
                        ReportTemplate.is_active == True
                    )
                )
                
                if user_id:
                    query = query.filter(
                        or_(
                            ReportTemplate.created_by == user_id,
                            ReportTemplate.is_shared == True
                        )
                    )
                
                query = query.order_by(desc(ReportTemplate.usage_count), ReportTemplate.name)
                template_records = query.all()
                
                templates = []
                for record in template_records:
                    try:
                        template_config = self._deserialize_template_config(record)
                        templates.append(template_config)
                    except Exception as e:
                        logger.error(f"Failed to deserialize template {record.template_id}: {e}")
                        continue
                
                logger.info(f"Retrieved {len(templates)} templates for category {category}")
                return templates
                
        except Exception as e:
            logger.error(f"Failed to get templates by category: {e}")
            return []
    
    def get_popular_templates(self, limit: int = 10, user_id: Optional[str] = None) -> List[TemplateConfiguration]:
        """Get most popular templates"""
        try:
            with get_db_session() as session:
                query = session.query(ReportTemplate).filter(
                    ReportTemplate.is_active == True
                )
                
                if user_id:
                    query = query.filter(
                        or_(
                            ReportTemplate.created_by == user_id,
                            ReportTemplate.is_shared == True
                        )
                    )
                
                query = query.order_by(desc(ReportTemplate.usage_count)).limit(limit)
                template_records = query.all()
                
                templates = []
                for record in template_records:
                    try:
                        template_config = self._deserialize_template_config(record)
                        templates.append(template_config)
                    except Exception as e:
                        logger.error(f"Failed to deserialize template {record.template_id}: {e}")
                        continue
                
                return templates
                
        except Exception as e:
            logger.error(f"Failed to get popular templates: {e}")
            return []
    
    def get_recent_templates(self, limit: int = 10, user_id: Optional[str] = None) -> List[TemplateConfiguration]:
        """Get recently created templates"""
        try:
            with get_db_session() as session:
                query = session.query(ReportTemplate).filter(
                    ReportTemplate.is_active == True
                )
                
                if user_id:
                    query = query.filter(
                        or_(
                            ReportTemplate.created_by == user_id,
                            ReportTemplate.is_shared == True
                        )
                    )
                
                query = query.order_by(desc(ReportTemplate.created_at)).limit(limit)
                template_records = query.all()
                
                templates = []
                for record in template_records:
                    try:
                        template_config = self._deserialize_template_config(record)
                        templates.append(template_config)
                    except Exception as e:
                        logger.error(f"Failed to deserialize template {record.template_id}: {e}")
                        continue
                
                return templates
                
        except Exception as e:
            logger.error(f"Failed to get recent templates: {e}")
            return []
    
    def update_usage_count(self, template_id: str) -> bool:
        """Increment template usage count"""
        try:
            with get_db_session() as session:
                template_record = session.query(ReportTemplate).filter(
                    ReportTemplate.template_id == template_id
                ).first()
                
                if template_record:
                    template_record.usage_count += 1
                    session.commit()
                    
                    # Update cache if present
                    if template_id in self.cache:
                        self.cache[template_id].usage_count += 1
                    
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to update usage count: {e}")
            return False
    
    def get_template_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get template statistics from database"""
        try:
            with get_db_session() as session:
                query = session.query(ReportTemplate)
                
                if user_id:
                    query = query.filter(
                        or_(
                            ReportTemplate.created_by == user_id,
                            ReportTemplate.is_shared == True
                        )
                    )
                
                all_templates = query.all()
                active_templates = [t for t in all_templates if t.is_active]
                
                # Category breakdown
                categories = {}
                for template in active_templates:
                    category = template.category
                    categories[category] = categories.get(category, 0) + 1
                
                # Most used templates
                most_used = sorted(active_templates, key=lambda t: t.usage_count, reverse=True)[:10]
                
                # Recent templates
                recent = sorted(active_templates, key=lambda t: t.created_at, reverse=True)[:10]
                
                stats = {
                    'total_templates': len(all_templates),
                    'active_templates': len(active_templates),
                    'shared_templates': sum(1 for t in active_templates if t.is_shared),
                    'categories': categories,
                    'most_used': [
                        {
                            'template_id': t.template_id,
                            'name': t.name,
                            'usage_count': t.usage_count
                        }
                        for t in most_used
                    ],
                    'recent_templates': [
                        {
                            'template_id': t.template_id,
                            'name': t.name,
                            'created_at': t.created_at.isoformat()
                        }
                        for t in recent
                    ]
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get template statistics: {e}")
            return {'error': str(e)}
    
    def _serialize_template_config(self, template_config: TemplateConfiguration) -> Dict[str, Any]:
        """Serialize a template configuration to a dictionary"""
        try:
            return {
                'template_id': template_config.template_id,
                'name': template_config.name,
                'category': template_config.category.value,
                'template_type': template_config.template_type.value,
                'description': template_config.description,
                'specialty': template_config.specialty,
                'procedure_type': template_config.procedure_type,
                'sections': [
                    {
                        'section_id': section.section_id,
                        'section_name': section.section_name,
                        'title': section.title,
                        'description': section.description,
                        'order_index': section.order_index,
                        'is_collapsible': section.is_collapsible,
                        'is_expanded': section.is_expanded,
                        'voice_commands': section.voice_commands,
                        'fields': [
                            {
                                'field_id': field.field_id,
                                'field_name': field.field_name,
                                'field_type': field.field_type.value,
                                'label': field.label,
                                'description': field.description,
                                'required': field.required,
                                'default_value': field.default_value,
                                'options': field.options,
                                'validation_rules': field.validation_rules,
                                'voice_commands': field.voice_commands,
                                'order_index': field.order_index,
                                'section': field.section,
                                'properties': field.properties
                            }
                            for field in section.fields
                        ]
                    }
                    for section in template_config.sections
                ],
                'voice_commands': [
                    {
                        'command_id': cmd.command_id,
                        'command_text': cmd.command_text,
                        'command_variations': cmd.command_variations,
                        'action_type': cmd.action_type,
                        'target_id': cmd.target_id,
                        'parameters': cmd.parameters,
                        'confidence_threshold': cmd.confidence_threshold
                    }
                    for cmd in template_config.voice_commands
                ],
                'tags': template_config.tags,
                'is_active': template_config.is_active,
                'is_shared': template_config.is_shared,
                'created_by': template_config.created_by,
                'created_at': template_config.created_at.isoformat(),
                'modified_at': template_config.modified_at.isoformat(),
                'version': template_config.version,
                'usage_count': template_config.usage_count
            }
            
        except Exception as e:
            logger.error(f"Failed to serialize template config: {e}")
            raise
    
    def _deserialize_template_config(self, template_record: ReportTemplate) -> TemplateConfiguration:
        """Deserialize a template configuration from a database record"""
        try:
            template_data = template_record.template_data
            
            # Parse sections
            sections = []
            for section_data in template_data.get('sections', []):
                # Parse fields
                fields = []
                for field_data in section_data.get('fields', []):
                    field = TemplateField(
                        field_id=field_data['field_id'],
                        field_name=field_data['field_name'],
                        field_type=FieldType(field_data['field_type']),
                        label=field_data['label'],
                        description=field_data.get('description', ''),
                        required=field_data.get('required', False),
                        default_value=field_data.get('default_value'),
                        options=field_data.get('options', []),
                        validation_rules=field_data.get('validation_rules', {}),
                        voice_commands=field_data.get('voice_commands', []),
                        order_index=field_data.get('order_index', 0),
                        section=field_data.get('section', 'main'),
                        properties=field_data.get('properties', {})
                    )
                    fields.append(field)
                
                section = TemplateSection(
                    section_id=section_data['section_id'],
                    section_name=section_data['section_name'],
                    title=section_data['title'],
                    description=section_data.get('description', ''),
                    fields=fields,
                    order_index=section_data.get('order_index', 0),
                    is_collapsible=section_data.get('is_collapsible', True),
                    is_expanded=section_data.get('is_expanded', True),
                    voice_commands=section_data.get('voice_commands', [])
                )
                sections.append(section)
            
            # Parse voice commands
            voice_commands = []
            for cmd_data in template_data.get('voice_commands', []):
                voice_cmd = VoiceCommand(
                    command_id=cmd_data['command_id'],
                    command_text=cmd_data['command_text'],
                    command_variations=cmd_data.get('command_variations', []),
                    action_type=cmd_data.get('action_type', 'load_template'),
                    target_id=cmd_data.get('target_id', ''),
                    parameters=cmd_data.get('parameters', {}),
                    confidence_threshold=cmd_data.get('confidence_threshold', 0.8)
                )
                voice_commands.append(voice_cmd)
            
            # Parse tags
            tags = json.loads(template_record.tags) if template_record.tags else []
            
            # Create template configuration
            template_config = TemplateConfiguration(
                template_id=template_record.template_id,
                name=template_record.name,
                category=TemplateCategory(template_record.category),
                template_type=TemplateType(template_record.template_type),
                description=template_record.description,
                specialty=template_record.specialty,
                procedure_type=template_record.procedure_type,
                sections=sections,
                voice_commands=voice_commands,
                tags=tags,
                is_active=template_record.is_active,
                is_shared=template_record.is_shared,
                created_by=template_record.created_by,
                created_at=template_record.created_at,
                modified_at=template_record.modified_at,
                version=template_record.version,
                usage_count=template_record.usage_count
            )
            
            return template_config
            
        except Exception as e:
            logger.error(f"Failed to deserialize template config: {e}")
            raise
    
    def _is_cached(self, template_id: str) -> bool:
        """Check if a template is cached and not expired"""
        if template_id not in self.cache:
            return False
        
        if template_id not in self.cache_expiry:
            return False
        
        # Check if cache has expired
        cache_time = self.cache_expiry[template_id]
        now = datetime.utcnow()
        elapsed_minutes = (now - cache_time).total_seconds() / 60
        
        if elapsed_minutes > self.cache_timeout_minutes:
            # Remove expired cache entry
            del self.cache[template_id]
            del self.cache_expiry[template_id]
            return False
        
        return True
    
    def clear_cache(self):
        """Clear the template cache"""
        self.cache.clear()
        self.cache_expiry.clear()
        logger.info("Cleared template cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_templates': len(self.cache),
            'cache_timeout_minutes': self.cache_timeout_minutes,
            'cache_entries': list(self.cache.keys())
        }

# Global template repository instance
template_repository = TemplateRepository()