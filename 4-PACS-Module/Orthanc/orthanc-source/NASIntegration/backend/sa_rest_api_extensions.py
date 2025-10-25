#!/usr/bin/env python3
"""
🌐 SA Healthcare REST API Extensions
Comprehensive REST API endpoints for South African healthcare integration
"""

from flask import Blueprint, request, jsonify, session, g
from flask_cors import cross_origin
import logging
import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import re
from functools import wraps

logger = logging.getLogger(__name__)

# Create blueprint for SA REST API extensions
sa_rest_api = Blueprint('sa_rest_api', __name__, url_prefix='/api/sa')

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required', 'error_code': 1004}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_role(required_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('user_role', 'USER')
            if user_role not in required_roles:
                return jsonify({'error': 'Insufficient permissions', 'error_code': 1005}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_db_connection():
    """Get database connection"""
    # Use a simple in-memory database for now to avoid file issues
    try:
        # Try to use existing database if available
        db_path = os.path.join(os.getcwd(), 'data', 'sa_healthcare.db')
        if os.path.exists(db_path):
            return sqlite3.connect(db_path)
        else:
            # Create in-memory database for testing
            return sqlite3.connect(':memory:')
    except Exception:
        # Fallback to in-memory database
        return sqlite3.connect(':memory:')

# ===== HEALTHCARE PROFESSIONAL MANAGEMENT ENDPOINTS =====

@sa_rest_api.route('/professionals', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_healthcare_professionals():
    """Get list of healthcare professionals with filtering and pagination"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)  # Max 100 per page
        search = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        province = request.args.get('province', '').strip()
        specialization = request.args.get('specialization', '').strip()
        validation_status = request.args.get('validation_status', '').strip()
        
        offset = (page - 1) * per_page
        
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query with filters
            where_conditions = ["is_active = 1", "is_deleted = 0"]
            params = []
            
            if search:
                where_conditions.append("(first_name LIKE ? OR last_name LIKE ? OR hpcsa_number LIKE ?)")
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])
            
            if category:
                where_conditions.append("registration_category = ?")
                params.append(category)
            
            if province:
                where_conditions.append("province_code = ?")
                params.append(province)
            
            if specialization:
                where_conditions.append("specialization = ?")
                params.append(specialization)
            
            if validation_status:
                where_conditions.append("hpcsa_validation_status = ?")
                params.append(validation_status)
            
            # Get total count
            count_query = f"""
                SELECT COUNT(*) FROM vw_active_healthcare_professionals
                WHERE {' AND '.join(where_conditions)}
            """
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Get paginated results
            query = f"""
                SELECT * FROM vw_active_healthcare_professionals
                WHERE {' AND '.join(where_conditions)}
                ORDER BY last_name, first_name
                LIMIT ? OFFSET ?
            """
            params.extend([per_page, offset])
            
            cursor.execute(query, params)
            professionals = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'success': True,
                'professionals': professionals,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                },
                'filters': {
                    'search': search,
                    'category': category,
                    'province': province,
                    'specialization': specialization,
                    'validation_status': validation_status
                }
            })
            
    except Exception as e:
        logger.error(f"Error getting healthcare professionals: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

@sa_rest_api.route('/professionals', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
@require_role(['ADMINISTRATOR', 'MANAGER'])
def create_healthcare_professional():
    """Create new healthcare professional"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data required', 'error_code': 1003}), 400
        
        # Validate required fields
        required_fields = ['hpcsa_number', 'first_name', 'last_name', 'registration_category', 'province_code']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required', 'error_code': 1003}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if HPCSA number already exists
            cursor.execute("SELECT id FROM sa_healthcare_professionals WHERE hpcsa_number = ?", 
                         (data['hpcsa_number'],))
            if cursor.fetchone():
                return jsonify({'error': 'HPCSA number already exists', 'error_code': 1006}), 409
            
            # Insert new professional
            cursor.execute("""
                INSERT INTO sa_healthcare_professionals (
                    hpcsa_number, first_name, last_name, middle_names,
                    email, phone_primary, phone_secondary,
                    registration_category, registration_status, specialization,
                    sub_specialization, province_code, practice_city,
                    practice_address, practice_postal_code,
                    initial_registration_date, current_registration_date,
                    registration_expiry_date, primary_qualification,
                    additional_qualifications, practice_type, practice_name,
                    hospital_affiliations, hpcsa_validation_status,
                    created_by, metadata, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['hpcsa_number'],
                data['first_name'],
                data['last_name'],
                data.get('middle_names'),
                data.get('email'),
                data.get('phone_primary'),
                data.get('phone_secondary'),
                data['registration_category'],
                data.get('registration_status', 'ACTIVE'),
                data.get('specialization'),
                data.get('sub_specialization'),
                data['province_code'],
                data.get('practice_city'),
                data.get('practice_address'),
                data.get('practice_postal_code'),
                data.get('initial_registration_date'),
                data.get('current_registration_date'),
                data.get('registration_expiry_date'),
                data.get('primary_qualification'),
                json.dumps(data.get('additional_qualifications', [])),
                data.get('practice_type'),
                data.get('practice_name'),
                json.dumps(data.get('hospital_affiliations', [])),
                'PENDING',
                session.get('username', 'SYSTEM'),
                json.dumps(data.get('metadata', {})),
                data.get('notes')
            ))
            
            professional_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                'success': True,
                'professional_id': professional_id,
                'message': 'Healthcare professional created successfully'
            }), 201
            
    except Exception as e:
        logger.error(f"Error creating healthcare professional: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

@sa_rest_api.route('/professionals/<int:professional_id>', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_healthcare_professional(professional_id):
    """Get specific healthcare professional by ID"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM vw_active_healthcare_professionals 
                WHERE id = ? AND is_active = 1 AND is_deleted = 0
            """, (professional_id,))
            
            professional = cursor.fetchone()
            if not professional:
                return jsonify({'error': 'Healthcare professional not found', 'error_code': 1007}), 404
            
            return jsonify({
                'success': True,
                'professional': dict(professional)
            })
            
    except Exception as e:
        logger.error(f"Error getting healthcare professional: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

@sa_rest_api.route('/professionals/<int:professional_id>', methods=['PUT'])
@cross_origin(supports_credentials=True)
@require_auth
@require_role(['ADMINISTRATOR', 'MANAGER'])
def update_healthcare_professional(professional_id):
    """Update healthcare professional"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data required', 'error_code': 1003}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if professional exists
            cursor.execute("SELECT id FROM sa_healthcare_professionals WHERE id = ? AND is_active = 1 AND is_deleted = 0", 
                         (professional_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Healthcare professional not found', 'error_code': 1007}), 404
            
            # Build update query dynamically
            update_fields = []
            params = []
            
            updatable_fields = [
                'first_name', 'last_name', 'middle_names', 'email', 'phone_primary', 'phone_secondary',
                'registration_status', 'specialization', 'sub_specialization', 'practice_city',
                'practice_address', 'practice_postal_code', 'current_registration_date',
                'registration_expiry_date', 'primary_qualification', 'practice_type', 'practice_name',
                'notes'
            ]
            
            for field in updatable_fields:
                if field in data:
                    update_fields.append(f"{field} = ?")
                    params.append(data[field])
            
            # Handle JSON fields
            if 'additional_qualifications' in data:
                update_fields.append("additional_qualifications = ?")
                params.append(json.dumps(data['additional_qualifications']))
            
            if 'hospital_affiliations' in data:
                update_fields.append("hospital_affiliations = ?")
                params.append(json.dumps(data['hospital_affiliations']))
            
            if 'metadata' in data:
                update_fields.append("metadata = ?")
                params.append(json.dumps(data['metadata']))
            
            if not update_fields:
                return jsonify({'error': 'No valid fields to update', 'error_code': 1003}), 400
            
            # Add updated_by and updated_at
            update_fields.extend(["updated_by = ?", "updated_at = ?"])
            params.extend([session.get('username', 'SYSTEM'), datetime.now().isoformat()])
            params.append(professional_id)
            
            query = f"UPDATE sa_healthcare_professionals SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Healthcare professional updated successfully'
            })
            
    except Exception as e:
        logger.error(f"Error updating healthcare professional: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

# ===== PATIENT MEDICAL AID INFORMATION ENDPOINTS =====

@sa_rest_api.route('/patients/<patient_id>/medical-aid', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_patient_medical_aid_info(patient_id):
    """Get patient's medical aid information"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get patient medical aid info
            cursor.execute("""
                SELECT 
                    p.patient_id,
                    p.medical_scheme_code,
                    p.medical_scheme_number,
                    p.medical_aid_status,
                    p.medical_aid_plan,
                    p.medical_aid_effective_date,
                    p.medical_aid_expiry_date,
                    p.medical_aid_dependents,
                    p.medical_aid_benefits,
                    p.medical_aid_last_verified
                FROM sa_patients p
                WHERE p.patient_id = ? AND p.is_active = 1 AND p.is_deleted = 0
            """, (patient_id,))
            
            patient = cursor.fetchone()
            if not patient:
                return jsonify({'error': 'Patient not found', 'error_code': 1007}), 404
            
            medical_aid_info = dict(patient)
            
            # If patient has medical aid, get additional scheme information
            if medical_aid_info['medical_scheme_code']:
                # This would typically call the medical aid validation service
                # For now, return the stored information
                pass
            
            return jsonify({
                'success': True,
                'patient_id': patient_id,
                'medical_aid_info': medical_aid_info
            })
            
    except Exception as e:
        logger.error(f"Error getting patient medical aid info: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

@sa_rest_api.route('/patients/<patient_id>/medical-aid', methods=['PUT'])
@cross_origin(supports_credentials=True)
@require_auth
@require_role(['ADMINISTRATOR', 'MANAGER', 'DOCTOR', 'NURSE'])
def update_patient_medical_aid_info(patient_id):
    """Update patient's medical aid information"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data required', 'error_code': 1003}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if patient exists
            cursor.execute("SELECT id FROM sa_patients WHERE patient_id = ? AND is_active = 1 AND is_deleted = 0", 
                         (patient_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Patient not found', 'error_code': 1007}), 404
            
            # Update medical aid information
            cursor.execute("""
                UPDATE sa_patients SET
                    medical_scheme_code = ?,
                    medical_scheme_number = ?,
                    medical_aid_status = ?,
                    medical_aid_plan = ?,
                    medical_aid_effective_date = ?,
                    medical_aid_expiry_date = ?,
                    medical_aid_dependents = ?,
                    medical_aid_benefits = ?,
                    medical_aid_last_verified = ?,
                    updated_at = ?,
                    updated_by = ?
                WHERE patient_id = ?
            """, (
                data.get('medical_scheme_code'),
                data.get('medical_scheme_number'),
                data.get('medical_aid_status'),
                data.get('medical_aid_plan'),
                data.get('medical_aid_effective_date'),
                data.get('medical_aid_expiry_date'),
                data.get('medical_aid_dependents'),
                json.dumps(data.get('medical_aid_benefits', {})),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                session.get('username', 'SYSTEM'),
                patient_id
            ))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Patient medical aid information updated successfully'
            })
            
    except Exception as e:
        logger.error(f"Error updating patient medical aid info: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

# ===== COMPLIANCE REPORTING ENDPOINTS =====

@sa_rest_api.route('/compliance/report', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
@require_role(['ADMINISTRATOR', 'MANAGER', 'COMPLIANCE_OFFICER'])
def get_compliance_report():
    """Generate comprehensive compliance report"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('type', 'summary')  # summary, detailed, hpcsa, popia
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            report = {
                'report_type': report_type,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'generated_at': datetime.now().isoformat(),
                'generated_by': session.get('username', 'SYSTEM')
            }
            
            if report_type in ['summary', 'hpcsa']:
                # HPCSA Compliance Statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_professionals,
                        SUM(CASE WHEN hpcsa_validation_status = 'VALIDATED' THEN 1 ELSE 0 END) as validated_professionals,
                        SUM(CASE WHEN hpcsa_validation_status = 'PENDING' THEN 1 ELSE 0 END) as pending_validation,
                        SUM(CASE WHEN hpcsa_validation_status = 'FAILED' THEN 1 ELSE 0 END) as failed_validation,
                        SUM(CASE WHEN registration_status = 'ACTIVE' THEN 1 ELSE 0 END) as active_professionals
                    FROM sa_healthcare_professionals
                    WHERE is_active = 1 AND is_deleted = 0
                """)
                
                hpcsa_stats = dict(cursor.fetchone())
                hpcsa_stats['compliance_rate'] = (
                    (hpcsa_stats['validated_professionals'] / hpcsa_stats['total_professionals']) * 100
                    if hpcsa_stats['total_professionals'] > 0 else 0
                )
                
                report['hpcsa_compliance'] = hpcsa_stats
            
            if report_type in ['summary', 'popia']:
                # POPIA Compliance Statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_patients,
                        SUM(CASE WHEN popia_consent_given = 1 THEN 1 ELSE 0 END) as patients_with_consent,
                        COUNT(DISTINCT CASE WHEN popia_consent_date >= ? THEN patient_id END) as new_consents_period
                    FROM sa_patients
                    WHERE is_active = 1 AND is_deleted = 0
                """, (start_date,))
                
                popia_stats = dict(cursor.fetchone())
                popia_stats['consent_rate'] = (
                    (popia_stats['patients_with_consent'] / popia_stats['total_patients']) * 100
                    if popia_stats['total_patients'] > 0 else 0
                )
                
                report['popia_compliance'] = popia_stats
            
            if report_type in ['summary', 'detailed']:
                # Audit Log Statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_events,
                        COUNT(DISTINCT user_id) as unique_users,
                        SUM(CASE WHEN severity_level = 'ERROR' THEN 1 ELSE 0 END) as error_events,
                        SUM(CASE WHEN severity_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical_events,
                        SUM(CASE WHEN contains_phi = 1 THEN 1 ELSE 0 END) as phi_access_events,
                        SUM(CASE WHEN contains_pii = 1 THEN 1 ELSE 0 END) as pii_access_events
                    FROM sa_audit_log
                    WHERE event_date BETWEEN ? AND ?
                """, (start_date, end_date))
                
                audit_stats = dict(cursor.fetchone())
                report['audit_statistics'] = audit_stats
            
            if report_type == 'detailed':
                # Top accessed resources
                cursor.execute("""
                    SELECT resource_type, COUNT(*) as access_count
                    FROM sa_audit_log
                    WHERE event_date BETWEEN ? AND ?
                    GROUP BY resource_type
                    ORDER BY access_count DESC
                    LIMIT 10
                """, (start_date, end_date))
                
                report['top_accessed_resources'] = [dict(row) for row in cursor.fetchall()]
                
                # Most active users
                cursor.execute("""
                    SELECT username, COUNT(*) as activity_count
                    FROM sa_audit_log
                    WHERE event_date BETWEEN ? AND ? AND username IS NOT NULL
                    GROUP BY username
                    ORDER BY activity_count DESC
                    LIMIT 10
                """, (start_date, end_date))
                
                report['most_active_users'] = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'success': True,
                'compliance_report': report
            })
            
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

@sa_rest_api.route('/compliance/violations', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
@require_role(['ADMINISTRATOR', 'MANAGER', 'COMPLIANCE_OFFICER'])
def get_compliance_violations():
    """Get compliance violations and alerts"""
    try:
        # Get query parameters
        severity = request.args.get('severity', 'all')  # all, high, medium, low
        violation_type = request.args.get('type', 'all')  # all, hpcsa, popia, security
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        offset = (page - 1) * per_page
        
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query for violations
            where_conditions = ["severity_level IN ('ERROR', 'CRITICAL')"]
            params = []
            
            if severity != 'all':
                if severity == 'high':
                    where_conditions.append("severity_level = 'CRITICAL'")
                elif severity == 'medium':
                    where_conditions.append("severity_level = 'ERROR'")
                elif severity == 'low':
                    where_conditions.append("severity_level = 'WARN'")
            
            if violation_type != 'all':
                if violation_type == 'hpcsa':
                    where_conditions.append("category_code LIKE 'HPCSA_%'")
                elif violation_type == 'popia':
                    where_conditions.append("category_code LIKE 'POPIA_%'")
                elif violation_type == 'security':
                    where_conditions.append("category_code LIKE 'SECURITY_%'")
            
            # Get total count
            count_query = f"""
                SELECT COUNT(*) FROM sa_audit_log
                WHERE {' AND '.join(where_conditions)}
            """
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Get violations
            query = f"""
                SELECT 
                    id, audit_uuid, category_code, event_type, action,
                    username, user_role, severity_level, description,
                    event_timestamp, ip_address, resource_type, resource_id
                FROM sa_audit_log
                WHERE {' AND '.join(where_conditions)}
                ORDER BY event_timestamp DESC
                LIMIT ? OFFSET ?
            """
            params.extend([per_page, offset])
            
            cursor.execute(query, params)
            violations = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'success': True,
                'violations': violations,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                },
                'filters': {
                    'severity': severity,
                    'type': violation_type
                }
            })
            
    except Exception as e:
        logger.error(f"Error getting compliance violations: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

# ===== SYSTEM STATISTICS AND MONITORING ENDPOINTS =====

@sa_rest_api.route('/statistics/dashboard', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_dashboard_statistics():
    """Get dashboard statistics for SA healthcare system"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get current date for time-based queries
            today = datetime.now().strftime('%Y-%m-%d')
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            dashboard_stats = {}
            
            # Healthcare Professionals Statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN hpcsa_validation_status = 'VALIDATED' THEN 1 ELSE 0 END) as validated,
                    SUM(CASE WHEN registration_status = 'ACTIVE' THEN 1 ELSE 0 END) as active,
                    COUNT(DISTINCT registration_category) as categories,
                    COUNT(DISTINCT province_code) as provinces
                FROM sa_healthcare_professionals
                WHERE is_active = 1 AND is_deleted = 0
            """)
            dashboard_stats['healthcare_professionals'] = dict(cursor.fetchone())
            
            # Patient Statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN popia_consent_given = 1 THEN 1 ELSE 0 END) as with_consent,
                    SUM(CASE WHEN medical_scheme_code IS NOT NULL THEN 1 ELSE 0 END) as with_medical_aid,
                    COUNT(DISTINCT preferred_language) as languages
                FROM sa_patients
                WHERE is_active = 1 AND is_deleted = 0
            """)
            dashboard_stats['patients'] = dict(cursor.fetchone())
            
            # Recent Activity (last 7 days)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT username) as active_users,
                    SUM(CASE WHEN severity_level IN ('ERROR', 'CRITICAL') THEN 1 ELSE 0 END) as alerts,
                    SUM(CASE WHEN contains_phi = 1 THEN 1 ELSE 0 END) as phi_access
                FROM sa_audit_log
                WHERE event_date >= ?
            """, (week_ago,))
            dashboard_stats['recent_activity'] = dict(cursor.fetchone())
            
            # System Health Indicators
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN category_code LIKE 'SECURITY_%' THEN 1 ELSE 0 END) as security_events,
                    SUM(CASE WHEN category_code LIKE 'POPIA_%' THEN 1 ELSE 0 END) as privacy_events,
                    SUM(CASE WHEN category_code LIKE 'HPCSA_%' THEN 1 ELSE 0 END) as compliance_events
                FROM sa_audit_log
                WHERE event_date >= ?
            """, (month_ago,))
            dashboard_stats['system_health'] = dict(cursor.fetchone())
            
            # Top Categories by Activity
            cursor.execute("""
                SELECT registration_category, COUNT(*) as count
                FROM sa_healthcare_professionals
                WHERE is_active = 1 AND is_deleted = 0
                GROUP BY registration_category
                ORDER BY count DESC
                LIMIT 5
            """)
            dashboard_stats['top_professional_categories'] = [dict(row) for row in cursor.fetchall()]
            
            # Recent Registrations (last 30 days)
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM sa_healthcare_professionals
                WHERE created_at >= ? AND is_active = 1 AND is_deleted = 0
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """, (month_ago,))
            dashboard_stats['recent_registrations'] = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'success': True,
                'dashboard_statistics': dashboard_stats,
                'generated_at': datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error getting dashboard statistics: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

# ===== SEARCH AND DISCOVERY ENDPOINTS =====

@sa_rest_api.route('/search', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def global_search():
    """Global search across SA healthcare entities"""
    try:
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')  # all, professionals, patients, studies
        limit = min(int(request.args.get('limit', 20)), 100)
        
        if not query or len(query) < 2:
            return jsonify({'error': 'Search query must be at least 2 characters', 'error_code': 1003}), 400
        
        results = {
            'query': query,
            'search_type': search_type,
            'results': {}
        }
        
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if search_type in ['all', 'professionals']:
                # Search healthcare professionals
                cursor.execute("""
                    SELECT id, hpcsa_number, first_name, last_name, registration_category, 
                           specialization, province_code, 'professional' as result_type
                    FROM sa_healthcare_professionals
                    WHERE (first_name LIKE ? OR last_name LIKE ? OR hpcsa_number LIKE ?)
                      AND is_active = 1 AND is_deleted = 0
                    ORDER BY last_name, first_name
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                
                results['results']['professionals'] = [dict(row) for row in cursor.fetchall()]
            
            if search_type in ['all', 'patients']:
                # Search patients (limited fields for privacy)
                cursor.execute("""
                    SELECT patient_id, first_name, last_name, medical_scheme_code, 
                           'patient' as result_type
                    FROM sa_patients
                    WHERE (first_name LIKE ? OR last_name LIKE ? OR patient_id LIKE ?)
                      AND is_active = 1 AND is_deleted = 0
                    ORDER BY last_name, first_name
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                
                results['results']['patients'] = [dict(row) for row in cursor.fetchall()]
            
            # Calculate total results
            total_results = sum(len(result_list) for result_list in results['results'].values())
            results['total_results'] = total_results
            
            return jsonify({
                'success': True,
                'search_results': results
            })
            
    except Exception as e:
        logger.error(f"Error performing global search: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

# Blueprint is ready to be imported and registered