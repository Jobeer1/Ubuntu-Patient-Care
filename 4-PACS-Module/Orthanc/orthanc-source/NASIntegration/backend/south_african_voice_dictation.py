"""
South African Voice Dictation System
Advanced STT with SA accent recognition and medical terminology
"""

import os
import json
import wave
import tempfile
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import sqlite3
import hashlib
import base64
from dataclasses import dataclass
import logging

try:
    import vosk
    import pyaudio
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("Warning: Vosk not available. Install with: pip install vosk pyaudio")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    print("Warning: SpeechRecognition not available. Install with: pip install SpeechRecognition")

from .south_african_localization import sa_localization

@dataclass
class DictationSession:
    """Voice dictation session data"""
    session_id: str
    user_id: str
    patient_id: str
    study_id: str
    audio_file_path: str
    raw_transcript: str
    corrected_transcript: str
    confidence_score: float
    language: str
    created_at: str
    status: str  # 'recording', 'processing', 'transcribed', 'corrected', 'finalized'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'patient_id': self.patient_id,
            'study_id': self.study_id,
            'raw_transcript': self.raw_transcript,
            'corrected_transcript': self.corrected_transcript,
            'confidence_score': self.confidence_score,
            'language': self.language,
            'created_at': self.created_at,
            'status': self.status
        }

class SouthAfricanVoiceDictation:
    """Advanced voice dictation system for South African medical professionals"""
    
    def __init__(self, db_path: str = "voice_dictation.db"):
        self.db_path = db_path
        self.logger = self._setup_logging()
        self.audio_storage_path = "audio_files"
        self.vosk_model = None
        self.recognizer = None
        self.medical_vocabulary = self._load_medical_vocabulary()
        self.sa_accent_corrections = self._load_sa_accent_corrections()
        self._init_database()
        self._init_speech_engines()
        
        # Create audio storage directory
        os.makedirs(self.audio_storage_path, exist_ok=True)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for voice dictation"""
        logger = logging.getLogger('voice_dictation')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_database(self):
        """Initialize voice dictation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Dictation sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dictation_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                patient_id TEXT,
                study_id TEXT,
                audio_file_path TEXT NOT NULL,
                raw_transcript TEXT,
                corrected_transcript TEXT,
                confidence_score REAL,
                language TEXT DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'recording'
            )
        ''')
        
        # Correction learning table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS correction_learning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_text TEXT NOT NULL,
                corrected_text TEXT NOT NULL,
                user_id TEXT,
                frequency INTEGER DEFAULT 1,
                confidence_improvement REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Medical vocabulary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medical_vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT UNIQUE NOT NULL,
                pronunciation TEXT,
                category TEXT,
                frequency INTEGER DEFAULT 1,
                language TEXT DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Voice profiles table (for accent adaptation)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS voice_profiles (
                user_id TEXT PRIMARY KEY,
                accent_type TEXT,
                language_preference TEXT DEFAULT 'en',
                voice_characteristics TEXT,  -- JSON
                adaptation_data TEXT,        -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_speech_engines(self):
        """Initialize speech recognition engines"""
        try:
            if VOSK_AVAILABLE:
                # Try to load Vosk model (download if needed)
                model_path = self._get_vosk_model_path()
                if model_path and os.path.exists(model_path):
                    self.vosk_model = vosk.Model(model_path)
                    self.logger.info("Vosk model loaded successfully")
                else:
                    self.logger.warning("Vosk model not found. Download from https://alphacephei.com/vosk/models")
            
            if SR_AVAILABLE:
                self.recognizer = sr.Recognizer()
                self.logger.info("SpeechRecognition initialized")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize speech engines: {e}")
    
    def _get_vosk_model_path(self) -> Optional[str]:
        """Get path to Vosk model, prioritizing SA English models"""
        possible_paths = [
            "models/vosk-model-en-za-0.22",  # South African English
            "models/vosk-model-en-us-0.22",  # US English fallback
            "models/vosk-model-small-en-us-0.15",  # Small model fallback
            "/usr/share/vosk/models/vosk-model-en-za-0.22",
            "/opt/vosk/models/vosk-model-en-za-0.22"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _load_medical_vocabulary(self) -> Dict[str, List[str]]:
        """Load South African medical vocabulary and terminology"""
        return {
            'anatomy': [
                'abdomen', 'thorax', 'pelvis', 'cranium', 'vertebrae', 'sternum',
                'ribs', 'clavicle', 'scapula', 'humerus', 'radius', 'ulna',
                'femur', 'tibia', 'fibula', 'patella', 'mandible', 'maxilla'
            ],
            'pathology': [
                'pneumonia', 'pneumothorax', 'pleural effusion', 'atelectasis',
                'consolidation', 'nodule', 'mass', 'lesion', 'fracture',
                'dislocation', 'subluxation', 'osteoporosis', 'arthritis',
                'osteomyelitis', 'neoplasm', 'carcinoma', 'sarcoma'
            ],
            'procedures': [
                'radiography', 'fluoroscopy', 'tomography', 'angiography',
                'myelography', 'arthrography', 'hysterosalpingography',
                'intravenous pyelography', 'barium enema', 'upper GI series'
            ],
            'contrast_agents': [
                'iodine', 'barium', 'gadolinium', 'omnipaque', 'visipaque',
                'ultravist', 'dotarem', 'magnevist', 'primovist'
            ],
            'measurements': [
                'millimeter', 'centimeter', 'millilitre', 'hounsfield units',
                'kilovoltage', 'milliamperage', 'milliseconds', 'tesla'
            ],
            'sa_medical_terms': [
                'casualty', 'theatre', 'ward', 'matron', 'sister', 'registrar',
                'consultant', 'houseman', 'medical officer', 'radiographer',
                'sonographer', 'medical aid', 'discovery', 'momentum', 'gems'
            ]
        }
    
    def _load_sa_accent_corrections(self) -> Dict[str, str]:
        """Load South African accent-specific corrections"""
        return {
            # Common SA pronunciation variations
            'penshent': 'patient',
            'penshen': 'patient', 
            'theeta': 'theatre',
            'theetre': 'theatre',
            'sistah': 'sister',
            'doctah': 'doctor',
            'watah': 'water',
            'centah': 'center',
            'centeh': 'centre',
            'medicul': 'medical',
            'hospitol': 'hospital',
            'x-rey': 'x-ray',
            'sken': 'scan',
            'imej': 'image',
            'imige': 'image',
            'repot': 'report',
            'repawt': 'report',
            'nohmal': 'normal',
            'abnohmal': 'abnormal',
            'fractyah': 'fracture',
            'infectshun': 'infection',
            'inflammeshun': 'inflammation',
            'pneumonye': 'pneumonia',
            'bronkitis': 'bronchitis',
            'arthrytis': 'arthritis',
            'osteopohrosis': 'osteoporosis'
        }
    
    def create_dictation_session(self, user_id: str, patient_id: str = None, 
                                study_id: str = None, language: str = 'en') -> str:
        """Create a new dictation session"""
        session_id = f"dict_{hashlib.md5(f'{user_id}_{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"
        
        # Create audio file path
        audio_filename = f"{session_id}.wav"
        audio_file_path = os.path.join(self.audio_storage_path, audio_filename)
        
        # Store session in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO dictation_sessions (
                session_id, user_id, patient_id, study_id, audio_file_path, language, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, user_id, patient_id, study_id, audio_file_path, language, 'recording'))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Created dictation session: {session_id}")
        return session_id
    
    def save_audio_data(self, session_id: str, audio_data: bytes, 
                       sample_rate: int = 16000, channels: int = 1) -> bool:
        """Save audio data to file"""
        try:
            session = self.get_dictation_session(session_id)
            if not session:
                return False
            
            # Save as WAV file
            with wave.open(session.audio_file_path, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data)
            
            # Update session status
            self._update_session_status(session_id, 'processing')
            
            self.logger.info(f"Audio saved for session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save audio for session {session_id}: {e}")
            return False
    
    def transcribe_audio(self, session_id: str) -> Optional[str]:
        """Transcribe audio using available STT engines"""
        session = self.get_dictation_session(session_id)
        if not session or not os.path.exists(session.audio_file_path):
            return None
        
        transcript = None
        confidence = 0.0
        
        try:
            # Try Vosk first (better for SA accents if model available)
            if self.vosk_model:
                transcript, confidence = self._transcribe_with_vosk(session.audio_file_path)
            
            # Fallback to SpeechRecognition
            if not transcript and SR_AVAILABLE:
                transcript, confidence = self._transcribe_with_sr(session.audio_file_path)
            
            if transcript:
                # Apply SA accent corrections
                transcript = self._apply_accent_corrections(transcript)
                
                # Apply medical vocabulary corrections
                transcript = self._apply_medical_corrections(transcript)
                
                # Update session with transcript
                self._update_session_transcript(session_id, transcript, confidence)
                
                self.logger.info(f"Transcription completed for session: {session_id}")
                return transcript
            
        except Exception as e:
            self.logger.error(f"Transcription failed for session {session_id}: {e}")
        
        return None
    
    def _transcribe_with_vosk(self, audio_file_path: str) -> Tuple[str, float]:
        """Transcribe using Vosk"""
        try:
            rec = vosk.KaldiRecognizer(self.vosk_model, 16000)
            
            with wave.open(audio_file_path, 'rb') as wf:
                transcript_parts = []
                confidence_scores = []
                
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        if 'text' in result and result['text']:
                            transcript_parts.append(result['text'])
                            confidence_scores.append(result.get('confidence', 0.5))
                
                # Get final result
                final_result = json.loads(rec.FinalResult())
                if 'text' in final_result and final_result['text']:
                    transcript_parts.append(final_result['text'])
                    confidence_scores.append(final_result.get('confidence', 0.5))
                
                transcript = ' '.join(transcript_parts)
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
                
                return transcript, avg_confidence
                
        except Exception as e:
            self.logger.error(f"Vosk transcription failed: {e}")
            return "", 0.0
    
    def _transcribe_with_sr(self, audio_file_path: str) -> Tuple[str, float]:
        """Transcribe using SpeechRecognition library"""
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio = self.recognizer.record(source)
            
            # Try Google Speech Recognition (requires internet)
            try:
                transcript = self.recognizer.recognize_google(audio, language='en-ZA')
                return transcript, 0.8  # Assume good confidence for Google
            except sr.UnknownValueError:
                return "", 0.0
            except sr.RequestError:
                # Fallback to offline recognition if available
                try:
                    transcript = self.recognizer.recognize_sphinx(audio)
                    return transcript, 0.6  # Lower confidence for Sphinx
                except:
                    return "", 0.0
                    
        except Exception as e:
            self.logger.error(f"SpeechRecognition transcription failed: {e}")
            return "", 0.0
    
    def _apply_accent_corrections(self, transcript: str) -> str:
        """Apply South African accent corrections"""
        corrected = transcript.lower()
        
        for incorrect, correct in self.sa_accent_corrections.items():
            corrected = corrected.replace(incorrect, correct)
        
        return corrected
    
    def _apply_medical_corrections(self, transcript: str) -> str:
        """Apply medical vocabulary corrections"""
        words = transcript.split()
        corrected_words = []
        
        for word in words:
            # Check if word is in medical vocabulary
            corrected_word = word
            for category, terms in self.medical_vocabulary.items():
                for term in terms:
                    if self._fuzzy_match(word.lower(), term.lower()):
                        corrected_word = term
                        break
                if corrected_word != word:
                    break
            
            corrected_words.append(corrected_word)
        
        return ' '.join(corrected_words)
    
    def _fuzzy_match(self, word1: str, word2: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy matching for word correction"""
        if len(word1) < 3 or len(word2) < 3:
            return word1 == word2
        
        # Simple Levenshtein distance approximation
        if abs(len(word1) - len(word2)) > 2:
            return False
        
        matches = sum(c1 == c2 for c1, c2 in zip(word1, word2))
        similarity = matches / max(len(word1), len(word2))
        
        return similarity >= threshold
    
    def submit_correction(self, session_id: str, corrected_transcript: str, 
                         user_id: str) -> bool:
        """Submit corrected transcript and learn from corrections"""
        try:
            session = self.get_dictation_session(session_id)
            if not session:
                return False
            
            # Update session with corrected transcript
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE dictation_sessions 
                SET corrected_transcript = ?, status = 'corrected', updated_at = ?
                WHERE session_id = ?
            ''', (corrected_transcript, datetime.now().isoformat(), session_id))
            
            # Learn from corrections
            if session.raw_transcript and corrected_transcript:
                self._learn_from_correction(session.raw_transcript, corrected_transcript, user_id)
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Correction submitted for session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to submit correction for session {session_id}: {e}")
            return False
    
    def _learn_from_correction(self, original: str, corrected: str, user_id: str):
        """Learn from user corrections to improve future transcriptions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Store correction for learning
            cursor.execute('''
                INSERT OR REPLACE INTO correction_learning (
                    original_text, corrected_text, user_id, frequency, updated_at
                ) VALUES (?, ?, ?, 
                    COALESCE((SELECT frequency + 1 FROM correction_learning 
                             WHERE original_text = ? AND corrected_text = ?), 1),
                    ?)
            ''', (original, corrected, user_id, original, corrected, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to learn from correction: {e}")
    
    def get_dictation_session(self, session_id: str) -> Optional[DictationSession]:
        """Get dictation session by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM dictation_sessions WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return DictationSession(*row)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get dictation session {session_id}: {e}")
            return None
    
    def get_user_dictations(self, user_id: str, limit: int = 50) -> List[DictationSession]:
        """Get user's dictation sessions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM dictation_sessions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [DictationSession(*row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to get user dictations for {user_id}: {e}")
            return []
    
    def _update_session_status(self, session_id: str, status: str):
        """Update session status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE dictation_sessions 
                SET status = ?, updated_at = ?
                WHERE session_id = ?
            ''', (status, datetime.now().isoformat(), session_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update session status: {e}")
    
    def _update_session_transcript(self, session_id: str, transcript: str, confidence: float):
        """Update session with transcript"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE dictation_sessions 
                SET raw_transcript = ?, confidence_score = ?, status = 'transcribed', updated_at = ?
                WHERE session_id = ?
            ''', (transcript, confidence, datetime.now().isoformat(), session_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update session transcript: {e}")
    
    def get_dictation_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get dictation statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            where_clause = "WHERE user_id = ?" if user_id else ""
            params = [user_id] if user_id else []
            
            # Total sessions
            cursor.execute(f'SELECT COUNT(*) FROM dictation_sessions {where_clause}', params)
            total_sessions = cursor.fetchone()[0]
            
            # Sessions by status
            cursor.execute(f'''
                SELECT status, COUNT(*) FROM dictation_sessions {where_clause}
                GROUP BY status
            ''', params)
            sessions_by_status = dict(cursor.fetchall())
            
            # Average confidence
            cursor.execute(f'''
                SELECT AVG(confidence_score) FROM dictation_sessions 
                {where_clause} AND confidence_score IS NOT NULL
            ''', params)
            avg_confidence = cursor.fetchone()[0] or 0.0
            
            # Recent activity (last 7 days)
            cursor.execute(f'''
                SELECT COUNT(*) FROM dictation_sessions 
                {where_clause} {"AND" if where_clause else "WHERE"} 
                created_at > datetime('now', '-7 days')
            ''', params)
            recent_activity = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_sessions': total_sessions,
                'sessions_by_status': sessions_by_status,
                'average_confidence': round(avg_confidence, 2),
                'recent_activity_7d': recent_activity
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get dictation stats: {e}")
            return {}

# Global voice dictation instance
sa_voice_dictation = SouthAfricanVoiceDictation()