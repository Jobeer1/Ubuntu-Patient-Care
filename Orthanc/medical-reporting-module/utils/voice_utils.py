"""
Voice processing utilities for South African English accents and medical terminology
"""

import logging
import re
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class SouthAfricanAccentProcessor:
    """Processor for South African English accent patterns"""
    
    def __init__(self):
        self.accent_patterns = self._load_accent_patterns()
        self.pronunciation_mappings = self._load_pronunciation_mappings()
        
        logger.info("South African accent processor initialized")
    
    def _load_accent_patterns(self) -> Dict[str, List[str]]:
        """Load South African English accent patterns"""
        return {
            # Vowel shifts common in South African English
            "kit_vowel": {
                "patterns": [r"\bi([tn])\b", r"\bi([ck])\b"],
                "replacements": ["e\\1", "e\\1"],
                "description": "KIT vowel centralization"
            },
            
            # Consonant patterns
            "th_fronting": {
                "patterns": [r"\bth([aeiou])", r"([aeiou])th\b"],
                "replacements": ["f\\1", "\\1f"],
                "description": "TH-fronting to F"
            },
            
            "th_stopping": {
                "patterns": [r"\bth([aeiou])", r"([aeiou])th\b"],
                "replacements": ["d\\1", "\\1d"],
                "description": "TH-stopping to D"
            },
            
            # R-dropping patterns
            "r_dropping": {
                "patterns": [r"([aeiou])r\b", r"([aeiou])r([bcdfghjklmnpqstvwxyz])"],
                "replacements": ["\\1", "\\1\\2"],
                "description": "R-dropping in non-rhotic positions"
            },
            
            # Monophthongization
            "diphthong_reduction": {
                "patterns": [r"\bai\b", r"\bau\b", r"\bei\b"],
                "replacements": ["a", "o", "e"],
                "description": "Diphthong reduction"
            }
        }
    
    def _load_pronunciation_mappings(self) -> Dict[str, str]:
        """Load common pronunciation variations"""
        return {
            # Common word variations in South African English
            "about": "aboot",
            "house": "hoos",
            "out": "oot",
            "south": "sooth",
            "mouth": "mooth",
            
            # Medical terms with SA pronunciation
            "pneumonia": "numonia",
            "tuberculosis": "tuberkulosis",
            "stethoscope": "stetoskoop",
            "radiograph": "radiograf",
            "ultrasound": "ultrasond",
            
            # Anatomical terms
            "thorax": "toraks",
            "abdomen": "abdomen",
            "pelvis": "pelwis",
            
            # Common phrases
            "patient": "pasient",
            "doctor": "dokter",
            "hospital": "hospitaal",
            "medicine": "medisyne"
        }
    
    def process_accent_variations(self, text: str) -> List[str]:
        """Generate accent variation candidates for text"""
        try:
            variations = [text]  # Original text
            
            # Apply pronunciation mappings
            mapped_text = text.lower()
            for standard, variant in self.pronunciation_mappings.items():
                if standard in mapped_text:
                    mapped_text = mapped_text.replace(standard, variant)
            
            if mapped_text != text.lower():
                variations.append(mapped_text)
            
            # Apply accent patterns
            for pattern_name, pattern_info in self.accent_patterns.items():
                pattern_text = text.lower()
                
                for i, pattern in enumerate(pattern_info["patterns"]):
                    replacement = pattern_info["replacements"][i]
                    modified_text = re.sub(pattern, replacement, pattern_text)
                    
                    if modified_text != pattern_text:
                        variations.append(modified_text)
            
            # Remove duplicates while preserving order
            unique_variations = []
            seen = set()
            for variation in variations:
                if variation.lower() not in seen:
                    unique_variations.append(variation)
                    seen.add(variation.lower())
            
            return unique_variations
            
        except Exception as e:
            logger.error(f"Failed to process accent variations: {e}")
            return [text]

class MedicalTerminologyProcessor:
    """Processor for medical terminology with South African context"""
    
    def __init__(self):
        self.medical_dictionary = self._load_medical_dictionary()
        self.abbreviation_expansions = self._load_abbreviations()
        self.context_patterns = self._load_context_patterns()
        
        logger.info("Medical terminology processor initialized")
    
    def _load_medical_dictionary(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive medical dictionary"""
        return {
            # Respiratory system (high priority in SA due to TB, mining)
            "tuberculosis": {
                "variants": ["tb", "tuberkulosis", "consumption"],
                "category": "infectious_disease",
                "priority": "high",
                "context": ["lung", "chest", "respiratory", "cough", "fever"]
            },
            
            "pneumoconiosis": {
                "variants": ["numoconiosis", "dust lung", "miners lung"],
                "category": "occupational_disease",
                "priority": "high",
                "context": ["mining", "dust", "occupational", "silica"]
            },
            
            "silicosis": {
                "variants": ["silicosis", "silica lung"],
                "category": "occupational_disease",
                "priority": "high",
                "context": ["mining", "silica", "dust", "occupational"]
            },
            
            "pneumonia": {
                "variants": ["numonia", "lung infection"],
                "category": "infectious_disease",
                "priority": "high",
                "context": ["lung", "infection", "fever", "cough"]
            },
            
            # HIV-related conditions (high prevalence in SA)
            "pneumocystis": {
                "variants": ["pcp", "pneumocystis pneumonia"],
                "category": "opportunistic_infection",
                "priority": "high",
                "context": ["hiv", "aids", "immunocompromised"]
            },
            
            "kaposi": {
                "variants": ["kaposis sarcoma", "ks"],
                "category": "malignancy",
                "priority": "medium",
                "context": ["hiv", "aids", "skin", "lesion"]
            },
            
            # Trauma (high incidence in SA)
            "fracture": {
                "variants": ["break", "broken bone", "frakture"],
                "category": "trauma",
                "priority": "high",
                "context": ["bone", "trauma", "accident", "fall"]
            },
            
            "gunshot": {
                "variants": ["gsw", "bullet wound", "firearm injury"],
                "category": "trauma",
                "priority": "urgent",
                "context": ["trauma", "penetrating", "bullet", "wound"]
            },
            
            # Common findings
            "consolidation": {
                "variants": ["konsolidasie", "opacity"],
                "category": "radiological_finding",
                "priority": "medium",
                "context": ["lung", "chest", "xray", "opacity"]
            },
            
            "atelectasis": {
                "variants": ["collapse", "atelektase"],
                "category": "radiological_finding",
                "priority": "medium",
                "context": ["lung", "collapse", "volume loss"]
            },
            
            "pleural_effusion": {
                "variants": ["fluid", "pleural fluid", "effusie"],
                "category": "radiological_finding",
                "priority": "medium",
                "context": ["pleura", "fluid", "chest"]
            }
        }
    
    def _load_abbreviations(self) -> Dict[str, str]:
        """Load medical abbreviations and expansions"""
        return {
            # Common medical abbreviations
            "tb": "tuberculosis",
            "mdr": "multidrug-resistant",
            "xdr": "extensively drug-resistant",
            "hiv": "human immunodeficiency virus",
            "aids": "acquired immunodeficiency syndrome",
            "pcp": "pneumocystis pneumonia",
            "ks": "kaposi's sarcoma",
            "gsw": "gunshot wound",
            "mva": "motor vehicle accident",
            "cxr": "chest x-ray",
            "ct": "computed tomography",
            "mri": "magnetic resonance imaging",
            "us": "ultrasound",
            
            # Anatomical abbreviations
            "rul": "right upper lobe",
            "rml": "right middle lobe",
            "rll": "right lower lobe",
            "lul": "left upper lobe",
            "lll": "left lower lobe",
            "rul": "right upper lobe",
            
            # Clinical abbreviations
            "wnl": "within normal limits",
            "naa": "no acute abnormality",
            "sob": "shortness of breath",
            "doe": "dyspnea on exertion",
            "cp": "chest pain",
            "loc": "loss of consciousness"
        }
    
    def _load_context_patterns(self) -> Dict[str, List[str]]:
        """Load context patterns for disambiguation"""
        return {
            "respiratory": [
                "lung", "chest", "respiratory", "breathing", "cough",
                "dyspnea", "shortness of breath", "wheeze", "stridor"
            ],
            
            "cardiac": [
                "heart", "cardiac", "cardiovascular", "chest pain",
                "palpitations", "murmur", "rhythm", "rate"
            ],
            
            "gastrointestinal": [
                "abdomen", "stomach", "bowel", "intestine", "liver",
                "gallbladder", "pancreas", "nausea", "vomiting"
            ],
            
            "musculoskeletal": [
                "bone", "joint", "muscle", "fracture", "dislocation",
                "arthritis", "osteoporosis", "trauma"
            ],
            
            "neurological": [
                "brain", "head", "neurological", "seizure", "stroke",
                "headache", "confusion", "weakness"
            ],
            
            "infectious": [
                "infection", "fever", "sepsis", "bacteria", "virus",
                "antibiotic", "culture", "white blood cell"
            ]
        }
    
    def process_medical_terms(self, text: str, context: str = "") -> str:
        """Process text to correct medical terminology"""
        try:
            processed_text = text.lower()
            
            # Expand abbreviations first
            for abbrev, expansion in self.abbreviation_expansions.items():
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(abbrev) + r'\b'
                processed_text = re.sub(pattern, expansion, processed_text, flags=re.IGNORECASE)
            
            # Apply medical dictionary corrections
            for term, term_info in self.medical_dictionary.items():
                # Check if context matches
                if context and term_info.get("context"):
                    context_match = any(ctx in context.lower() for ctx in term_info["context"])
                    if not context_match:
                        continue
                
                # Apply variants
                for variant in term_info["variants"]:
                    pattern = r'\b' + re.escape(variant) + r'\b'
                    processed_text = re.sub(pattern, term, processed_text, flags=re.IGNORECASE)
            
            # Capitalize sentences
            sentences = processed_text.split('. ')
            capitalized_sentences = [s.capitalize() for s in sentences]
            processed_text = '. '.join(capitalized_sentences)
            
            return processed_text
            
        except Exception as e:
            logger.error(f"Failed to process medical terms: {e}")
            return text
    
    def get_term_suggestions(self, partial_term: str, context: str = "") -> List[str]:
        """Get medical term suggestions for partial input"""
        try:
            suggestions = []
            partial_lower = partial_term.lower()
            
            for term, term_info in self.medical_dictionary.items():
                # Check main term
                if term.startswith(partial_lower):
                    suggestions.append(term)
                
                # Check variants
                for variant in term_info["variants"]:
                    if variant.startswith(partial_lower):
                        suggestions.append(variant)
            
            # Sort by priority and relevance
            def sort_key(suggestion):
                term_info = self.medical_dictionary.get(suggestion, {})
                priority_score = {"high": 3, "medium": 2, "low": 1}.get(
                    term_info.get("priority", "low"), 1)
                
                # Boost score if context matches
                if context and term_info.get("context"):
                    context_match = any(ctx in context.lower() for ctx in term_info["context"])
                    if context_match:
                        priority_score += 2
                
                return -priority_score  # Negative for descending sort
            
            suggestions.sort(key=sort_key)
            return suggestions[:10]  # Return top 10 suggestions
            
        except Exception as e:
            logger.error(f"Failed to get term suggestions: {e}")
            return []

class AudioQualityAnalyzer:
    """Analyzer for audio quality assessment"""
    
    def __init__(self):
        self.quality_thresholds = {
            "excellent": {"snr": 20, "clarity": 0.9, "volume": 0.7},
            "good": {"snr": 15, "clarity": 0.7, "volume": 0.5},
            "fair": {"snr": 10, "clarity": 0.5, "volume": 0.3},
            "poor": {"snr": 5, "clarity": 0.3, "volume": 0.1}
        }
        
        logger.info("Audio quality analyzer initialized")
    
    def analyze_audio_quality(self, audio_data: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        """Analyze audio quality metrics"""
        try:
            # Convert bytes to numpy array (simplified)
            # In production, would use proper audio processing libraries
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            if len(audio_array) == 0:
                return {"quality": "poor", "metrics": {}}
            
            # Calculate basic metrics
            metrics = {
                "duration": len(audio_array) / sample_rate,
                "sample_rate": sample_rate,
                "data_size": len(audio_data),
                "rms_level": self._calculate_rms(audio_array),
                "peak_level": self._calculate_peak(audio_array),
                "zero_crossing_rate": self._calculate_zcr(audio_array),
                "estimated_snr": self._estimate_snr(audio_array),
                "silence_ratio": self._calculate_silence_ratio(audio_array)
            }
            
            # Determine overall quality
            quality = self._determine_quality(metrics)
            
            return {
                "quality": quality,
                "metrics": metrics,
                "recommendations": self._get_quality_recommendations(quality, metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze audio quality: {e}")
            return {"quality": "unknown", "metrics": {}}
    
    def _calculate_rms(self, audio_array: np.ndarray) -> float:
        """Calculate RMS (Root Mean Square) level"""
        try:
            return float(np.sqrt(np.mean(audio_array.astype(np.float64) ** 2)))
        except:
            return 0.0
    
    def _calculate_peak(self, audio_array: np.ndarray) -> float:
        """Calculate peak level"""
        try:
            return float(np.max(np.abs(audio_array)))
        except:
            return 0.0
    
    def _calculate_zcr(self, audio_array: np.ndarray) -> float:
        """Calculate Zero Crossing Rate"""
        try:
            zero_crossings = np.sum(np.diff(np.sign(audio_array)) != 0)
            return zero_crossings / len(audio_array)
        except:
            return 0.0
    
    def _estimate_snr(self, audio_array: np.ndarray) -> float:
        """Estimate Signal-to-Noise Ratio (simplified)"""
        try:
            # Simple SNR estimation based on signal variance
            signal_power = np.var(audio_array.astype(np.float64))
            
            # Estimate noise from quiet segments (bottom 10% of signal)
            sorted_abs = np.sort(np.abs(audio_array))
            noise_samples = sorted_abs[:len(sorted_abs) // 10]
            noise_power = np.var(noise_samples.astype(np.float64))
            
            if noise_power > 0:
                snr = 10 * np.log10(signal_power / noise_power)
                return float(snr)
            
            return 20.0  # Default good SNR if no noise detected
            
        except:
            return 10.0  # Default moderate SNR
    
    def _calculate_silence_ratio(self, audio_array: np.ndarray) -> float:
        """Calculate ratio of silence in audio"""
        try:
            # Define silence threshold (5% of max amplitude)
            threshold = 0.05 * np.max(np.abs(audio_array))
            silence_samples = np.sum(np.abs(audio_array) < threshold)
            return silence_samples / len(audio_array)
        except:
            return 0.0
    
    def _determine_quality(self, metrics: Dict[str, Any]) -> str:
        """Determine overall audio quality"""
        try:
            snr = metrics.get("estimated_snr", 0)
            rms = metrics.get("rms_level", 0)
            silence_ratio = metrics.get("silence_ratio", 1.0)
            
            # Normalize RMS to 0-1 scale (rough approximation)
            normalized_rms = min(1.0, rms / 10000.0)
            
            # Calculate quality score
            quality_score = 0
            
            # SNR contribution (40%)
            if snr >= 20:
                quality_score += 40
            elif snr >= 15:
                quality_score += 30
            elif snr >= 10:
                quality_score += 20
            elif snr >= 5:
                quality_score += 10
            
            # RMS level contribution (30%)
            if normalized_rms >= 0.7:
                quality_score += 30
            elif normalized_rms >= 0.5:
                quality_score += 25
            elif normalized_rms >= 0.3:
                quality_score += 15
            elif normalized_rms >= 0.1:
                quality_score += 10
            
            # Silence ratio contribution (30% - less silence is better)
            if silence_ratio <= 0.1:
                quality_score += 30
            elif silence_ratio <= 0.2:
                quality_score += 25
            elif silence_ratio <= 0.4:
                quality_score += 15
            elif silence_ratio <= 0.6:
                quality_score += 10
            
            # Determine quality level
            if quality_score >= 80:
                return "excellent"
            elif quality_score >= 60:
                return "good"
            elif quality_score >= 40:
                return "fair"
            else:
                return "poor"
                
        except Exception as e:
            logger.error(f"Failed to determine quality: {e}")
            return "fair"
    
    def _get_quality_recommendations(self, quality: str, metrics: Dict[str, Any]) -> List[str]:
        """Get recommendations for improving audio quality"""
        recommendations = []
        
        try:
            if quality in ["poor", "fair"]:
                snr = metrics.get("estimated_snr", 0)
                rms = metrics.get("rms_level", 0)
                silence_ratio = metrics.get("silence_ratio", 0)
                
                if snr < 15:
                    recommendations.append("Reduce background noise")
                    recommendations.append("Move closer to microphone")
                
                if rms < 5000:
                    recommendations.append("Speak louder")
                    recommendations.append("Check microphone sensitivity")
                
                if silence_ratio > 0.3:
                    recommendations.append("Reduce pauses between words")
                    recommendations.append("Speak more continuously")
                
                recommendations.append("Ensure quiet environment")
                recommendations.append("Check microphone positioning")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return ["Check audio setup"]

# Utility functions
def preprocess_south_african_text(text: str, context: str = "") -> str:
    """Preprocess text for South African English patterns"""
    try:
        accent_processor = SouthAfricanAccentProcessor()
        medical_processor = MedicalTerminologyProcessor()
        
        # Process medical terminology first
        processed_text = medical_processor.process_medical_terms(text, context)
        
        # Then apply accent processing if needed
        # (In production, this would be more sophisticated)
        
        return processed_text
        
    except Exception as e:
        logger.error(f"Failed to preprocess South African text: {e}")
        return text

def analyze_voice_audio(audio_data: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
    """Analyze voice audio for quality and characteristics"""
    try:
        analyzer = AudioQualityAnalyzer()
        return analyzer.analyze_audio_quality(audio_data, sample_rate)
        
    except Exception as e:
        logger.error(f"Failed to analyze voice audio: {e}")
        return {"quality": "unknown", "metrics": {}}

def get_medical_suggestions(partial_term: str, context: str = "") -> List[str]:
    """Get medical term suggestions"""
    try:
        processor = MedicalTerminologyProcessor()
        return processor.get_term_suggestions(partial_term, context)
        
    except Exception as e:
        logger.error(f"Failed to get medical suggestions: {e}")
        return []