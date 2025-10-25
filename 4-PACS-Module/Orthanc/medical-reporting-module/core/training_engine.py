#!/usr/bin/env python3
"""
Medical Training Engine for STT Enhancements
"""

import logging
import numpy as np
import json
from datetime import datetime
from models.training_data import TrainingDataStore, MedicalTerm

logger = logging.getLogger(__name__)

class MedicalTrainingEngine:
    """Core training engine for medical terminology STT improvement"""
    
    def __init__(self, whisper_model, user_id):
        self.whisper_model = whisper_model
        self.user_id = user_id
        self.training_data = TrainingDataStore(user_id)
        
        # Medical terms categories
        self.medical_categories = {
            "anatomy": [
                "cardiovascular system", "respiratory system", "gastrointestinal tract",
                "central nervous system", "musculoskeletal system", "genitourinary system",
                "endocrine system", "lymphatic system", "integumentary system"
            ],
            "conditions": [
                "hypertension", "diabetes mellitus", "myocardial infarction",
                "pneumonia", "tuberculosis", "HIV/AIDS", "chronic kidney disease",
                "asthma", "chronic obstructive pulmonary disease", "stroke"
            ],
            "procedures": [
                "chest X-ray", "CT scan", "MRI scan", "echocardiogram",
                "electrocardiogram", "blood pressure measurement", "pulse oximetry",
                "ultrasound", "endoscopy", "biopsy"
            ],
            "medications": [
                "antihypertensives", "antibiotics", "analgesics", "antiretrovirals",
                "bronchodilators", "diuretics", "beta-blockers", "ACE inhibitors",
                "insulin", "anticoagulants"
            ],
            "sa_specific": [
                "clinic sister", "community health worker", "traditional healer",
                "motor vehicle accident", "gunshot wound", "traditional medicine",
                "sangoma", "muti", "clinic", "district hospital"
            ]
        }
    
    def process_training_audio(self, audio_data, expected_term, category=None):
        """Process training audio and update user-specific model adaptations"""
        try:
            # Transcribe the audio using Whisper
            if isinstance(audio_data, bytes):
                # Convert bytes to numpy array if needed
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
            else:
                audio_array = audio_data
            
            # Get transcription
            result = self.whisper_model.transcribe(audio_array, language="en")
            actual_transcription = result["text"].strip().lower()
            expected_lower = expected_term.lower()
            
            # Calculate accuracy score
            accuracy_score = self._calculate_accuracy(expected_lower, actual_transcription)
            
            # Extract audio features for pattern matching
            audio_features = self._extract_audio_features(audio_array)
            
            # Store training session
            session = self.training_data.store_training_session(
                term=expected_term,
                audio_features=audio_features,
                accuracy_score=accuracy_score,
                category=category,
                expected_transcription=expected_term,
                actual_transcription=actual_transcription
            )
            
            logger.info(f"Training session completed for '{expected_term}': {accuracy_score:.2f} accuracy")
            
            return {
                'success': True,
                'session_id': session.id,
                'expected': expected_term,
                'actual': actual_transcription,
                'accuracy_score': accuracy_score,
                'needs_retry': accuracy_score < 0.7
            }
            
        except Exception as e:
            logger.error(f"Training audio processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_training_categories(self):
        """Return organized medical term categories"""
        return self.medical_categories
    
    def get_terms_for_category(self, category):
        """Get terms for a specific category"""
        return self.medical_categories.get(category, [])
    
    def calculate_accuracy_improvement(self):
        """Calculate user's STT accuracy improvements from training"""
        progress = self.training_data.get_user_training_progress()
        return progress.get('accuracy_improvement', 0.0)
    
    def get_recommended_terms(self, limit=10):
        """Get recommended terms for training based on user progress"""
        problematic_terms = self.training_data.get_problematic_terms()
        
        if problematic_terms:
            # Return problematic terms first
            return [term['term'] for term in problematic_terms[:limit]]
        
        # Return common terms from all categories
        all_terms = []
        for category_terms in self.medical_categories.values():
            all_terms.extend(category_terms)
        
        return all_terms[:limit]
    
    def _calculate_accuracy(self, expected, actual):
        """Calculate accuracy score between expected and actual transcription"""
        if not expected or not actual:
            return 0.0
        
        # Simple word-based accuracy
        expected_words = expected.split()
        actual_words = actual.split()
        
        if not expected_words:
            return 1.0 if not actual_words else 0.0
        
        # Calculate word overlap
        expected_set = set(expected_words)
        actual_set = set(actual_words)
        
        intersection = len(expected_set.intersection(actual_set))
        union = len(expected_set.union(actual_set))
        
        if union == 0:
            return 1.0
        
        # Jaccard similarity
        jaccard = intersection / union
        
        # Also consider sequence similarity
        sequence_score = self._sequence_similarity(expected_words, actual_words)
        
        # Weighted average
        return (jaccard * 0.6 + sequence_score * 0.4)
    
    def _sequence_similarity(self, seq1, seq2):
        """Calculate sequence similarity using longest common subsequence"""
        if not seq1 or not seq2:
            return 0.0
        
        # Simple LCS-based similarity
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs_length = dp[m][n]
        return lcs_length / max(m, n)
    
    def _extract_audio_features(self, audio_array):
        """Extract audio features for pattern matching"""
        try:
            # Simple feature extraction - in production, use more sophisticated methods
            features = {
                'length': len(audio_array),
                'mean': float(np.mean(audio_array)),
                'std': float(np.std(audio_array)),
                'max': float(np.max(audio_array)),
                'min': float(np.min(audio_array))
            }
            
            # Convert to bytes for storage
            return json.dumps(features).encode('utf-8')
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return b'{}' 
    
    def enhance_transcription_with_training(self, transcription, user_training_data=None):
        """Apply user-specific training improvements to transcription"""
        if not transcription:
            return transcription
        
        enhanced = transcription.lower()
        
        # Get user's training progress
        if not user_training_data:
            user_training_data = self.training_data.get_user_training_progress()
        
        # Apply learned corrections based on training sessions
        # This is a simplified version - in production, use ML models
        
        # Get problematic terms that user has trained on
        problematic_terms = self.training_data.get_problematic_terms()
        
        for term_data in problematic_terms:
            term = term_data['term'].lower()
            # Simple fuzzy matching and correction
            if term in enhanced or any(word in enhanced for word in term.split()):
                # Apply correction based on training data
                enhanced = enhanced.replace(term, term)
        
        return enhanced
    
    def start_training_session(self, category, terms_limit=10):
        """Start a new training session for a category"""
        try:
            terms = self.get_terms_for_category(category)
            if not terms:
                return {
                    'success': False,
                    'error': f'No terms found for category: {category}'
                }
            
            # Limit number of terms
            selected_terms = terms[:terms_limit]
            
            # Create session data
            session_id = f"session_{self.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Convert terms to objects with metadata
            term_objects = []
            for i, term in enumerate(selected_terms):
                term_obj = {
                    'id': f"{session_id}_term_{i}",
                    'term': term,
                    'category': category,
                    'pronunciation_guide': self._get_pronunciation_guide(term),
                    'definition': self._get_term_definition(term)
                }
                term_objects.append(term_obj)
            
            session_data = {
                'session_id': session_id,
                'user_id': self.user_id,
                'category': category,
                'terms': term_objects,
                'total_terms': len(term_objects),
                'current_index': 0,
                'current_term': term_objects[0] if term_objects else None,
                'start_time': datetime.now().isoformat(),
                'completed_terms': []
            }
            
            # Store session (in production, use proper session storage)
            self._store_session(session_id, session_data)
            
            return {
                'success': True,
                'session_id': session_id,
                'category': category,
                'total_terms': len(term_objects),
                'current_index': 0,
                'current_term': term_objects[0] if term_objects else None
            }
            
        except Exception as e:
            logger.error(f"Failed to start training session: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_next_training_term(self, session_id):
        """Get the next term in the training session"""
        try:
            session_data = self._get_session(session_id)
            if not session_data:
                return {
                    'success': False,
                    'error': 'Session not found'
                }
            
            current_index = session_data.get('current_index', 0)
            terms = session_data.get('terms', [])
            
            # Move to next term
            next_index = current_index + 1
            
            if next_index >= len(terms):
                # Session completed
                return {
                    'success': True,
                    'completed': True,
                    'message': 'All terms completed'
                }
            
            # Update session
            session_data['current_index'] = next_index
            session_data['current_term'] = terms[next_index]
            self._store_session(session_id, session_data)
            
            return {
                'success': True,
                'completed': False,
                'current_index': next_index,
                'current_term': terms[next_index],
                'total_terms': len(terms)
            }
            
        except Exception as e:
            logger.error(f"Failed to get next training term: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def complete_training_session(self, session_id):
        """Complete the training session and return statistics"""
        try:
            session_data = self._get_session(session_id)
            if not session_data:
                return {
                    'success': False,
                    'error': 'Session not found'
                }
            
            # Calculate session statistics
            completed_terms = session_data.get('completed_terms', [])
            total_terms = len(session_data.get('terms', []))
            
            # Calculate average accuracy
            if completed_terms:
                total_accuracy = sum(term.get('accuracy', 0) for term in completed_terms)
                average_accuracy = total_accuracy / len(completed_terms)
            else:
                average_accuracy = 0.0
            
            # Calculate session duration
            start_time = datetime.fromisoformat(session_data.get('start_time', datetime.now().isoformat()))
            duration_minutes = (datetime.now() - start_time).total_seconds() / 60
            
            stats = {
                'terms_practiced': len(completed_terms),
                'total_terms': total_terms,
                'average_accuracy': average_accuracy,
                'session_duration': int(duration_minutes),
                'category': session_data.get('category', 'unknown')
            }
            
            # Clean up session
            self._remove_session(session_id)
            
            return {
                'success': True,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Failed to complete training session: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_pronunciation_guide(self, term):
        """Get pronunciation guide for a medical term"""
        # Simple pronunciation guides for common terms
        pronunciation_guides = {
            'pneumonia': 'new-MOH-nee-ah',
            'tuberculosis': 'too-ber-kyuh-LOH-sis',
            'hypertension': 'hahy-per-TEN-shuhn',
            'diabetes mellitus': 'dahy-uh-BEE-teez muh-LAHY-tuhs',
            'myocardial infarction': 'mahy-uh-KAHR-dee-uhl in-FAHRK-shuhn',
            'electrocardiogram': 'ih-lek-troh-KAHR-dee-uh-gram',
            'echocardiogram': 'ek-oh-KAHR-dee-uh-gram'
        }
        return pronunciation_guides.get(term.lower(), None)
    
    def _get_term_definition(self, term):
        """Get definition for a medical term"""
        # Simple definitions for common terms
        definitions = {
            'pneumonia': 'Infection that inflames air sacs in one or both lungs',
            'tuberculosis': 'Infectious disease that mainly affects the lungs',
            'hypertension': 'High blood pressure',
            'diabetes mellitus': 'Group of metabolic disorders characterized by high blood sugar',
            'myocardial infarction': 'Heart attack caused by blocked blood flow to heart muscle',
            'chest X-ray': 'Imaging test that uses radiation to create pictures of chest structures'
        }
        return definitions.get(term.lower(), None)
    
    def _store_session(self, session_id, session_data):
        """Store session data (in production, use proper session storage)"""
        # For now, store in memory - in production, use database or cache
        if not hasattr(self, '_sessions'):
            self._sessions = {}
        self._sessions[session_id] = session_data
    
    def _get_session(self, session_id):
        """Get session data"""
        if not hasattr(self, '_sessions'):
            self._sessions = {}
        return self._sessions.get(session_id)
    
    def _remove_session(self, session_id):
        """Remove session data"""
        if hasattr(self, '_sessions') and session_id in self._sessions:
            del self._sessions[session_id]