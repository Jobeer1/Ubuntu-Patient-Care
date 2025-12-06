"""Medical Standards API for terminology and templates"""

from flask import Blueprint, jsonify, request
from datetime import datetime

medical_bp = Blueprint('medical', __name__)

@medical_bp.route('/terminology/search', methods=['GET'])
def search_terminology():
    """Search medical terminology"""
    try:
        query = request.args.get('q', '')
        category = request.args.get('category', 'all')
        
        # Sample medical terms for South African context
        terms = [
            {'id': 1, 'term': 'hypertension', 'category': 'cardiovascular', 'definition': 'High blood pressure'},
            {'id': 2, 'term': 'diabetes mellitus', 'category': 'endocrine', 'definition': 'Diabetes'},
            {'id': 3, 'term': 'pneumonia', 'category': 'respiratory', 'definition': 'Lung infection'},
            {'id': 4, 'term': 'tuberculosis', 'category': 'infectious', 'definition': 'TB infection'},
            {'id': 5, 'term': 'malaria', 'category': 'infectious', 'definition': 'Parasitic infection'}
        ]
        
        # Filter by query and category
        filtered_terms = []
        for term in terms:
            if query.lower() in term['term'].lower():
                if category == 'all' or term['category'] == category:
                    filtered_terms.append(term)
        
        return jsonify({
            'success': True,
            'data': {
                'terms': filtered_terms,
                'total': len(filtered_terms),
                'query': query,
                'category': category
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@medical_bp.route('/templates', methods=['GET'])
def get_templates():
    """Get medical report templates"""
    try:
        template_type = request.args.get('type', 'all')
        
        templates = {
            'consultation': {
                'id': 'consultation',
                'name': 'Consultation Note',
                'content': 'CONSULTATION NOTE\n\nDate: [Date]\nPatient: [Patient Name]\n\nCHIEF COMPLAINT:\n\nHISTORY OF PRESENT ILLNESS:\n\nPHYSICAL EXAMINATION:\n- Vital signs:\n- General appearance:\n- Systems review:\n\nASSESSMENT AND PLAN:\n\nDr. [Name]'
            },
            'discharge': {
                'id': 'discharge',
                'name': 'Discharge Summary',
                'content': 'DISCHARGE SUMMARY\n\nPatient: [Patient Name]\nAdmission Date: [Date]\nDischarge Date: [Date]\n\nDIAGNOSES:\n1. Primary:\n2. Secondary:\n\nHOSPITAL COURSE:\n\nDISCHARGE MEDICATIONS:\n\nFOLLOW-UP INSTRUCTIONS:\n\nDr. [Name]'
            },
            'referral': {
                'id': 'referral',
                'name': 'Referral Letter',
                'content': 'REFERRAL LETTER\n\nDate: [Date]\nTo: [Specialist/Department]\nRe: [Patient Name]\n\nDear Colleague,\n\nI am referring the above patient for your expert opinion and management.\n\nHISTORY:\n\nEXAMINATION FINDINGS:\n\nREASON FOR REFERRAL:\n\nThank you for your assistance.\n\nYours sincerely,\nDr. [Name]'
            }
        }
        
        if template_type != 'all' and template_type in templates:
            result = {template_type: templates[template_type]}
        else:
            result = templates
            
        return jsonify({
            'success': True,
            'data': {
                'templates': result,
                'total': len(result)
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@medical_bp.route('/validate', methods=['POST'])
def validate_content():
    """Validate medical content"""
    try:
        data = request.get_json() or {}
        content = data.get('content', '')
        
        # Basic validation (can be enhanced)
        validation_result = {
            'valid': True,
            'warnings': [],
            'suggestions': []
        }
        
        if len(content) < 10:
            validation_result['warnings'].append('Content seems too short')
            
        return jsonify({
            'success': True,
            'data': validation_result,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500