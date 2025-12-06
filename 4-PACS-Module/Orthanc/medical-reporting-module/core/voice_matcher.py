#!/usr/bin/env python3
"""
Voice Pattern Matcher for Voice Shortcuts
"""

import logging
import numpy as np
import json
from datetime import datetime
from models.voice_shortcuts import VoiceShortcutStore

logger = logging.getLogger(__name__)

class VoicePatternMatcher:
    """Voice pattern matching for shortcuts"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.shortcuts = VoiceShortcutStore(user_id)
    
    def register_voice_shortcut(self, audio_data, shortcut_name, template_type=None, template_content=None):
        """Register a new voice shortcut with audio pattern"""
        try:
            # Extract audio features
            audio_features = self._extract_audio_features(audio_data)
            
            # Create shortcut
            shortcut = self.shortcuts.create_shortcut(
                name=shortcut_name,
                audio_features=audio_features,
                template_id=template_type,
                template_content=template_content
            )
            
            logger.info(f"Registered voice shortcut '{shortcut_name}' for user {self.user_id}")
            
            return {
                'success': True,
                'shortcut_id': shortcut.id,
                'name': shortcut_name,
                'message': 'Voice shortcut registered successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to register voice shortcut: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def match_voice_command(self, audio_data, confidence_threshold=0.8):
        """Match incoming audio against registered shortcuts"""
        try:
            # Extract features from input audio
            input_features = self._extract_audio_features(audio_data)
            input_features_dict = json.loads(input_features.decode('utf-8'))
            
            # Get all user shortcuts
            user_shortcuts = self.shortcuts.get_user_shortcuts()
            
            if not user_shortcuts:
                return {
                    'success': True,
                    'match_found': False,
                    'message': 'No shortcuts registered'
                }
            
            best_match = None
            best_confidence = 0.0
            
            # Compare against each shortcut
            for shortcut in user_shortcuts:
                try:
                    stored_features = json.loads(shortcut['audio_features'] if isinstance(shortcut['audio_features'], str) else shortcut['audio_features'].decode('utf-8'))
                    confidence = self._calculate_similarity(input_features_dict, stored_features)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = shortcut
                        
                except Exception as e:
                    logger.error(f"Error comparing shortcut {shortcut['id']}: {e}")
                    continue
            
            # Check if best match meets threshold
            if best_match and best_confidence >= confidence_threshold:
                # Record successful usage
                self.shortcuts.record_usage(
                    shortcut_id=best_match['id'],
                    match_confidence=best_confidence,
                    success=True
                )
                
                return {
                    'success': True,
                    'matched': True,
                    'shortcut': {
                        'shortcut_name': best_match['shortcut_name'],
                        'template_type': best_match.get('template_type'),
                        'template_content': best_match.get('template_content')
                    },
                    'confidence': best_confidence
                }
            
            # No match found above threshold
            return {
                'success': True,
                'matched': False,
                'best_confidence': best_confidence,
                'threshold': confidence_threshold,
                'suggestions': self._get_similar_shortcuts(user_shortcuts, input_features_dict, 0.5)
            }
            
        except Exception as e:
            logger.error(f"Voice command matching failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_shortcut_accuracy(self, shortcut_id, match_success):
        """Update shortcut matching accuracy based on usage"""
        try:
            confidence = 1.0 if match_success else 0.0
            success = self.shortcuts.record_usage(
                shortcut_id=shortcut_id,
                match_confidence=confidence,
                success=match_success
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update shortcut accuracy: {e}")
            return False
    
    def _extract_audio_features(self, audio_data):
        """Extract audio features for pattern matching"""
        try:
            if isinstance(audio_data, bytes):
                # Convert bytes to numpy array
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
            else:
                audio_array = np.array(audio_data, dtype=np.float32)
            
            # Extract comprehensive features
            features = {
                'length': len(audio_array),
                'duration': len(audio_array) / 16000.0,  # Assuming 16kHz sample rate
                'mean': float(np.mean(audio_array)),
                'std': float(np.std(audio_array)),
                'max': float(np.max(audio_array)),
                'min': float(np.min(audio_array)),
                'rms': float(np.sqrt(np.mean(audio_array**2))),
                'zero_crossings': int(np.sum(np.diff(np.sign(audio_array)) != 0))
            }
            
            # Add spectral features (simplified)
            if len(audio_array) > 0:
                # Simple energy distribution
                chunk_size = len(audio_array) // 4
                if chunk_size > 0:
                    chunks = [audio_array[i:i+chunk_size] for i in range(0, len(audio_array), chunk_size)]
                    features['energy_distribution'] = [float(np.sum(chunk**2)) for chunk in chunks[:4]]
                else:
                    features['energy_distribution'] = [float(np.sum(audio_array**2))]
            
            return json.dumps(features).encode('utf-8')
            
        except Exception as e:
            logger.error(f"Audio feature extraction failed: {e}")
            return json.dumps({}).encode('utf-8')
    
    def _calculate_similarity(self, features1, features2):
        """Calculate similarity between two feature sets"""
        try:
            # Normalize and compare key features
            similarity_score = 0.0
            total_weight = 0.0
            
            # Duration similarity (important for voice commands)
            if 'duration' in features1 and 'duration' in features2:
                duration_diff = abs(features1['duration'] - features2['duration'])
                duration_similarity = max(0, 1 - (duration_diff / max(features1['duration'], features2['duration'], 0.1)))
                similarity_score += duration_similarity * 0.3
                total_weight += 0.3
            
            # RMS energy similarity
            if 'rms' in features1 and 'rms' in features2:
                rms_diff = abs(features1['rms'] - features2['rms'])
                rms_similarity = max(0, 1 - (rms_diff / max(features1['rms'], features2['rms'], 0.001)))
                similarity_score += rms_similarity * 0.2
                total_weight += 0.2
            
            # Zero crossings similarity (voice pattern indicator)
            if 'zero_crossings' in features1 and 'zero_crossings' in features2:
                zc_diff = abs(features1['zero_crossings'] - features2['zero_crossings'])
                max_zc = max(features1['zero_crossings'], features2['zero_crossings'], 1)
                zc_similarity = max(0, 1 - (zc_diff / max_zc))
                similarity_score += zc_similarity * 0.2
                total_weight += 0.2
            
            # Energy distribution similarity
            if 'energy_distribution' in features1 and 'energy_distribution' in features2:
                ed1 = features1['energy_distribution']
                ed2 = features2['energy_distribution']
                
                if len(ed1) == len(ed2) and len(ed1) > 0:
                    # Normalize energy distributions
                    sum1 = sum(ed1) if sum(ed1) > 0 else 1
                    sum2 = sum(ed2) if sum(ed2) > 0 else 1
                    norm_ed1 = [e / sum1 for e in ed1]
                    norm_ed2 = [e / sum2 for e in ed2]
                    
                    # Calculate cosine similarity
                    dot_product = sum(a * b for a, b in zip(norm_ed1, norm_ed2))
                    magnitude1 = np.sqrt(sum(a * a for a in norm_ed1))
                    magnitude2 = np.sqrt(sum(a * a for a in norm_ed2))
                    
                    if magnitude1 > 0 and magnitude2 > 0:
                        cosine_sim = dot_product / (magnitude1 * magnitude2)
                        similarity_score += cosine_sim * 0.3
                        total_weight += 0.3
            
            # Return normalized similarity
            if total_weight > 0:
                return similarity_score / total_weight
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    def _get_similar_shortcuts(self, shortcuts, input_features, min_confidence=0.3):
        """Get shortcuts similar to input for suggestions"""
        similar = []
        
        for shortcut in shortcuts:
            try:
                if isinstance(shortcut.get('audio_features'), bytes):
                    stored_features = json.loads(shortcut['audio_features'].decode('utf-8'))
                else:
                    stored_features = json.loads(shortcut['audio_features'])
                    
                confidence = self._calculate_similarity(input_features, stored_features)
                
                if confidence >= min_confidence:
                    similar.append({
                        'shortcut': shortcut,
                        'confidence': confidence
                    })
                    
            except Exception as e:
                logger.error(f"Error calculating similarity for shortcut {shortcut.get('id')}: {e}")
                continue
        
        # Sort by confidence and return top 3
        similar.sort(key=lambda x: x['confidence'], reverse=True)
        return similar[:3]