#!/usr/bin/env python3
"""
🇿🇦 SA Medical Templates Engine

Provides South African medical report templates, terminology, and compliance features.
Designed specifically for SA healthcare workflows and regulatory requirements.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)

@dataclass
class SAMedicalTemplate:
    """South African medical report template"""
    template_id: str
    name_en: str
    name_af: str = ""
    name_zu: str = ""
    modality: str = ""
    body_part: str = ""
    category: str = "diagnostic"  # screening, diagnostic, follow_up, emergency
    structure: Dict[str, Any] = None
    compliance_level: str = "basic"  # basic, hpcsa, medical_aid
    created_by: str = ""
    institution_id: str = ""
    is_public: bool = True
    sa_specific: bool = True
    version: str = "1.0"
    common_conditions: List[str] = None
    medical_aid_fields: List[str] = None
    hpcsa_requirements: Dict[str, Any] = None
    language_variants: Dict[str, Dict] = None
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if self.structure is None:
            self.structure = {}
        if self.common_conditions is None:
            self.common_conditions = []
        if self.medical_aid_fields is None:
            self.medical_aid_fields = []
        if self.hpcsa_requirements is None:
            self.hpcsa_requirements = {}
        if self.language_variants is None:
            self.language_variants = {}
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SAMedicalTemplate':
        return cls(**data)

@dataclass
class SAMedicalTerm:
    """South African medical terminology"""
    term_id: str
    english_term: str
    afrikaans_term: str = ""
    isizulu_term: str = ""
    category: str = "general"  # anatomy, condition, procedure, drug, general
    modality: str = ""
    body_part: str = ""
    frequency: int = 0
    confidence: float = 1.0
    synonyms: List[str] = None
    abbreviations: List[str] = None
    context: str = ""
    
    def __post_init__(self):
        if self.synonyms is None:
            self.synonyms = []
        if self.abbreviations is None:
            self.abbreviations = []
    
    def to_dict(self) -> Dict:
        return asdict(self)

class SAMedicalTemplateEngine:
    """
    South African Medical Template Engine
    Manages templates, terminology, and compliance for SA healthcare
    """
    
    def __init__(self, db_path: str = "reporting.db"):
        self.db_path = db_path
        self.init_template_database()
        self.load_sa_medical_data()
    
    def init_template_database(self):
        """Initialize template database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # SA Medical Templates table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sa_medical_templates (
                    template_id TEXT PRIMARY KEY,
                    name_en TEXT NOT NULL,
                    name_af TEXT,
                    name_zu TEXT,
                    modality TEXT NOT NULL,
                    body_part TEXT NOT NULL,
                    category TEXT NOT NULL,
                    structure TEXT NOT NULL,
                    compliance_level TEXT DEFAULT 'basic',
                    created_by TEXT NOT NULL,
                    institution_id TEXT,
                    is_public BOOLEAN DEFAULT TRUE,
                    sa_specific BOOLEAN DEFAULT TRUE,
                    version TEXT DEFAULT '1.0',
                    common_conditions TEXT,
                    medical_aid_fields TEXT,
                    hpcsa_requirements TEXT,
                    language_variants TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            
            # SA Medical Terms table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sa_medical_terms (
                    term_id TEXT PRIMARY KEY,
                    english_term TEXT NOT NULL,
                    afrikaans_term TEXT,
                    isizulu_term TEXT,
                    category TEXT NOT NULL,
                    modality TEXT,
                    body_part TEXT,
                    frequency INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 1.0,
                    synonyms TEXT,
                    abbreviations TEXT,
                    context TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            
            # Template usage analytics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS template_usage (
                    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    language TEXT NOT NULL,
                    completion_time INTEGER,
                    fields_completed INTEGER,
                    total_fields INTEGER,
                    quality_score REAL,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (template_id) REFERENCES sa_medical_templates(template_id)
                )
            ''')
            
            # SA Medical Aids
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sa_medical_aids (
                    scheme_id TEXT PRIMARY KEY,
                    scheme_name TEXT NOT NULL,
                    logo_url TEXT,
                    billing_codes TEXT,
                    authorization_fields TEXT,
                    report_requirements TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_template_modality ON sa_medical_templates(modality, body_part)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_template_category ON sa_medical_templates(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_terms_category ON sa_medical_terms(category, modality)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_template ON template_usage(template_id)')
            
            conn.commit()
            conn.close()
            logger.info("✅ SA Medical Templates database initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing template database: {e}")
            raise
    
    def load_sa_medical_data(self):
        """Load initial SA medical templates and terminology"""
        try:
            # Load default templates
            self._create_default_templates()
            
            # Load SA medical terminology
            self._load_sa_terminology()
            
            # Load medical aid schemes
            self._load_medical_aid_schemes()
            
            logger.info("✅ SA medical data loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Error loading SA medical data: {e}")
    
    def _create_default_templates(self):
        """Create default SA medical templates"""
        templates = [
            # TB Screening Template
            {
                'template_id': 'sa_tb_screening_chest',
                'name_en': 'TB Screening - Chest X-Ray',
                'name_af': 'TB Sifting - Bors X-straal',
                'name_zu': 'Ukuhlola i-TB - X-ray yesifuba',
                'modality': 'CR',
                'body_part': 'CHEST',
                'category': 'screening',
                'structure': {
                    'sections': [
                        {
                            'id': 'clinical_indication',
                            'title': {'en': 'Clinical Indication', 'af': 'Kliniese Aanduiding', 'zu': 'Isikhombiso Sokwelapha'},
                            'type': 'text',
                            'required': True,
                            'voice_prompts': {
                                'en': 'State the clinical indication for TB screening',
                                'af': 'Stel die kliniese aanduiding vir TB-sifting',
                                'zu': 'Chaza isizathu sokuhlola i-TB'
                            }
                        },
                        {
                            'id': 'findings',
                            'title': {'en': 'Findings', 'af': 'Bevindinge', 'zu': 'Okutholiwe'},
                            'type': 'structured',
                            'required': True,
                            'fields': [
                                {
                                    'id': 'lung_fields',
                                    'label': {'en': 'Lung Fields', 'af': 'Longvelde', 'zu': 'Izindawo Zamaphaphu'},
                                    'type': 'select',
                                    'options': ['Clear', 'Consolidation', 'Cavitation', 'Fibrosis', 'Pleural effusion']
                                },
                                {
                                    'id': 'heart_size',
                                    'label': {'en': 'Heart Size', 'af': 'Hartgrootte', 'zu': 'Usayizi Wenhliziyo'},
                                    'type': 'select',
                                    'options': ['Normal', 'Enlarged', 'Cannot assess']
                                }
                            ]
                        },
                        {
                            'id': 'impression',
                            'title': {'en': 'Impression', 'af': 'Indruk', 'zu': 'Umbono'},
                            'type': 'text',
                            'required': True,
                            'suggestions': [
                                'No evidence of active pulmonary tuberculosis',
                                'Findings consistent with pulmonary tuberculosis',
                                'Post-tuberculous changes',
                                'Recommend clinical correlation'
                            ]
                        }
                    ]
                },
                'common_conditions': ['tuberculosis', 'pneumonia', 'pleural_effusion'],
                'compliance_level': 'hpcsa',
                'sa_specific': True
            },
            
            # Trauma Assessment Template
            {
                'template_id': 'sa_trauma_chest',
                'name_en': 'Trauma Assessment - Chest',
                'name_af': 'Trauma Assessering - Bors',
                'name_zu': 'Ukuhlola Ukulimala - Isifuba',
                'modality': 'CR',
                'body_part': 'CHEST',
                'category': 'emergency',
                'structure': {
                    'sections': [
                        {
                            'id': 'mechanism_of_injury',
                            'title': {'en': 'Mechanism of Injury', 'af': 'Meganisme van Besering', 'zu': 'Indlela Yokulimala'},
                            'type': 'text',
                            'required': True
                        },
                        {
                            'id': 'emergency_findings',
                            'title': {'en': 'Emergency Findings', 'af': 'Nood Bevindinge', 'zu': 'Okutholakele Ngokushesha'},
                            'type': 'structured',
                            'required': True,
                            'fields': [
                                {
                                    'id': 'pneumothorax',
                                    'label': {'en': 'Pneumothorax', 'af': 'Pneumotoraks', 'zu': 'Umoya Ephaphwini'},
                                    'type': 'select',
                                    'options': ['None', 'Small', 'Moderate', 'Large', 'Tension']
                                },
                                {
                                    'id': 'rib_fractures',
                                    'label': {'en': 'Rib Fractures', 'af': 'Ribbreuke', 'zu': 'Ukwephuka Kwamathambo Omqolo'},
                                    'type': 'text'
                                }
                            ]
                        }
                    ]
                },
                'common_conditions': ['pneumothorax', 'rib_fractures', 'hemothorax'],
                'compliance_level': 'hpcsa'
            }
        ]
        
        for template_data in templates:
            self.create_template(template_data, 'system')
    
    def _load_sa_terminology(self):
        """Load SA medical terminology"""
        terms = [
            # Anatomical terms
            {
                'term_id': 'chest_en_af_zu',
                'english_term': 'chest',
                'afrikaans_term': 'bors',
                'isizulu_term': 'isifuba',
                'category': 'anatomy',
                'modality': 'CR',
                'body_part': 'CHEST'
            },
            {
                'term_id': 'lungs_en_af_zu',
                'english_term': 'lungs',
                'afrikaans_term': 'longe',
                'isizulu_term': 'amaphaphu',
                'category': 'anatomy',
                'modality': 'CR',
                'body_part': 'CHEST'
            },
            {
                'term_id': 'heart_en_af_zu',
                'english_term': 'heart',
                'afrikaans_term': 'hart',
                'isizulu_term': 'inhliziyo',
                'category': 'anatomy',
                'modality': 'CR',
                'body_part': 'CHEST'
            },
            
            # Medical conditions
            {
                'term_id': 'tuberculosis_en_af_zu',
                'english_term': 'tuberculosis',
                'afrikaans_term': 'tuberkulose',
                'isizulu_term': 'isifo sefuba',
                'category': 'condition',
                'abbreviations': ['TB'],
                'synonyms': ['TB', 'pulmonary tuberculosis']
            },
            {
                'term_id': 'pneumonia_en_af_zu',
                'english_term': 'pneumonia',
                'afrikaans_term': 'longontsteking',
                'isizulu_term': 'inyumoniya',
                'category': 'condition'
            },
            {
                'term_id': 'fracture_en_af_zu',
                'english_term': 'fracture',
                'afrikaans_term': 'breuk',
                'isizulu_term': 'ukwephuka',
                'category': 'condition'
            }
        ]
        
        for term_data in terms:
            self.add_medical_term(term_data)
    
    def _load_medical_aid_schemes(self):
        """Load SA medical aid schemes"""
        schemes = [
            {
                'scheme_id': 'discovery_health',
                'scheme_name': 'Discovery Health',
                'billing_codes': ['ICD-10', 'CPT'],
                'authorization_fields': ['member_number', 'authorization_code'],
                'report_requirements': ['clinical_indication', 'findings', 'impression']
            },
            {
                'scheme_id': 'momentum_health',
                'scheme_name': 'Momentum Health',
                'billing_codes': ['ICD-10', 'CPT'],
                'authorization_fields': ['member_number', 'plan_type'],
                'report_requirements': ['clinical_indication', 'findings', 'impression']
            },
            {
                'scheme_id': 'bonitas',
                'scheme_name': 'Bonitas Medical Fund',
                'billing_codes': ['ICD-10'],
                'authorization_fields': ['member_number'],
                'report_requirements': ['clinical_indication', 'findings', 'impression']
            }
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for scheme in schemes:
            cursor.execute('''
                INSERT OR REPLACE INTO sa_medical_aids 
                (scheme_id, scheme_name, billing_codes, authorization_fields, report_requirements)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                scheme['scheme_id'],
                scheme['scheme_name'],
                json.dumps(scheme['billing_codes']),
                json.dumps(scheme['authorization_fields']),
                json.dumps(scheme['report_requirements'])
            ))
        
        conn.commit()
        conn.close()    

    def get_templates_by_modality(self, modality: str, body_part: str = "", 
                                 language: str = 'en', category: str = "") -> List[SAMedicalTemplate]:
        """Get templates by modality and optional filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM sa_medical_templates WHERE modality = ?'
            params = [modality]
            
            if body_part:
                query += ' AND body_part = ?'
                params.append(body_part)
            
            if category:
                query += ' AND category = ?'
                params.append(category)
            
            query += ' ORDER BY category, name_en'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            templates = []
            columns = [desc[0] for desc in cursor.description]
            
            for row in rows:
                template_data = dict(zip(columns, row))
                
                # Parse JSON fields
                template_data['structure'] = json.loads(template_data['structure'] or '{}')
                template_data['common_conditions'] = json.loads(template_data['common_conditions'] or '[]')
                template_data['medical_aid_fields'] = json.loads(template_data['medical_aid_fields'] or '[]')
                template_data['hpcsa_requirements'] = json.loads(template_data['hpcsa_requirements'] or '{}')
                template_data['language_variants'] = json.loads(template_data['language_variants'] or '{}')
                
                templates.append(SAMedicalTemplate.from_dict(template_data))
            
            conn.close()
            return templates
            
        except Exception as e:
            logger.error(f"❌ Error getting templates by modality: {e}")
            return []
    
    def get_template_by_id(self, template_id: str, language: str = 'en') -> Optional[SAMedicalTemplate]:
        """Get specific template by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM sa_medical_templates WHERE template_id = ?', (template_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                template_data = dict(zip(columns, row))
                
                # Parse JSON fields
                template_data['structure'] = json.loads(template_data['structure'] or '{}')
                template_data['common_conditions'] = json.loads(template_data['common_conditions'] or '[]')
                template_data['medical_aid_fields'] = json.loads(template_data['medical_aid_fields'] or '[]')
                template_data['hpcsa_requirements'] = json.loads(template_data['hpcsa_requirements'] or '{}')
                template_data['language_variants'] = json.loads(template_data['language_variants'] or '{}')
                
                conn.close()
                return SAMedicalTemplate.from_dict(template_data)
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting template by ID: {e}")
            return None
    
    def create_template(self, template_data: Dict, user_id: str) -> Tuple[bool, str]:
        """Create new medical template"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            template_id = template_data.get('template_id') or f"template_{uuid.uuid4().hex[:8]}"
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO sa_medical_templates 
                (template_id, name_en, name_af, name_zu, modality, body_part, category,
                 structure, compliance_level, created_by, institution_id, is_public,
                 sa_specific, version, common_conditions, medical_aid_fields,
                 hpcsa_requirements, language_variants, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                template_id,
                template_data.get('name_en', ''),
                template_data.get('name_af', ''),
                template_data.get('name_zu', ''),
                template_data.get('modality', ''),
                template_data.get('body_part', ''),
                template_data.get('category', 'diagnostic'),
                json.dumps(template_data.get('structure', {})),
                template_data.get('compliance_level', 'basic'),
                user_id,
                template_data.get('institution_id', ''),
                template_data.get('is_public', True),
                template_data.get('sa_specific', True),
                template_data.get('version', '1.0'),
                json.dumps(template_data.get('common_conditions', [])),
                json.dumps(template_data.get('medical_aid_fields', [])),
                json.dumps(template_data.get('hpcsa_requirements', {})),
                json.dumps(template_data.get('language_variants', {})),
                now,
                now
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Created template: {template_id}")
            return True, template_id
            
        except Exception as e:
            logger.error(f"❌ Error creating template: {e}")
            return False, str(e)
    
    def add_medical_term(self, term_data: Dict) -> Tuple[bool, str]:
        """Add medical terminology"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            term_id = term_data.get('term_id') or f"term_{uuid.uuid4().hex[:8]}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO sa_medical_terms 
                (term_id, english_term, afrikaans_term, isizulu_term, category,
                 modality, body_part, frequency, confidence, synonyms, abbreviations, context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                term_id,
                term_data.get('english_term', ''),
                term_data.get('afrikaans_term', ''),
                term_data.get('isizulu_term', ''),
                term_data.get('category', 'general'),
                term_data.get('modality', ''),
                term_data.get('body_part', ''),
                term_data.get('frequency', 0),
                term_data.get('confidence', 1.0),
                json.dumps(term_data.get('synonyms', [])),
                json.dumps(term_data.get('abbreviations', [])),
                term_data.get('context', '')
            ))
            
            conn.commit()
            conn.close()
            
            return True, term_id
            
        except Exception as e:
            logger.error(f"❌ Error adding medical term: {e}")
            return False, str(e)
    
    def get_medical_terms(self, language: str = 'en', category: str = "", 
                         modality: str = "", search: str = "") -> List[SAMedicalTerm]:
        """Get medical terms with optional filtering"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM sa_medical_terms WHERE 1=1'
            params = []
            
            if category:
                query += ' AND category = ?'
                params.append(category)
            
            if modality:
                query += ' AND modality = ?'
                params.append(modality)
            
            if search:
                query += ' AND (english_term LIKE ? OR afrikaans_term LIKE ? OR isizulu_term LIKE ?)'
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])
            
            query += ' ORDER BY frequency DESC, english_term'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            terms = []
            columns = [desc[0] for desc in cursor.description]
            
            for row in rows:
                term_data = dict(zip(columns, row))
                term_data['synonyms'] = json.loads(term_data['synonyms'] or '[]')
                term_data['abbreviations'] = json.loads(term_data['abbreviations'] or '[]')
                terms.append(SAMedicalTerm.from_dict(term_data))
            
            conn.close()
            return terms
            
        except Exception as e:
            logger.error(f"❌ Error getting medical terms: {e}")
            return []
    
    def translate_medical_term(self, term: str, from_lang: str, to_lang: str) -> Optional[str]:
        """Translate medical term between languages"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Map language codes to column names
            lang_columns = {
                'en': 'english_term',
                'af': 'afrikaans_term',
                'zu': 'isizulu_term'
            }
            
            from_col = lang_columns.get(from_lang)
            to_col = lang_columns.get(to_lang)
            
            if not from_col or not to_col:
                return None
            
            cursor.execute(f'SELECT {to_col} FROM sa_medical_terms WHERE {from_col} = ? AND {to_col} != ""', (term,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row and row[0]:
                return row[0]
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error translating medical term: {e}")
            return None
    
    def populate_template(self, template_id: str, data: Dict, language: str = 'en') -> Dict[str, Any]:
        """Populate template with data"""
        try:
            template = self.get_template_by_id(template_id, language)
            if not template:
                return {'error': 'Template not found'}
            
            populated = {
                'template_id': template_id,
                'template_name': getattr(template, f'name_{language}', template.name_en),
                'language': language,
                'populated_sections': [],
                'metadata': {
                    'modality': template.modality,
                    'body_part': template.body_part,
                    'category': template.category,
                    'compliance_level': template.compliance_level
                }
            }
            
            # Populate sections with provided data
            for section in template.structure.get('sections', []):
                populated_section = {
                    'id': section['id'],
                    'title': section['title'].get(language, section['title'].get('en', '')),
                    'type': section['type'],
                    'required': section.get('required', False),
                    'content': data.get(section['id'], ''),
                    'completed': bool(data.get(section['id']))
                }
                
                # Add field-specific data for structured sections
                if section['type'] == 'structured' and 'fields' in section:
                    populated_section['fields'] = []
                    for field in section['fields']:
                        field_data = {
                            'id': field['id'],
                            'label': field['label'].get(language, field['label'].get('en', '')),
                            'type': field['type'],
                            'value': data.get(f"{section['id']}.{field['id']}", ''),
                            'options': field.get('options', [])
                        }
                        populated_section['fields'].append(field_data)
                
                populated['populated_sections'].append(populated_section)
            
            return populated
            
        except Exception as e:
            logger.error(f"❌ Error populating template: {e}")
            return {'error': str(e)}
    
    def validate_template_compliance(self, template_id: str, report_data: Dict) -> Dict[str, Any]:
        """Validate template compliance with SA standards"""
        try:
            template = self.get_template_by_id(template_id)
            if not template:
                return {'valid': False, 'errors': ['Template not found']}
            
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'compliance_level': template.compliance_level,
                'checks_performed': []
            }
            
            # Check required fields
            for section in template.structure.get('sections', []):
                if section.get('required', False):
                    if not report_data.get(section['id']):
                        validation_result['errors'].append(f"Required section '{section['id']}' is missing")
                        validation_result['valid'] = False
                    
                    validation_result['checks_performed'].append(f"Required field check: {section['id']}")
            
            # HPCSA compliance checks
            if template.compliance_level in ['hpcsa', 'medical_aid']:
                hpcsa_requirements = template.hpcsa_requirements
                
                # Check for required HPCSA fields
                required_hpcsa_fields = hpcsa_requirements.get('required_fields', [])
                for field in required_hpcsa_fields:
                    if not report_data.get(field):
                        validation_result['errors'].append(f"HPCSA required field '{field}' is missing")
                        validation_result['valid'] = False
                
                validation_result['checks_performed'].append("HPCSA compliance check")
            
            # Medical aid compliance checks
            if template.compliance_level == 'medical_aid':
                medical_aid_fields = template.medical_aid_fields
                for field in medical_aid_fields:
                    if not report_data.get(field):
                        validation_result['warnings'].append(f"Medical aid field '{field}' is recommended")
                
                validation_result['checks_performed'].append("Medical aid compliance check")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Error validating template compliance: {e}")
            return {'valid': False, 'errors': [str(e)]}
    
    def record_template_usage(self, template_id: str, user_id: str, session_id: str,
                            language: str, completion_data: Dict) -> bool:
        """Record template usage for analytics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO template_usage 
                (template_id, user_id, session_id, language, completion_time,
                 fields_completed, total_fields, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                template_id,
                user_id,
                session_id,
                language,
                completion_data.get('completion_time', 0),
                completion_data.get('fields_completed', 0),
                completion_data.get('total_fields', 0),
                completion_data.get('quality_score', 0.0)
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error recording template usage: {e}")
            return False
    
    def get_template_analytics(self, template_id: str = "", user_id: str = "") -> Dict[str, Any]:
        """Get template usage analytics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM template_usage WHERE 1=1'
            params = []
            
            if template_id:
                query += ' AND template_id = ?'
                params.append(template_id)
            
            if user_id:
                query += ' AND user_id = ?'
                params.append(user_id)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                return {'total_usage': 0, 'analytics': {}}
            
            # Calculate analytics
            total_usage = len(rows)
            avg_completion_time = sum(row[4] for row in rows if row[4]) / total_usage if total_usage > 0 else 0
            avg_quality_score = sum(row[7] for row in rows if row[7]) / total_usage if total_usage > 0 else 0
            
            # Language distribution
            language_dist = {}
            for row in rows:
                lang = row[3]
                language_dist[lang] = language_dist.get(lang, 0) + 1
            
            conn.close()
            
            return {
                'total_usage': total_usage,
                'average_completion_time': round(avg_completion_time, 2),
                'average_quality_score': round(avg_quality_score, 2),
                'language_distribution': language_dist,
                'analytics': {
                    'most_used_language': max(language_dist.items(), key=lambda x: x[1])[0] if language_dist else 'en',
                    'completion_rate': sum(1 for row in rows if row[5] == row[6]) / total_usage if total_usage > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting template analytics: {e}")
            return {'total_usage': 0, 'analytics': {}}

# Global instance
sa_template_engine = SAMedicalTemplateEngine()