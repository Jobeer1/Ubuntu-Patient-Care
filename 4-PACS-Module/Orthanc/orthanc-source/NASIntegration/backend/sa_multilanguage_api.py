#!/usr/bin/env python3
"""
🌍 SA Multi-Language Support API
Support for all 11 official South African languages in medical interfaces
"""

from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint
sa_multilanguage_api = Blueprint('sa_multilanguage_api', __name__, url_prefix='/api/sa/language')

# South African Official Languages
SA_LANGUAGES = {
    'en': {'name': 'English', 'native': 'English', 'rtl': False},
    'af': {'name': 'Afrikaans', 'native': 'Afrikaans', 'rtl': False},
    'zu': {'name': 'Zulu', 'native': 'isiZulu', 'rtl': False},
    'xh': {'name': 'Xhosa', 'native': 'isiXhosa', 'rtl': False},
    'st': {'name': 'Sotho', 'native': 'Sesotho', 'rtl': False},
    'tn': {'name': 'Tswana', 'native': 'Setswana', 'rtl': False},
    'ss': {'name': 'Swati', 'native': 'siSwati', 'rtl': False},
    've': {'name': 'Venda', 'native': 'Tshivenḓa', 'rtl': False},
    'ts': {'name': 'Tsonga', 'native': 'Xitsonga', 'rtl': False},
    'nr': {'name': 'Ndebele', 'native': 'isiNdebele', 'rtl': False},
    'nso': {'name': 'Northern Sotho', 'native': 'Sepedi', 'rtl': False}
}

# Medical terminology translations (basic set)
MEDICAL_TRANSLATIONS = {
    'en': {
        'patient': 'Patient',
        'doctor': 'Doctor',
        'nurse': 'Nurse',
        'hospital': 'Hospital',
        'clinic': 'Clinic'
    },
    'af': {
        'patient': 'Pasiënt',
        'doctor': 'Dokter',
        'nurse': 'Verpleegster',
        'hospital': 'Hospitaal',
        'clinic': 'Kliniek'
    },
    'zu': {
        'patient': 'Isiguli',
        'doctor': 'Udokotela',
        'nurse': 'Umuhlengikazi',
        'hospital': 'Isibhedlela',
        'clinic': 'Umtholampilo'
    }
}

# UI translations (basic set)
UI_TRANSLATIONS = {
    'en': {
        'login': 'Login',
        'logout': 'Logout',
        'save': 'Save',
        'cancel': 'Cancel',
        'search': 'Search'
    },
    'af': {
        'login': 'Meld aan',
        'logout': 'Meld af',
        'save': 'Stoor',
        'cancel': 'Kanselleer',
        'search': 'Soek'
    },
    'zu': {
        'login': 'Ngena',
        'logout': 'Phuma',
        'save': 'Londoloza',
        'cancel': 'Khansela',
        'search': 'Sesha'
    }
}

def require_auth():
    """Simple authentication check"""
    if not session.get('user_id'):
        return jsonify({'error': 'Authentication required', 'error_code': 1004}), 401
    return None

def get_user_language():
    """Get user's preferred language"""
    return session.get('language', 'en')

def set_user_language(language_code):
    """Set user's preferred language"""
    if language_code in SA_LANGUAGES:
        session['language'] = language_code
        return True
    return False

# ===== REST API ENDPOINTS =====

@sa_multilanguage_api.route('/languages', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_supported_languages():
    """Get list of supported SA languages"""
    try:
        languages = []
        for code, info in SA_LANGUAGES.items():
            languages.append({
                'code': code,
                'name': info['name'],
                'native_name': info['native'],
                'rtl': info['rtl']
            })
        
        return jsonify({
            'success': True,
            'languages': languages,
            'total': len(languages),
            'current_language': get_user_language()
        })
        
    except Exception as e:
        logger.error(f"Error getting languages: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

@sa_multilanguage_api.route('/set', methods=['POST'])
@cross_origin(supports_credentials=True)
def set_language():
    """Set user's preferred language"""
    try:
        auth_error = require_auth()
        if auth_error:
            return auth_error
        
        data = request.get_json()
        if not data or not data.get('language'):
            return jsonify({'error': 'Language code required', 'error_code': 1003}), 400
        
        language_code = data['language'].lower()
        
        if language_code not in SA_LANGUAGES:
            return jsonify({
                'error': f'Unsupported language: {language_code}',
                'error_code': 1003,
                'supported_languages': list(SA_LANGUAGES.keys())
            }), 400
        
        set_user_language(language_code)
        
        return jsonify({
            'success': True,
            'language': language_code,
            'language_name': SA_LANGUAGES[language_code]['name'],
            'native_name': SA_LANGUAGES[language_code]['native'],
            'message': f'Language set to {SA_LANGUAGES[language_code]["name"]}'
        })
        
    except Exception as e:
        logger.error(f"Error setting language: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

@sa_multilanguage_api.route('/translate/medical', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_medical_translations():
    """Get medical terminology translations"""
    try:
        language = request.args.get('language', get_user_language())
        
        if language not in MEDICAL_TRANSLATIONS:
            language = 'en'  # Fallback to English
        
        translations = MEDICAL_TRANSLATIONS.get(language, MEDICAL_TRANSLATIONS['en'])
        
        return jsonify({
            'success': True,
            'language': language,
            'language_name': SA_LANGUAGES[language]['name'],
            'translations': translations,
            'total_terms': len(translations)
        })
        
    except Exception as e:
        logger.error(f"Error getting medical translations: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

@sa_multilanguage_api.route('/translate/ui', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_ui_translations():
    """Get UI element translations"""
    try:
        language = request.args.get('language', get_user_language())
        
        if language not in UI_TRANSLATIONS:
            language = 'en'  # Fallback to English
        
        translations = UI_TRANSLATIONS.get(language, UI_TRANSLATIONS['en'])
        
        return jsonify({
            'success': True,
            'language': language,
            'language_name': SA_LANGUAGES[language]['name'],
            'translations': translations,
            'total_terms': len(translations)
        })
        
    except Exception as e:
        logger.error(f"Error getting UI translations: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

@sa_multilanguage_api.route('/translate/batch', methods=['POST'])
@cross_origin(supports_credentials=True)
def translate_batch():
    """Translate multiple terms at once"""
    try:
        data = request.get_json()
        if not data or not data.get('terms'):
            return jsonify({'error': 'Terms array required', 'error_code': 1003}), 400
        
        terms = data['terms']
        target_language = data.get('language', get_user_language())
        category = data.get('category', 'medical')
        
        # Select translation dictionary
        if category == 'ui':
            translations_dict = UI_TRANSLATIONS
        else:
            translations_dict = MEDICAL_TRANSLATIONS
        
        # Get target language translations
        target_translations = translations_dict.get(target_language, {})
        english_translations = translations_dict.get('en', {})
        
        # Translate all terms
        translated_terms = {}
        for term in terms:
            term_lower = term.lower()
            translated = target_translations.get(term_lower) or english_translations.get(term_lower) or term
            translated_terms[term] = translated
        
        return jsonify({
            'success': True,
            'language': target_language,
            'language_name': SA_LANGUAGES.get(target_language, {}).get('name', target_language),
            'category': category,
            'translations': translated_terms,
            'total_terms': len(translated_terms)
        })
        
    except Exception as e:
        logger.error(f"Error batch translating: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500

@sa_multilanguage_api.route('/current', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_current_language():
    """Get current user language"""
    try:
        current_lang = get_user_language()
        
        return jsonify({
            'success': True,
            'language': current_lang,
            'language_name': SA_LANGUAGES[current_lang]['name'],
            'native_name': SA_LANGUAGES[current_lang]['native'],
            'rtl': SA_LANGUAGES[current_lang]['rtl']
        })
        
    except Exception as e:
        logger.error(f"Error getting current language: {e}")
        return jsonify({'error': 'Internal server error', 'error_code': 1003}), 500