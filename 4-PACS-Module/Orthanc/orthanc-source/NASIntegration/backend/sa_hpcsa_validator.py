#!/usr/bin/env python3
"""
🏥 SA HPCSA Number Validation System
Comprehensive validation system for South African healthcare professional registration numbers
"""

import re
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json

logger = logging.getLogger(__name__)

class HPCSAValidator:
    """HPCSA number validation and management system"""
    
    # HPCSA Registration Categories and their validation patterns
    REGISTRATION_CATEGORIES = {
        'MP': {
            'name': 'Medical Practitioner',
            'pattern': r'^MP[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Qualified medical doctors'
        },
        'DP': {
            'name': 'Dental Practitioner',
            'pattern': r'^DP[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Qualified dentists'
        },
        'DT': {
            'name': 'Dental Therapist',
            'pattern': r'^DT[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Dental therapy professionals'
        },
        'PS': {
            'name': 'Medical Specialist',
            'pattern': r'^PS[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Medical specialists in various fields'
        },
        'RP': {
            'name': 'Radiographer',
            'pattern': r'^RP[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Medical imaging professionals'
        },
        'RT': {
            'name': 'Radiation Therapist',
            'pattern': r'^RT[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Radiation therapy professionals'
        },
        'OT': {
            'name': 'Occupational Therapist',
            'pattern': r'^OT[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Occupational therapy professionals'
        },
        'PT': {
            'name': 'Physiotherapist',
            'pattern': r'^PT[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Physiotherapy professionals'
        },
        'SP': {
            'name': 'Speech-Language Pathologist',
            'pattern': r'^SP[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Speech and language therapy professionals'
        },
        'AU': {
            'name': 'Audiologist',
            'pattern': r'^AU[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Hearing and balance professionals'
        },
        'OP': {
            'name': 'Optometrist',
            'pattern': r'^OP[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Eye care professionals'
        },
        'CP': {
            'name': 'Clinical Psychologist',
            'pattern': r'^CP[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Clinical psychology professionals'
        },
        'PO': {
            'name': 'Podiatrist',
            'pattern': r'^PO[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Foot and ankle care professionals'
        },
        'CH': {
            'name': 'Chiropractor',
            'pattern': r'^CH[0-9]{6,8}$',
            'min_length': 8,
            'max_length': 10,
            'description': 'Chiropractic professionals'
        }
    }
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or 'sa_healthcare.db'
        self.validation_cache = {}
        self.cache_expiry = timedelta(hours=24)
    
    def validate_hpcsa_number(self, hpcsa_number: str, registration_category: str = None) -> Dict[str, Any]:
        """
        Validate HPCSA number format and structure
        
        Args:
            hpcsa_number: The HPCSA number to validate
            registration_category: Optional specific category to validate against
            
        Returns:
            Dict containing validation results
        """
        result = {
            'is_valid': False,
            'hpcsa_number': hpcsa_number.upper().strip() if hpcsa_number else '',
            'detected_category': None,
            'category_name': None,
            'errors': [],
            'warnings': []
        }
        
        if not hpcsa_number:
            result['errors'].append('HPCSA number is required')
            return result
        
        hpcsa_number = hpcsa_number.upper().strip()
        result['hpcsa_number'] = hpcsa_number
        
        # Basic format validation
        if len(hpcsa_number) < 6:
            result['errors'].append('HPCSA number too short (minimum 6 characters)')
            return result
        
        if len(hpcsa_number) > 12:
            result['errors'].append('HPCSA number too long (maximum 12 characters)')
            return result
        
        # Extract category prefix
        category_match = re.match(r'^([A-Z]{1,3})', hpcsa_number)
        if not category_match:
            result['errors'].append('Invalid HPCSA number format - must start with letters')
            return result
        
        detected_category = category_match.group(1)
        result['detected_category'] = detected_category
        
        # Validate against known categories
        if detected_category not in self.REGISTRATION_CATEGORIES:
            result['errors'].append(f'Unknown registration category: {detected_category}')
            result['warnings'].append('This may be a valid but unrecognized category')
            return result
        
        category_info = self.REGISTRATION_CATEGORIES[detected_category]
        result['category_name'] = category_info['name']
        
        # If specific category provided, check match
        if registration_category and registration_category != detected_category:
            result['errors'].append(f'Category mismatch: expected {registration_category}, found {detected_category}')
            return result
        
        # Validate format pattern
        if not re.match(category_info['pattern'], hpcsa_number):
            result['errors'].append(f'Invalid format for {category_info["name"]} - expected pattern: {category_info["pattern"]}')
            return result
        
        # Validate length
        if len(hpcsa_number) < category_info['min_length']:
            result['errors'].append(f'Number too short for {category_info["name"]} (minimum {category_info["min_length"]} characters)')
            return result
        
        if len(hpcsa_number) > category_info['max_length']:
            result['errors'].append(f'Number too long for {category_info["name"]} (maximum {category_info["max_length"]} characters)')
            return result
        
        # Extract numeric part for additional validation
        numeric_part = hpcsa_number[len(detected_category):]
        if not numeric_part.isdigit():
            result['errors'].append('Numeric part contains non-digit characters')
            return result
        
        # Additional validation rules
        if len(numeric_part) < 6:
            result['errors'].append('Numeric part too short (minimum 6 digits)')
            return result
        
        # Check for obviously invalid patterns
        if numeric_part == '000000' or numeric_part == '111111':
            result['warnings'].append('Number appears to be a test or placeholder value')
        
        # If we get here, the number is valid
        result['is_valid'] = True
        
        return result
    
    def validate_and_store(self, professional_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate HPCSA number and store professional data
        
        Args:
            professional_data: Dictionary containing professional information
            
        Returns:
            Dict containing validation and storage results
        """
        hpcsa_number = professional_data.get('hpcsa_number', '')
        registration_category = professional_data.get('registration_category', '')
        
        # Validate HPCSA number
        validation_result = self.validate_hpcsa_number(hpcsa_number, registration_category)
        
        if not validation_result['is_valid']:
            return {
                'success': False,
                'validation': validation_result,
                'message': 'HPCSA number validation failed'
            }
        
        # Check if professional already exists
        existing = self.get_professional_by_hpcsa(hpcsa_number)
        if existing:
            return {
                'success': False,
                'validation': validation_result,
                'message': 'Professional with this HPCSA number already exists',
                'existing_professional': existing
            }
        
        # Store professional data
        try:
            professional_id = self.store_professional(professional_data, validation_result)
            return {
                'success': True,
                'validation': validation_result,
                'professional_id': professional_id,
                'message': 'Professional successfully validated and stored'
            }
        except Exception as e:
            logger.error(f"Error storing professional: {e}")
            return {
                'success': False,
                'validation': validation_result,
                'message': f'Error storing professional: {str(e)}'
            }
    
    def get_professional_by_hpcsa(self, hpcsa_number: str) -> Optional[Dict[str, Any]]:
        """Get professional by HPCSA number"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM vw_active_healthcare_professionals 
                    WHERE hpcsa_number = ? AND is_active = 1 AND is_deleted = 0
                """, (hpcsa_number.upper(),))
                
                row = cursor.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Error getting professional by HPCSA: {e}")
            return None
    
    def store_professional(self, professional_data: Dict[str, Any], validation_result: Dict[str, Any]) -> int:
        """Store professional data in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Prepare data for insertion
                insert_data = {
                    'hpcsa_number': validation_result['hpcsa_number'],
                    'first_name': professional_data.get('first_name', ''),
                    'last_name': professional_data.get('last_name', ''),
                    'middle_names': professional_data.get('middle_names'),
                    'email': professional_data.get('email'),
                    'phone_primary': professional_data.get('phone_primary'),
                    'phone_secondary': professional_data.get('phone_secondary'),
                    'registration_category': validation_result['detected_category'],
                    'registration_status': professional_data.get('registration_status', 'ACTIVE'),
                    'specialization': professional_data.get('specialization'),
                    'sub_specialization': professional_data.get('sub_specialization'),
                    'province_code': professional_data.get('province_code'),
                    'practice_city': professional_data.get('practice_city'),
                    'practice_address': professional_data.get('practice_address'),
                    'practice_postal_code': professional_data.get('practice_postal_code'),
                    'initial_registration_date': professional_data.get('initial_registration_date'),
                    'current_registration_date': professional_data.get('current_registration_date'),
                    'registration_expiry_date': professional_data.get('registration_expiry_date'),
                    'primary_qualification': professional_data.get('primary_qualification'),
                    'additional_qualifications': json.dumps(professional_data.get('additional_qualifications', [])),
                    'practice_type': professional_data.get('practice_type'),
                    'practice_name': professional_data.get('practice_name'),
                    'hospital_affiliations': json.dumps(professional_data.get('hospital_affiliations', [])),
                    'hpcsa_validation_status': 'VALIDATED',
                    'hpcsa_validation_date': datetime.now().isoformat(),
                    'hpcsa_validation_details': json.dumps(validation_result),
                    'created_by': professional_data.get('created_by', 'SYSTEM'),
                    'metadata': json.dumps(professional_data.get('metadata', {})),
                    'notes': professional_data.get('notes')
                }
                
                # Build INSERT query
                columns = [k for k, v in insert_data.items() if v is not None]
                values = [insert_data[k] for k in columns]
                placeholders = ','.join(['?' for _ in columns])
                
                query = f"""
                    INSERT INTO sa_healthcare_professionals ({','.join(columns)})
                    VALUES ({placeholders})
                """
                
                cursor.execute(query, values)
                professional_id = cursor.lastrowid
                
                logger.info(f"Stored professional {validation_result['hpcsa_number']} with ID {professional_id}")
                return professional_id
                
        except Exception as e:
            logger.error(f"Error storing professional: {e}")
            raise
    
    def search_professionals(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search professionals with various criteria"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Build search query
                where_conditions = ["is_active = 1", "is_deleted = 0"]
                params = []
                
                if search_params.get('hpcsa_number'):
                    where_conditions.append("hpcsa_number LIKE ?")
                    params.append(f"%{search_params['hpcsa_number']}%")
                
                if search_params.get('name'):
                    where_conditions.append("(first_name LIKE ? OR last_name LIKE ?)")
                    params.extend([f"%{search_params['name']}%", f"%{search_params['name']}%"])
                
                if search_params.get('registration_category'):
                    where_conditions.append("registration_category = ?")
                    params.append(search_params['registration_category'])
                
                if search_params.get('province_code'):
                    where_conditions.append("province_code = ?")
                    params.append(search_params['province_code'])
                
                if search_params.get('specialization'):
                    where_conditions.append("specialization = ?")
                    params.append(search_params['specialization'])
                
                if search_params.get('validation_status'):
                    where_conditions.append("hpcsa_validation_status = ?")
                    params.append(search_params['validation_status'])
                
                # Build final query
                query = f"""
                    SELECT * FROM vw_active_healthcare_professionals
                    WHERE {' AND '.join(where_conditions)}
                    ORDER BY last_name, first_name
                    LIMIT ?
                """
                params.append(search_params.get('limit', 100))
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error searching professionals: {e}")
            return []
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get overall statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_professionals,
                        SUM(CASE WHEN hpcsa_validation_status = 'VALIDATED' THEN 1 ELSE 0 END) as validated_count,
                        SUM(CASE WHEN hpcsa_validation_status = 'PENDING' THEN 1 ELSE 0 END) as pending_count,
                        SUM(CASE WHEN hpcsa_validation_status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
                        SUM(CASE WHEN registration_status = 'ACTIVE' THEN 1 ELSE 0 END) as active_count
                    FROM sa_healthcare_professionals
                    WHERE is_active = 1 AND is_deleted = 0
                """)
                
                overall_stats = dict(cursor.fetchone())
                
                # Get category breakdown
                cursor.execute("""
                    SELECT * FROM vw_hpcsa_validation_stats
                    ORDER BY total_professionals DESC
                """)
                
                category_stats = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'overall': overall_stats,
                    'by_category': category_stats,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting validation statistics: {e}")
            return {}
    
    def update_validation_status(self, hpcsa_number: str, status: str, details: str = None, updated_by: str = None) -> bool:
        """Update validation status for a professional"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                update_data = {
                    'hpcsa_validation_status': status,
                    'hpcsa_validation_date': datetime.now().isoformat(),
                    'updated_by': updated_by or 'SYSTEM',
                    'updated_at': datetime.now().isoformat()
                }
                
                if details:
                    update_data['hpcsa_validation_details'] = details
                
                # Build UPDATE query
                set_clauses = [f"{k} = ?" for k in update_data.keys()]
                values = list(update_data.values())
                values.append(hpcsa_number.upper())
                
                query = f"""
                    UPDATE sa_healthcare_professionals 
                    SET {', '.join(set_clauses)}
                    WHERE hpcsa_number = ? AND is_active = 1 AND is_deleted = 0
                """
                
                cursor.execute(query, values)
                
                if cursor.rowcount > 0:
                    logger.info(f"Updated validation status for {hpcsa_number} to {status}")
                    return True
                else:
                    logger.warning(f"No professional found with HPCSA number {hpcsa_number}")
                    return False
                
        except Exception as e:
            logger.error(f"Error updating validation status: {e}")
            return False
    
    def get_registration_categories(self) -> List[Dict[str, Any]]:
        """Get all registration categories"""
        return [
            {
                'code': code,
                'name': info['name'],
                'description': info['description'],
                'pattern': info['pattern'],
                'min_length': info['min_length'],
                'max_length': info['max_length']
            }
            for code, info in self.REGISTRATION_CATEGORIES.items()
        ]
    
    def validate_bulk_hpcsa_numbers(self, hpcsa_numbers: List[str]) -> Dict[str, Any]:
        """Validate multiple HPCSA numbers at once"""
        results = {
            'total_processed': len(hpcsa_numbers),
            'valid_count': 0,
            'invalid_count': 0,
            'results': []
        }
        
        for hpcsa_number in hpcsa_numbers:
            validation_result = self.validate_hpcsa_number(hpcsa_number)
            results['results'].append(validation_result)
            
            if validation_result['is_valid']:
                results['valid_count'] += 1
            else:
                results['invalid_count'] += 1
        
        results['success_rate'] = (results['valid_count'] / results['total_processed']) * 100 if results['total_processed'] > 0 else 0
        
        return results


# Utility functions for integration with Flask app
def create_hpcsa_validator(db_path: str = None) -> HPCSAValidator:
    """Create HPCSA validator instance"""
    return HPCSAValidator(db_path)

def validate_hpcsa_number_simple(hpcsa_number: str, registration_category: str = None) -> bool:
    """Simple validation function that returns True/False"""
    validator = HPCSAValidator()
    result = validator.validate_hpcsa_number(hpcsa_number, registration_category)
    return result['is_valid']

def get_hpcsa_category_from_number(hpcsa_number: str) -> Optional[str]:
    """Extract registration category from HPCSA number"""
    if not hpcsa_number:
        return None
    
    category_match = re.match(r'^([A-Z]{1,3})', hpcsa_number.upper().strip())
    return category_match.group(1) if category_match else None