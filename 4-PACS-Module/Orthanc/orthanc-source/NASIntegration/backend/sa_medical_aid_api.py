#!/usr/bin/env python3
"""
🏥 SA Medical Aid Integration API
REST endpoints for managing medical aid schemes and member verification
"""

from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
import logging
import sqlite3
import json
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Create blueprint
sa_medical_aid_api = Blueprint('sa_medical_aid_api', __name__, url_prefix='/api/sa/medical-aid')

def require_auth():
    """Simple authentication check"""
    if not session.get('user_id'):
        return jsonify({'error': 'Authentication required', 'error_code': 1004}), 401
    return None

def validate_member_number(scheme_code, member_number):
    """Validate medical aid member number format"""
    if not member_number:
        return False, "Member number is required"
    
    # Clean the number
    clean_number = re.sub(r'[^A-Z0-9]', '', member_number.upper())
    
    # Scheme-specific validation
    validation_rules = {
        'DISCOVERY': {
            'pattern': r'^[A-Z0-9]{8,12}$',
            'description': '8-12 alphanumeric characters'
        },
        'BONITAS': {
            'pattern': r'^[A-Z0-9]{6,10}$',
            'description': '6-10 alphanumeric characters'
        },
        'MOMENTUM': {
            'pattern': r'^[A-Z0-9]{7,11}$',
            'description': '7-11 alphanumeric characters'
        },
        'MEDIHELP': {
            'pattern': r'^[A-Z0-9]{6,9}$',
            'description': '6-9 alphanumeric characters'
        },
        'BESTMED': {
            'pattern': r'^[A-Z0-9]{6,8}$',
            'description': '6-8 alphanumeric characters'
        },
        'GEMS': {
            'pattern': r'^[A-Z0-9]{8,10}$',
            'description': '8-10 alphanumeric characters'
        }
    }
    
    if scheme_code in validation_rules:
        rule = validation_rules[scheme_code]
        if not re.match(rule['pattern'], clean_number):
            return False, f"Invalid member number format for {scheme_code}. Expected: {rule['description']}"
    
    return True, clean_number

def get_database_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect('sa_medical_aid.db')
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
        
        # Medical aid schemes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sa_medical_schemes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_code TEXT UNIQUE NOT NULL,
                scheme_name TEXT NOT NULL,
                short_name TEXT,
                registration_number TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                website TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                supports_api BOOLEAN DEFAULT FALSE,
                api_endpoint TEXT,
                api_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Medical aid members table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sa_medical_aid_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                scheme_code TEXT NOT NULL,
                member_number TEXT NOT NULL,
                member_name TEXT,
                id_number TEXT,
                relationship TEXT DEFAULT 'MAIN_MEMBER',
                status TEXT DEFAULT 'ACTIVE',
                effective_date DATE,
                termination_date DATE,
                benefit_option TEXT,
                annual_threshold DECIMAL(10,2),
                available_benefits TEXT,
                last_verified TIMESTAMP,
                verification_status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(patient_id, scheme_code, member_number)
            )
        ''')
        
        # Benefits and authorizations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sa_medical_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                authorization_number TEXT,
                procedure_code TEXT,
                procedure_description TEXT,
                authorized_amount DECIMAL(10,2),
                co_payment DECIMAL(10,2),
                authorization_date DATE,
                expiry_date DATE,
                status TEXT DEFAULT 'ACTIVE',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES sa_medical_aid_members(id)
            )
        ''')
        
        # Insert default medical schemes
        schemes = [
            ('DISCOVERY', 'Discovery Health Medical Scheme', 'Discovery', '1125', '0860 99 88 77', 'info@discovery.co.za', 'https://www.discovery.co.za'),
            ('BONITAS', 'Bonitas Medical Fund', 'Bonitas', '1222', '0860 002 108', 'info@bonitas.co.za', 'https://www.bonitas.co.za'),
            ('MOMENTUM', 'Momentum Health', 'Momentum', '1144', '0860 11 78 59', 'info@momentum.co.za', 'https://www.momentum.co.za'),
            ('MEDIHELP', 'Medihelp Medical Scheme', 'Medihelp', '1159', '0861 633 433', 'info@medihelp.co.za', 'https://www.medihelp.co.za'),
            ('BESTMED', 'Bestmed Medical Scheme', 'Bestmed', '1252', '0860 002 378', 'info@bestmed.co.za', 'https://www.bestmed.co.za'),
            ('GEMS', 'Government Employees Medical Scheme', 'GEMS', '1279', '0860 436 769', 'info@gems.gov.za', 'https://www.gems.gov.za'),
            ('FEDHEALTH', 'Fedhealth Medical Scheme', 'Fedhealth', '1145', '0860 333 432', 'info@fedhealth.co.za', 'https://www.fedhealth.co.za'),
            ('KEYHEALTH', 'KeyHealth Medical Scheme', 'KeyHealth', '1369', '0860 539 432', 'info@keyhealth.co.za', 'https://www.keyhealth.co.za'),
            ('PROFMED', 'Profmed Medical Scheme', 'Profmed', '1604', '0860 776 363', 'info@profmed.co.za', 'https://www.profmed.co.za'),
            ('SAMWUMED', 'SAMWUMED Medical Scheme', 'SAMWUMED', '1652', '0860 726 988', 'info@samwumed.co.za', 'https://www.samwumed.co.za')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO sa_medical_schemes 
            (scheme_code, scheme_name, short_name, registration_number, contact_phone, contact_email, website) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', schemes)
        
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

@sa_medical_aid_api.route('/schemes', methods=['GET'])
@cross_origin(supports_credentials=True)
def list_schemes():
    """List all medical aid schemes"""
    try:
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM sa_medical_schemes 
                WHERE is_active = 1 
                ORDER BY scheme_name
            ''')
            
            schemes = []
            for row in cursor.fetchall():
                scheme = {
                    'code': row['scheme_code'],
                    'name': row['scheme_name'],
                    'short_name': row['short_name'],
                    'registration_number': row['registration_number'],
                    'contact_phone': row['contact_phone'],
                    'contact_email': row['contact_email'],
                    'website': row['website'],
                    'supports_api': bool(row['supports_api'])
                }
                schemes.append(scheme)
            
            return jsonify({
                'success': True,
                'schemes': schemes
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error listing schemes: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1002}), 500

@sa_medical_aid_api.route('/verify', methods=['POST'])
@cross_origin(supports_credentials=True)
def verify_member():
    """Verify medical aid member"""
    try:
        auth_error = require_auth()
        if auth_error:
            return auth_error
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'error_code': 1002}), 400
        
        # Validate required fields
        required_fields = ['scheme_code', 'member_number']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required', 'error_code': 1002}), 400
        
        scheme_code = data['scheme_code'].upper()
        member_number = data['member_number']
        
        # Validate member number format
        is_valid, clean_number = validate_member_number(scheme_code, member_number)
        if not is_valid:
            return jsonify({'error': clean_number, 'error_code': 1002}), 400
        
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Check if scheme exists
            cursor.execute('SELECT * FROM sa_medical_schemes WHERE scheme_code = ? AND is_active = 1', (scheme_code,))
            scheme = cursor.fetchone()
            if not scheme:
                return jsonify({'error': 'Medical scheme not found', 'error_code': 1002}), 404
            
            # For demo purposes, simulate verification
            # In a real implementation, this would call the medical aid's API
            verification_result = {
                'scheme_code': scheme_code,
                'scheme_name': scheme['scheme_name'],
                'member_number': clean_number,
                'verification_status': 'VERIFIED',
                'member_status': 'ACTIVE',
                'member_name': data.get('member_name', 'Demo Member'),
                'benefit_option': 'Comprehensive',
                'effective_date': '2024-01-01',
                'annual_threshold': 5000.00,
                'available_benefits': [
                    'General Practitioner',
                    'Specialist',
                    'Radiology',
                    'Pathology',
                    'Hospital Cover',
                    'Chronic Medication'
                ],
                'co_payment_required': False,
                'authorization_required': data.get('procedure_code') in ['CT', 'MRI', 'PET'],
                'verified_at': datetime.now().isoformat()
            }
            
            # Store verification result
            if data.get('patient_id'):
                cursor.execute('''
                    INSERT OR REPLACE INTO sa_medical_aid_members (
                        patient_id, scheme_code, member_number, member_name,
                        status, benefit_option, annual_threshold, 
                        last_verified, verification_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['patient_id'],
                    scheme_code,
                    clean_number,
                    verification_result['member_name'],
                    verification_result['member_status'],
                    verification_result['benefit_option'],
                    verification_result['annual_threshold'],
                    datetime.now().isoformat(),
                    'VERIFIED'
                ))
                conn.commit()
            
            return jsonify({
                'success': True,
                'verification': verification_result
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error verifying member: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1002}), 500

@sa_medical_aid_api.route('/member/<patient_id>', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_member_info(patient_id):
    """Get medical aid member information for a patient"""
    try:
        auth_error = require_auth()
        if auth_error:
            return auth_error
        
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    mam.*,
                    sms.scheme_name,
                    sms.short_name,
                    sms.contact_phone
                FROM sa_medical_aid_members mam
                JOIN sa_medical_schemes sms ON mam.scheme_code = sms.scheme_code
                WHERE mam.patient_id = ? AND mam.status = 'ACTIVE'
                ORDER BY mam.created_at DESC
            ''', (patient_id,))
            
            members = []
            for row in cursor.fetchall():
                member = {
                    'id': row['id'],
                    'scheme_code': row['scheme_code'],
                    'scheme_name': row['scheme_name'],
                    'short_name': row['short_name'],
                    'member_number': row['member_number'],
                    'member_name': row['member_name'],
                    'relationship': row['relationship'],
                    'status': row['status'],
                    'benefit_option': row['benefit_option'],
                    'annual_threshold': row['annual_threshold'],
                    'last_verified': row['last_verified'],
                    'verification_status': row['verification_status'],
                    'contact_phone': row['contact_phone']
                }
                members.append(member)
            
            return jsonify({
                'success': True,
                'patient_id': patient_id,
                'medical_aid_members': members
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting member info: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1002}), 500

@sa_medical_aid_api.route('/authorize', methods=['POST'])
@cross_origin(supports_credentials=True)
def request_authorization():
    """Request pre-authorization for a procedure"""
    try:
        auth_error = require_auth()
        if auth_error:
            return auth_error
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'error_code': 1002}), 400
        
        # Validate required fields
        required_fields = ['patient_id', 'scheme_code', 'member_number', 'procedure_code']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required', 'error_code': 1002}), 400
        
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Get member info
            cursor.execute('''
                SELECT id FROM sa_medical_aid_members 
                WHERE patient_id = ? AND scheme_code = ? AND member_number = ?
            ''', (data['patient_id'], data['scheme_code'], data['member_number']))
            
            member = cursor.fetchone()
            if not member:
                return jsonify({'error': 'Member not found', 'error_code': 1002}), 404
            
            # For demo purposes, simulate authorization
            # In a real implementation, this would call the medical aid's authorization API
            authorization_number = f"AUTH{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Determine authorization based on procedure
            procedure_info = {
                'CT': {'description': 'CT Scan', 'amount': 2500.00, 'co_payment': 250.00},
                'MRI': {'description': 'MRI Scan', 'amount': 4500.00, 'co_payment': 450.00},
                'XRAY': {'description': 'X-Ray', 'amount': 350.00, 'co_payment': 0.00},
                'ULTRASOUND': {'description': 'Ultrasound', 'amount': 800.00, 'co_payment': 80.00},
                'MAMMOGRAPHY': {'description': 'Mammography', 'amount': 1200.00, 'co_payment': 120.00}
            }
            
            procedure_code = data['procedure_code'].upper()
            proc_info = procedure_info.get(procedure_code, {
                'description': 'Medical Procedure',
                'amount': 1000.00,
                'co_payment': 100.00
            })
            
            # Store authorization
            cursor.execute('''
                INSERT INTO sa_medical_authorizations (
                    member_id, authorization_number, procedure_code, procedure_description,
                    authorized_amount, co_payment, authorization_date, expiry_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                member['id'],
                authorization_number,
                procedure_code,
                proc_info['description'],
                proc_info['amount'],
                proc_info['co_payment'],
                datetime.now().date().isoformat(),
                (datetime.now() + timedelta(days=30)).date().isoformat(),
                'APPROVED'
            ))
            
            conn.commit()
            
            authorization_result = {
                'authorization_number': authorization_number,
                'status': 'APPROVED',
                'procedure_code': procedure_code,
                'procedure_description': proc_info['description'],
                'authorized_amount': proc_info['amount'],
                'co_payment': proc_info['co_payment'],
                'authorization_date': datetime.now().date().isoformat(),
                'expiry_date': (datetime.now() + timedelta(days=30)).date().isoformat(),
                'notes': 'Pre-authorization approved for medical imaging procedure'
            }
            
            return jsonify({
                'success': True,
                'authorization': authorization_result
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error requesting authorization: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1002}), 500

@sa_medical_aid_api.route('/stats', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_stats():
    """Get medical aid statistics"""
    try:
        auth_error = require_auth()
        if auth_error:
            return auth_error
        
        conn = get_database_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Total members
            cursor.execute('SELECT COUNT(*) as total FROM sa_medical_aid_members WHERE status = "ACTIVE"')
            total_members = cursor.fetchone()['total']
            
            # Verified members
            cursor.execute('SELECT COUNT(*) as verified FROM sa_medical_aid_members WHERE verification_status = "VERIFIED"')
            verified_members = cursor.fetchone()['verified']
            
            # By scheme
            cursor.execute('''
                SELECT 
                    mam.scheme_code,
                    sms.scheme_name,
                    COUNT(*) as member_count
                FROM sa_medical_aid_members mam
                JOIN sa_medical_schemes sms ON mam.scheme_code = sms.scheme_code
                WHERE mam.status = 'ACTIVE'
                GROUP BY mam.scheme_code, sms.scheme_name
                ORDER BY member_count DESC
            ''')
            
            by_scheme = []
            for row in cursor.fetchall():
                by_scheme.append({
                    'scheme_code': row['scheme_code'],
                    'scheme_name': row['scheme_name'],
                    'member_count': row['member_count']
                })
            
            # Recent authorizations
            cursor.execute('''
                SELECT COUNT(*) as total_authorizations
                FROM sa_medical_authorizations
                WHERE authorization_date >= date('now', '-30 days')
            ''')
            recent_authorizations = cursor.fetchone()['total_authorizations']
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_members': total_members,
                    'verified_members': verified_members,
                    'verification_rate': round((verified_members / total_members * 100) if total_members > 0 else 0, 1),
                    'recent_authorizations': recent_authorizations,
                    'by_scheme': by_scheme
                }
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1002}), 500