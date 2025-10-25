#!/usr/bin/env python3
"""
🏥 SA Healthcare Professionals API
REST endpoints for managing healthcare professionals with HPCSA validation
"""

from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
import logging
import sqlite3
import json
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

# Create blueprint
sa_professionals_api = Blueprint('sa_professionals_api', __name__, url_prefix='/api/sa/professionals')

def require_auth():
    """Simple authentication check"""
    if not session.get('user_id'):
        return jsonify({'error': 'Authentication required', 'error_code': 1004}), 401
    return None

def require_admin():
    """Admin privilege check"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    if session.get('role') not in ['admin', 'administrator']:
        return jsonify({'error': 'Admin privileges required', 'error_code': 1004}), 403
    return None

def validate_hpcsa_number(hpcsa_number):
    """Validate HPCSA number format"""
    if not hpcsa_number:
        return False, "HPCSA number is required"
    
    # Clean the number
    clean_number = re.sub(r'[^A-Z0-9]', '', hpcsa_number.upper())
    
    # Check format: 2-3 letters + 6 digits
    if not re.match(r'^[A-Z]{2,3}\d{6}$', clean_number):
        return False, "Invalid HPCSA number format. Expected: XX123456 (2-3 letters + 6 digits)"
    
    # Check valid prefixes
    valid_prefixes = ['MP', 'DP', 'PS', 'DT', 'OH', 'EM', 'OT', 'PT', 'PO', 'OP', 'SP', 'AU']
    prefix = clean_number[:2] if len(clean_number) == 8 else clean_number[:3]
    
    if prefix not in valid_prefixes:
        return False, f"Invalid HPCSA category: {prefix}"
    
    return True, clean_number

def validate_sa_id_number(id_number):
    """Validate SA ID number format"""
    if not id_number:
        return True, ""  # Optional field
    
    # Remove spaces and non-digits
    clean_id = re.sub(r'[^0-9]', '', id_number)
    
    if len(clean_id) != 13:
        return False, "SA ID number must be 13 digits"
    
    # Basic Luhn algorithm check (simplified)
    try:
        # Check if it's all digits
        int(clean_id)
        return True, clean_id
    except ValueError:
        return False, "SA ID number must contain only digits"

def get_database_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect('sa_healthcare_professionals.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database tables"""
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Healthcare professionals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sa_healthcare_professionals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hpcsa_number TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                id_number TEXT,
                email TEXT,
                phone TEXT,
                registration_category TEXT NOT NULL,
                specialization TEXT,
                registration_date DATE,
                registration_status TEXT DEFAULT 'ACTIVE',
                practice_name TEXT,
                practice_number TEXT,
                province_code TEXT NOT NULL,
                city TEXT,
                postal_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                hpcsa_verified BOOLEAN DEFAULT FALSE,
                hpcsa_verified_date TIMESTAMP NULL,
                last_verification_attempt TIMESTAMP NULL,
                verification_attempts INTEGER DEFAULT 0
            )
        ''')
        
        # HPCSA categories reference
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sa_hpcsa_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_code TEXT UNIQUE NOT NULL,
                category_name TEXT NOT NULL,
                description TEXT,
                prefix TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Insert default categories
        categories = [
            ('MP', 'Medical Practitioner', 'Registered medical doctors', 'MP'),
            ('DP', 'Dental Practitioner', 'Registered dentists', 'DP'),
            ('PS', 'Psychology', 'Registered psychologists', 'PS'),
            ('DT', 'Dental Therapy', 'Registered dental therapists', 'DT'),
            ('OH', 'Oral Hygiene', 'Registered oral hygienists', 'OH'),
            ('EM', 'Emergency Medical Care', 'Emergency medical care practitioners', 'EM'),
            ('OT', 'Occupational Therapy', 'Registered occupational therapists', 'OT'),
            ('PT', 'Physiotherapy', 'Registered physiotherapists', 'PT'),
            ('PO', 'Podiatry', 'Registered podiatrists', 'PO'),
            ('OP', 'Optometry', 'Registered optometrists', 'OP'),
            ('SP', 'Speech-Language Pathology', 'Speech-language pathologists', 'SP'),
            ('AU', 'Audiology', 'Registered audiologists', 'AU')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO sa_hpcsa_categories 
            (category_code, category_name, description, prefix) 
            VALUES (?, ?, ?, ?)
        ''', categories)
        
        # SA provinces reference
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sa_provinces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                province_code TEXT UNIQUE NOT NULL,
                province_name TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        provinces = [
            ('GP', 'Gauteng'),
            ('WC', 'Western Cape'),
            ('KZN', 'KwaZulu-Natal'),
            ('EC', 'Eastern Cape'),
            ('FS', 'Free State'),
            ('LP', 'Limpopo'),
            ('MP', 'Mpumalanga'),
            ('NC', 'Northern Cape'),
            ('NW', 'North West')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO sa_provinces (province_code, province_name) 
            VALUES (?, ?)
        ''', provinces)
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False
    finally:
        conn.close()

# Initialize database on import
init_database()

# ===== REST API ENDPOINTS =====

@sa_professionals_api.route('', methods=['GET'])
@cross_origin(supports_credentials=True)
def list_professionals():
    """List all healthcare professionals"""
    try:
        auth_error = require_auth()
        if auth_error:
            return auth_error
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        province = request.args.get('province', '')
        status = request.args.get('status', 'ACTIVE')
        
        offset = (page - 1) * limit
        
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Build query
            where_conditions = ['hp.is_active = 1']
            params = []
            
            if search:
                where_conditions.append('(hp.first_name LIKE ? OR hp.last_name LIKE ? OR hp.hpcsa_number LIKE ?)')
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])
            
            if category:
                where_conditions.append('hp.registration_category = ?')
                params.append(category)
            
            if province:
                where_conditions.append('hp.province_code = ?')
                params.append(province)
            
            if status:
                where_conditions.append('hp.registration_status = ?')
                params.append(status)
            
            where_clause = ' AND '.join(where_conditions)
            
            # Get total count
            count_query = f'''
                SELECT COUNT(*) as total
                FROM sa_healthcare_professionals hp
                WHERE {where_clause}
            '''
            
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # Get professionals
            query = f'''
                SELECT 
                    hp.*,
                    hc.category_name,
                    sp.province_name
                FROM sa_healthcare_professionals hp
                LEFT JOIN sa_hpcsa_categories hc ON hp.registration_category = hc.category_code
                LEFT JOIN sa_provinces sp ON hp.province_code = sp.province_code
                WHERE {where_clause}
                ORDER BY hp.last_name, hp.first_name
                LIMIT ? OFFSET ?
            '''
            
            cursor.execute(query, params + [limit, offset])
            professionals = []
            
            for row in cursor.fetchall():
                professional = {
                    'id': row['id'],
                    'hpcsa_number': row['hpcsa_number'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'full_name': f"{row['first_name']} {row['last_name']}",
                    'email': row['email'],
                    'phone': row['phone'],
                    'registration_category': row['registration_category'],
                    'category_name': row['category_name'],
                    'specialization': row['specialization'],
                    'registration_status': row['registration_status'],
                    'practice_name': row['practice_name'],
                    'province_code': row['province_code'],
                    'province_name': row['province_name'],
                    'city': row['city'],
                    'hpcsa_verified': bool(row['hpcsa_verified']),
                    'hpcsa_verified_date': row['hpcsa_verified_date'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                professionals.append(professional)
            
            return jsonify({
                'success': True,
                'professionals': professionals,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit
                }
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error listing professionals: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1000}), 500

@sa_professionals_api.route('', methods=['POST'])
@cross_origin(supports_credentials=True)
def create_professional():
    """Register a new healthcare professional"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'error_code': 1000}), 400
        
        # Validate required fields
        required_fields = ['hpcsa_number', 'first_name', 'last_name', 'registration_category', 'province_code']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required', 'error_code': 1000}), 400
        
        # Validate HPCSA number
        is_valid, hpcsa_result = validate_hpcsa_number(data['hpcsa_number'])
        if not is_valid:
            return jsonify({'error': hpcsa_result, 'error_code': 1000}), 400
        
        # Validate SA ID number if provided
        if data.get('id_number'):
            is_valid, id_result = validate_sa_id_number(data['id_number'])
            if not is_valid:
                return jsonify({'error': id_result, 'error_code': 1000}), 400
            data['id_number'] = id_result
        
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Check if HPCSA number already exists
            cursor.execute('SELECT id FROM sa_healthcare_professionals WHERE hpcsa_number = ?', (hpcsa_result,))
            if cursor.fetchone():
                return jsonify({'error': 'HPCSA number already registered', 'error_code': 1000}), 400
            
            # Insert new professional
            cursor.execute('''
                INSERT INTO sa_healthcare_professionals (
                    hpcsa_number, first_name, last_name, id_number, email, phone,
                    registration_category, specialization, practice_name, practice_number,
                    province_code, city, postal_code, created_by, registration_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                hpcsa_result,
                data['first_name'],
                data['last_name'],
                data.get('id_number'),
                data.get('email'),
                data.get('phone'),
                data['registration_category'],
                data.get('specialization'),
                data.get('practice_name'),
                data.get('practice_number'),
                data['province_code'],
                data.get('city'),
                data.get('postal_code'),
                session.get('username', 'admin'),
                datetime.now().isoformat()
            ))
            
            professional_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Healthcare professional registered successfully',
                'professional_id': professional_id,
                'hpcsa_number': hpcsa_result
            }), 201
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error creating professional: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1000}), 500

@sa_professionals_api.route('/<hpcsa_number>', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_professional(hpcsa_number):
    """Get professional details by HPCSA number"""
    try:
        auth_error = require_auth()
        if auth_error:
            return auth_error
        
        # Validate HPCSA number format
        is_valid, clean_hpcsa = validate_hpcsa_number(hpcsa_number)
        if not is_valid:
            return jsonify({'error': clean_hpcsa, 'error_code': 1000}), 400
        
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    hp.*,
                    hc.category_name,
                    sp.province_name
                FROM sa_healthcare_professionals hp
                LEFT JOIN sa_hpcsa_categories hc ON hp.registration_category = hc.category_code
                LEFT JOIN sa_provinces sp ON hp.province_code = sp.province_code
                WHERE hp.hpcsa_number = ? AND hp.is_active = 1
            ''', (clean_hpcsa,))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': 'Professional not found', 'error_code': 1000}), 404
            
            professional = {
                'id': row['id'],
                'hpcsa_number': row['hpcsa_number'],
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'full_name': f"{row['first_name']} {row['last_name']}",
                'id_number': row['id_number'],
                'email': row['email'],
                'phone': row['phone'],
                'registration_category': row['registration_category'],
                'category_name': row['category_name'],
                'specialization': row['specialization'],
                'registration_date': row['registration_date'],
                'registration_status': row['registration_status'],
                'practice_name': row['practice_name'],
                'practice_number': row['practice_number'],
                'province_code': row['province_code'],
                'province_name': row['province_name'],
                'city': row['city'],
                'postal_code': row['postal_code'],
                'hpcsa_verified': bool(row['hpcsa_verified']),
                'hpcsa_verified_date': row['hpcsa_verified_date'],
                'last_verification_attempt': row['last_verification_attempt'],
                'verification_attempts': row['verification_attempts'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'created_by': row['created_by']
            }
            
            return jsonify({
                'success': True,
                'professional': professional
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting professional: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1000}), 500

@sa_professionals_api.route('/<hpcsa_number>/verify', methods=['POST'])
@cross_origin(supports_credentials=True)
def verify_professional(hpcsa_number):
    """Verify HPCSA registration"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        # Validate HPCSA number format
        is_valid, clean_hpcsa = validate_hpcsa_number(hpcsa_number)
        if not is_valid:
            return jsonify({'error': clean_hpcsa, 'error_code': 1000}), 400
        
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Check if professional exists
            cursor.execute('SELECT id FROM sa_healthcare_professionals WHERE hpcsa_number = ?', (clean_hpcsa,))
            professional = cursor.fetchone()
            if not professional:
                return jsonify({'error': 'Professional not found', 'error_code': 1000}), 404
            
            # Update verification status
            cursor.execute('''
                UPDATE sa_healthcare_professionals 
                SET hpcsa_verified = 1, 
                    hpcsa_verified_date = ?, 
                    last_verification_attempt = ?,
                    verification_attempts = verification_attempts + 1,
                    updated_at = ?
                WHERE hpcsa_number = ?
            ''', (
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                clean_hpcsa
            ))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Professional verification updated successfully',
                'hpcsa_number': clean_hpcsa,
                'verified': True,
                'verified_date': datetime.now().isoformat()
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error verifying professional: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1000}), 500

@sa_professionals_api.route('/categories', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_categories():
    """Get HPCSA categories"""
    try:
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sa_hpcsa_categories WHERE is_active = 1 ORDER BY category_name')
            
            categories = []
            for row in cursor.fetchall():
                categories.append({
                    'code': row['category_code'],
                    'name': row['category_name'],
                    'description': row['description'],
                    'prefix': row['prefix']
                })
            
            return jsonify({
                'success': True,
                'categories': categories
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1000}), 500

@sa_professionals_api.route('/provinces', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_provinces():
    """Get SA provinces"""
    try:
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sa_provinces WHERE is_active = 1 ORDER BY province_name')
            
            provinces = []
            for row in cursor.fetchall():
                provinces.append({
                    'code': row['province_code'],
                    'name': row['province_name']
                })
            
            return jsonify({
                'success': True,
                'provinces': provinces
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting provinces: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1000}), 500

@sa_professionals_api.route('/stats', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_stats():
    """Get healthcare professionals statistics"""
    try:
        auth_error = require_auth()
        if auth_error:
            return auth_error
        
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Total professionals
            cursor.execute('SELECT COUNT(*) as total FROM sa_healthcare_professionals WHERE is_active = 1')
            total = cursor.fetchone()['total']
            
            # Verified professionals
            cursor.execute('SELECT COUNT(*) as verified FROM sa_healthcare_professionals WHERE is_active = 1 AND hpcsa_verified = 1')
            verified = cursor.fetchone()['verified']
            
            # By category
            cursor.execute('''
                SELECT hp.registration_category, hc.category_name, COUNT(*) as count
                FROM sa_healthcare_professionals hp
                LEFT JOIN sa_hpcsa_categories hc ON hp.registration_category = hc.category_code
                WHERE hp.is_active = 1
                GROUP BY hp.registration_category, hc.category_name
                ORDER BY count DESC
            ''')
            
            by_category = []
            for row in cursor.fetchall():
                by_category.append({
                    'category': row['registration_category'],
                    'category_name': row['category_name'],
                    'count': row['count']
                })
            
            # By province
            cursor.execute('''
                SELECT hp.province_code, sp.province_name, COUNT(*) as count
                FROM sa_healthcare_professionals hp
                LEFT JOIN sa_provinces sp ON hp.province_code = sp.province_code
                WHERE hp.is_active = 1
                GROUP BY hp.province_code, sp.province_name
                ORDER BY count DESC
            ''')
            
            by_province = []
            for row in cursor.fetchall():
                by_province.append({
                    'province': row['province_code'],
                    'province_name': row['province_name'],
                    'count': row['count']
                })
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_professionals': total,
                    'verified_professionals': verified,
                    'verification_rate': round((verified / total * 100) if total > 0 else 0, 1),
                    'by_category': by_category,
                    'by_province': by_province
                }
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1000}), 500