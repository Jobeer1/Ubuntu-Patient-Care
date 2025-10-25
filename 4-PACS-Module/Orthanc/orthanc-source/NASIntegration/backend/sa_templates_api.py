#!/usr/bin/env python3
"""
🇿🇦 SA Medical Templates API Endpoints

REST API endpoints for South African medical templates, terminology, and compliance.
"""

from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
import logging
from datetime import datetime
from typing import Dict, Any

try:
    from .sa_medical_templates import sa_template_engine
    from .auth_2fa import require_auth
except ImportError:
    # Fallback to absolute imports
    from sa_medical_templates import sa_template_engine
    try:
        from auth_2fa import require_auth
    except ImportError:
        # Simple auth fallback
        def require_auth(f):
            def wrapper(*args, **kwargs):
                if not session.get('user_id'):
                    return jsonify({'error': 'Authentication required'}), 401
                return f(*args, **kwargs)
            return wrapper

logger = logging.getLogger(__name__)

# Create blueprint for SA templates endpoints
sa_templates_api_bp = Blueprint('sa_templates_api', __name__, url_prefix='/api/reporting/sa-templates')

# ============================================================================
# TEMPLATE MANAGEMENT ENDPOINTS
# ============================================================================

@sa_templates_api_bp.route('/templates', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_templates():
    """Get SA medical templates with filtering"""
    try:
        modality = request.args.get('modality', '')
        body_part = request.args.get('body_part', '')
        language = request.args.get('language', 'en')
        category = request.args.get('category', '')
        
        if not modality:
            return jsonify({
                'success': False,
                'error': 'Modality parameter is required'
            }), 400
        
        templates = sa_template_engine.get_templates_by_modality(
            modality=modality,
            body_part=body_part,
            language=language,
            category=category
        )
        
        return jsonify({
            'success': True,
            'templates': [template.to_dict() for template in templates],
            'count': len(templates),
            'filters': {
                'modality': modality,
                'body_part': body_part,
                'language': language,
                'category': category
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting templates: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_templates_api_bp.route('/templates/<template_id>', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_template(template_id: str):
    """Get specific template by ID"""
    try:
        language = request.args.get('language', 'en')
        
        template = sa_template_engine.get_template_by_id(template_id, language)
        
        if not template:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404
        
        return jsonify({
            'success': True,
            'template': template.to_dict()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_templates_api_bp.route('/templates', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def create_template():
    """Create new SA medical template"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Template data required'
            }), 400
        
        # Validate required fields
        required_fields = ['name_en', 'modality', 'body_part', 'structure']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        success, result = sa_template_engine.create_template(data, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'template_id': result,
                'message': 'Template created successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': result
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Error creating template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_templates_api_bp.route('/templates/<template_id>/populate', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def populate_template(template_id: str):
    """Populate template with data"""
    try:
        data = request.get_json() or {}
        language = data.get('language', 'en')
        report_data = data.get('data', {})
        
        populated = sa_template_engine.populate_template(template_id, report_data, language)
        
        if 'error' in populated:
            return jsonify({
                'success': False,
                'error': populated['error']
            }), 400
        
        return jsonify({
            'success': True,
            'populated_template': populated
        })
        
    except Exception as e:
        logger.error(f"❌ Error populating template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_templates_api_bp.route('/templates/<template_id>/validate', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def validate_template_compliance(template_id: str):
    """Validate template compliance with SA standards"""
    try:
        data = request.get_json() or {}
        report_data = data.get('report_data', {})
        
        validation_result = sa_template_engine.validate_template_compliance(template_id, report_data)
        
        return jsonify({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        logger.error(f"❌ Error validating template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# MEDICAL TERMINOLOGY ENDPOINTS
# ============================================================================

@sa_templates_api_bp.route('/terminology', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_medical_terminology():
    """Get SA medical terminology"""
    try:
        language = request.args.get('language', 'en')
        category = request.args.get('category', '')
        modality = request.args.get('modality', '')
        search = request.args.get('search', '')
        limit = request.args.get('limit', 50, type=int)
        
        terms = sa_template_engine.get_medical_terms(
            language=language,
            category=category,
            modality=modality,
            search=search
        )
        
        # Limit results
        if limit > 0:
            terms = terms[:limit]
        
        return jsonify({
            'success': True,
            'terms': [term.to_dict() for term in terms],
            'count': len(terms),
            'filters': {
                'language': language,
                'category': category,
                'modality': modality,
                'search': search
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting terminology: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_templates_api_bp.route('/terminology/translate', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def translate_medical_term():
    """Translate medical term between languages"""
    try:
        data = request.get_json()
        
        if not data or 'term' not in data:
            return jsonify({
                'success': False,
                'error': 'Term is required'
            }), 400
        
        term = data['term']
        from_lang = data.get('from_language', 'en')
        to_lang = data.get('to_language', 'af')
        
        translated = sa_template_engine.translate_medical_term(term, from_lang, to_lang)
        
        return jsonify({
            'success': True,
            'original_term': term,
            'translated_term': translated,
            'from_language': from_lang,
            'to_language': to_lang,
            'found': translated is not None
        })
        
    except Exception as e:
        logger.error(f"❌ Error translating term: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_templates_api_bp.route('/terminology/suggestions', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_terminology_suggestions():
    """Get medical terminology suggestions for auto-complete"""
    try:
        term = request.args.get('term', '')
        language = request.args.get('language', 'en')
        category = request.args.get('category', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not term or len(term) < 2:
            return jsonify({
                'success': True,
                'suggestions': [],
                'count': 0
            })
        
        # Get matching terms
        terms = sa_template_engine.get_medical_terms(
            language=language,
            category=category,
            search=term
        )
        
        # Format suggestions
        suggestions = []
        for medical_term in terms[:limit]:
            if language == 'en':
                suggestion = medical_term.english_term
            elif language == 'af':
                suggestion = medical_term.afrikaans_term or medical_term.english_term
            elif language == 'zu':
                suggestion = medical_term.isizulu_term or medical_term.english_term
            else:
                suggestion = medical_term.english_term
            
            if suggestion and term.lower() in suggestion.lower():
                suggestions.append({
                    'term': suggestion,
                    'category': medical_term.category,
                    'confidence': medical_term.confidence,
                    'synonyms': medical_term.synonyms,
                    'abbreviations': medical_term.abbreviations
                })
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'count': len(suggestions),
            'query': term
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting suggestions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# ANALYTICS AND USAGE ENDPOINTS
# ============================================================================

@sa_templates_api_bp.route('/analytics/usage', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_template_usage_analytics():
    """Get template usage analytics"""
    try:
        template_id = request.args.get('template_id', '')
        user_id = request.args.get('user_id', '')
        
        analytics = sa_template_engine.get_template_analytics(template_id, user_id)
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_templates_api_bp.route('/analytics/record-usage', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def record_template_usage():
    """Record template usage for analytics"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data or 'template_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Template ID is required'
            }), 400
        
        success = sa_template_engine.record_template_usage(
            template_id=data['template_id'],
            user_id=user_id,
            session_id=data.get('session_id', ''),
            language=data.get('language', 'en'),
            completion_data=data.get('completion_data', {})
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Usage recorded successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to record usage'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error recording usage: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# SYSTEM INFORMATION ENDPOINTS
# ============================================================================

@sa_templates_api_bp.route('/system/languages', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_supported_languages():
    """Get supported languages"""
    return jsonify({
        'success': True,
        'languages': [
            {
                'code': 'en',
                'name': 'English',
                'native_name': 'English',
                'flag': '🇬🇧'
            },
            {
                'code': 'af',
                'name': 'Afrikaans',
                'native_name': 'Afrikaans',
                'flag': '🇿🇦'
            },
            {
                'code': 'zu',
                'name': 'isiZulu',
                'native_name': 'isiZulu',
                'flag': '🇿🇦'
            }
        ]
    })

@sa_templates_api_bp.route('/system/categories', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_template_categories():
    """Get available template categories"""
    return jsonify({
        'success': True,
        'categories': [
            {
                'id': 'screening',
                'name': 'Screening',
                'description': 'Templates for screening examinations (TB, cardiac, etc.)',
                'icon': '🔍'
            },
            {
                'id': 'diagnostic',
                'name': 'Diagnostic',
                'description': 'Templates for diagnostic examinations',
                'icon': '🔬'
            },
            {
                'id': 'follow_up',
                'name': 'Follow-up',
                'description': 'Templates for follow-up examinations',
                'icon': '📋'
            },
            {
                'id': 'emergency',
                'name': 'Emergency',
                'description': 'Templates for emergency examinations',
                'icon': '🚨'
            }
        ]
    })

@sa_templates_api_bp.route('/system/modalities', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_supported_modalities():
    """Get supported modalities"""
    return jsonify({
        'success': True,
        'modalities': [
            {'code': 'CR', 'name': 'Computed Radiography', 'icon': '📷'},
            {'code': 'DX', 'name': 'Digital Radiography', 'icon': '📷'},
            {'code': 'CT', 'name': 'Computed Tomography', 'icon': '🔄'},
            {'code': 'MR', 'name': 'Magnetic Resonance', 'icon': '🧲'},
            {'code': 'US', 'name': 'Ultrasound', 'icon': '📡'},
            {'code': 'NM', 'name': 'Nuclear Medicine', 'icon': '☢️'},
            {'code': 'PT', 'name': 'Positron Emission Tomography', 'icon': '🔬'},
            {'code': 'MG', 'name': 'Mammography', 'icon': '🎯'}
        ]
    })

@sa_templates_api_bp.route('/system/status', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_system_status():
    """Get SA templates system status"""
    try:
        # Get basic statistics
        all_templates = sa_template_engine.get_templates_by_modality('CR')  # Sample query
        analytics = sa_template_engine.get_template_analytics()
        
        return jsonify({
            'success': True,
            'system_status': {
                'templates_available': len(all_templates),
                'total_usage': analytics.get('total_usage', 0),
                'languages_supported': 3,
                'sa_specific_features': True,
                'compliance_checking': True,
                'last_updated': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting system status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500