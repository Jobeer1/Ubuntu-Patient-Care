#!/usr/bin/env python3
"""
Medical STT Enhancer - Integrates training data with STT processing
"""

import logging
import json
from datetime import datetime
from models.training_data import TrainingDataStore
from models.voice_shortcuts import VoiceShortcutStore

logger = logging.getLogger(__name__)

class MedicalSTTEnhancer:
    """Enhanced STT processor with medical training integration"""
    
    def __init__(self, base_whisper_model):
        self.base_model = base_whisper_model
        self.medical_terms_db = self._load_medical_terms()
        
    def _load_medical_terms(self):
        """Load medical terms database"""
        try:
            from models.training_data import MedicalTerm
            terms = MedicalTerm.query.all()
            
            # Organize by category for faster lookup
            terms_db = {}
            for term in terms:
                if term.category not in terms_db:
                    terms_db[term.category] = []
                terms_db[term.category].append({
                    'term': term.term,
                    'variations': term.common_variations.split(',') if term.common_variations else [],
                    'difficulty': term.difficulty_level
                })
            
            logger.info(f"Loaded {len(terms)} medical terms from database")
            return terms_db
            
        except Exception as e:
            logger.error(f"Failed to load medical terms: {e}")
            return {}
    
    def enhance_transcription_with_training(self, transcription, user_id, user_training_data=None):
        """Apply user-specific training improvements to transcription"""
        if not transcription:
            return transcription
        
        try:
            # Get user's training data if not provided
            if not user_training_data:
                training_store = TrainingDataStore(user_id)
                user_training_data = training_store.get_user_training_progress()
            
            enhanced = transcription.lower()
            
            # Apply medical terminology corrections
            enhanced = self._apply_medical_corrections(enhanced)
            
            # Apply user-specific training corrections
            enhanced = self._apply_training_corrections(enhanced, user_id)
            
            # Apply South African medical context
            enhanced = self._apply_sa_medical_context(enhanced)
            
            # Capitalize appropriately
            enhanced = self._apply_capitalization(enhanced)
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Transcription enhancement failed: {e}")
            return transcription  # Return original on error
    
    def _apply_medical_corrections(self, text):
        """Apply general medical terminology corrections"""
        corrections = {
            # Common medical abbreviations
            'bp': 'blood pressure',
            'hr': 'heart rate',
            'rr': 'respiratory rate',
            'temp': 'temperature',
            'o2 sat': 'oxygen saturation',
            'ecg': 'ECG',
            'ekg': 'ECG',
            'cxr': 'chest X-ray',
            'ct': 'CT',
            'mri': 'MRI',
            
            # Medical conditions
            'mi': 'myocardial infarction',
            'copd': 'chronic obstructive pulmonary disease',
            'uti': 'urinary tract infection',
            'dvt': 'deep vein thrombosis',
            'pe': 'pulmonary embolism',
            
            # Anatomical terms
            'abd': 'abdomen',
            'cvs': 'cardiovascular system',
            'rs': 'respiratory system',
            'cns': 'central nervous system',
            'gi': 'gastrointestinal',
            'gu': 'genitourinary',
            
            # Procedures
            'echo': 'echocardiogram',
            'us': 'ultrasound',
            'xray': 'X-ray',
            'x ray': 'X-ray'
        }
        
        import re
        enhanced = text
        
        for abbrev, full_term in corrections.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            enhanced = re.sub(pattern, full_term, enhanced, flags=re.IGNORECASE)
        
        return enhanced
    
    def _apply_training_corrections(self, text, user_id):
        """Apply user-specific training corrections"""
        try:
            training_store = TrainingDataStore(user_id)
            problematic_terms = training_store.get_problematic_terms()
            
            enhanced = text
            
            # Apply corrections for terms the user has trained on
            for term_data in problematic_terms:
                term = term_data['term'].lower()
                
                # Simple fuzzy matching - in production, use more sophisticated methods
                words = enhanced.split()
                corrected_words = []
                
                for word in words:
                    # Check if word is similar to trained term
                    if self._is_similar(word, term):
                        corrected_words.append(term)
                    else:
                        corrected_words.append(word)
                
                enhanced = ' '.join(corrected_words)
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Training corrections failed: {e}")
            return text
    
    def _apply_sa_medical_context(self, text):
        """Apply South African medical context and terminology"""
        sa_corrections = {
            # SA-specific medical terms
            'clinic sister': 'clinic sister',
            'community health worker': 'community health worker',
            'traditional healer': 'traditional healer',
            'sangoma': 'traditional healer (sangoma)',
            'muti': 'traditional medicine (muti)',
            
            # SA medical facilities
            'district hospital': 'district hospital',
            'provincial hospital': 'provincial hospital',
            'academic hospital': 'academic hospital',
            'clinic': 'clinic',
            
            # SA medical conditions (common presentations)
            'tb': 'tuberculosis',
            'mva': 'motor vehicle accident',
            'gsw': 'gunshot wound',
            'assault': 'assault',
            
            # SA medical procedures
            'rapid test': 'rapid test',
            'hiv test': 'HIV test',
            'cd4 count': 'CD4 count',
            'viral load': 'viral load'
        }
        
        import re
        enhanced = text
        
        for sa_term, replacement in sa_corrections.items():
            pattern = r'\b' + re.escape(sa_term) + r'\b'
            enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
        
        return enhanced
    
    def _apply_capitalization(self, text):
        """Apply proper capitalization for medical text"""
        import re
        
        # Capitalize first letter of sentences
        enhanced = re.sub(r'(^|[.!?]\s+)([a-z])', 
                         lambda m: m.group(1) + m.group(2).upper(), text)
        
        # Capitalize specific medical terms that should always be capitalized
        capitalize_terms = [
            'HIV', 'AIDS', 'TB', 'ECG', 'EKG', 'CT', 'MRI', 'X-ray', 'COPD',
            'ICU', 'ER', 'OR', 'PACS', 'DICOM', 'HPCSA', 'POPIA'
        ]
        
        for term in capitalize_terms:
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            enhanced = re.sub(pattern, term, enhanced, flags=re.IGNORECASE)
        
        return enhanced
    
    def _is_similar(self, word1, word2, threshold=0.7):
        """Check if two words are similar (simple implementation)"""
        if not word1 or not word2:
            return False
        
        # Simple character-based similarity
        longer = word1 if len(word1) > len(word2) else word2
        shorter = word2 if len(word1) > len(word2) else word1
        
        if len(longer) == 0:
            return True
        
        # Count matching characters
        matches = sum(1 for a, b in zip(longer, shorter) if a == b)
        similarity = matches / len(longer)
        
        return similarity >= threshold
    
    def detect_voice_shortcuts(self, audio_data, user_id):
        """Detect if audio contains a voice shortcut command"""
        try:
            from core.voice_matcher import VoicePatternMatcher
            
            matcher = VoicePatternMatcher(user_id)
            result = matcher.match_voice_command(audio_data, confidence_threshold=0.7)
            
            if result.get('success') and result.get('match_found'):
                return {
                    'shortcut_detected': True,
                    'shortcut': result.get('shortcut'),
                    'confidence': result.get('confidence'),
                    'template_content': result.get('template_content')
                }
            
            return {'shortcut_detected': False}
            
        except Exception as e:
            logger.error(f"Voice shortcut detection failed: {e}")
            return {'shortcut_detected': False, 'error': str(e)}
    
    def apply_medical_context(self, transcription, medical_context=None):
        """Apply medical terminology corrections with context"""
        if not transcription:
            return transcription
        
        enhanced = transcription
        
        # If medical context is provided, use it for better corrections
        if medical_context:
            # Context-aware corrections based on previous medical terms
            context_corrections = self._get_context_corrections(medical_context)
            
            import re
            for pattern, replacement in context_corrections.items():
                enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
        
        return enhanced
    
    def _get_context_corrections(self, medical_context):
        """Get context-aware corrections based on medical context"""
        corrections = {}
        
        # If cardiovascular terms are in context
        if any('heart' in term.lower() or 'cardiac' in term.lower() for term in medical_context):
            corrections.update({
                r'\bmi\b': 'myocardial infarction',
                r'\baf\b': 'atrial fibrillation',
                r'\bvt\b': 'ventricular tachycardia'
            })
        
        # If respiratory terms are in context
        if any('lung' in term.lower() or 'respiratory' in term.lower() for term in medical_context):
            corrections.update({
                r'\bcopd\b': 'chronic obstructive pulmonary disease',
                r'\basthma\b': 'asthma',
                r'\bpe\b': 'pulmonary embolism'
            })
        
        # If infectious disease terms are in context
        if any('infection' in term.lower() or 'fever' in term.lower() for term in medical_context):
            corrections.update({
                r'\bhiv\b': 'HIV',
                r'\btb\b': 'tuberculosis',
                r'\buti\b': 'urinary tract infection'
            })
        
        return corrections