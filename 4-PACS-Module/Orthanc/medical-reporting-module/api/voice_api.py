"""Voice API for the Medical Reporting Module - Enhanced with Training and Security"""

import logging
import uuid
import tempfile
import os
import subprocess
import sys
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from pathlib import Path
from core.user_manager import require_auth, get_current_user_id
from core.secure_audio_handler import secure_audio_handler, store_training_audio, store_shortcut_audio

logger = logging.getLogger(__name__)

voice_bp = Blueprint("voice", __name__)

# Simple session storage
current_session = None
session_contexts = {}  # Store session transcription context
whisper_model = None  # Keep model loaded in memory
ffmpeg_available = None  # Cache FFmpeg availability
# Minimum webm size (bytes) to attempt ffmpeg conversion - tiny browser
# chunks often fail; treat them as raw bytes for matching/shortcut storage.
MIN_WEBM_CONVERT_BYTES = 16000

# Training and shortcuts instances
training_engines = {}  # user_id -> MedicalTrainingEngine
voice_matchers = {}    # user_id -> VoicePatternMatcher




def check_ffmpeg_availability():
    """Check if FFmpeg is available and install if needed"""
    global ffmpeg_available
    
    if ffmpeg_available is not None:
        return ffmpeg_available
    
    try:
        # Check if FFmpeg is in PATH
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("✅ FFmpeg found in PATH")
            ffmpeg_available = True
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    
    # Check local ffmpeg directory
    local_ffmpeg = Path("ffmpeg/ffmpeg.exe")
    if local_ffmpeg.exists():
        # Add to PATH
        ffmpeg_dir = str(local_ffmpeg.parent.absolute())
        current_path = os.environ.get('PATH', '')
        if ffmpeg_dir not in current_path:
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + current_path
            logger.info(f"✅ Added local FFmpeg to PATH: {ffmpeg_dir}")
        
        ffmpeg_available = True
        return True
    
    logger.error("❌ FFmpeg not found - audio conversion will fail")
    logger.error("Run 'python install_ffmpeg.py' to install FFmpeg automatically")
    ffmpeg_available = False
    return False

def get_or_load_whisper_model():
    """Get Whisper model, loading it if necessary"""
    global whisper_model
    
    # Check FFmpeg first
    if not check_ffmpeg_availability():
        logger.error("FFmpeg not available - Whisper will fail on audio files")
        return None
    
    if whisper_model is None:
        try:
            import whisper
            logger.info("Loading Whisper model into memory...")
            whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except ImportError:
            logger.error("Whisper not available - install with: pip install openai-whisper")
            return None
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return None
    return whisper_model


@voice_bp.route("/session/start", methods=["POST"])
def start_voice_session():
    """Start a new voice dictation session"""
    try:
        global current_session, session_contexts
        data = request.get_json() or {}
        
        # Get authenticated user ID
        user_id = get_current_user_id()
        
        session_id = str(uuid.uuid4())
        current_session = {
            "session_id": session_id,
            "user_id": user_id,
            "state": "active",
            "start_time": datetime.utcnow().isoformat(),
            "report_id": data.get("report_id"),
            "template_id": data.get("template_id")
        }
        
        # Initialize session context
        session_contexts[session_id] = {
            "chunks": [],
            "full_transcription": "",
            "medical_context": [],
            "last_processed_chunk": -1
        }
        
        # Pre-load Whisper model for faster processing
        get_or_load_whisper_model()
        
        logger.info(f"Started voice session {session_id}")
        return jsonify({"session": current_session}), 201
        
    except Exception as e:
        logger.error(f"Failed to start voice session: {e}")
        return jsonify({"error": "Failed to start voice session"}), 500


@voice_bp.route("/session/end", methods=["POST"])
def end_voice_session():
    """End the current voice session"""
    try:
        global current_session, session_contexts
        
        if not current_session:
            return jsonify({"error": "No active voice session"}), 400
        
        session_id = current_session["session_id"]
        current_session["end_time"] = datetime.utcnow().isoformat()
        current_session["state"] = "ended"
        
        session_data = current_session.copy()
        
        # Add final transcription to session data
        if session_id in session_contexts:
            session_data["final_transcription"] = session_contexts[session_id]["full_transcription"]
            session_data["total_chunks"] = len(session_contexts[session_id]["chunks"])
            
            # Clean up session context after some time (optional)
            # For now, keep it for debugging
        
        current_session = None
        
        logger.info(f"Ended voice session {session_id}")
        return jsonify({"session": session_data})
        
    except Exception as e:
        logger.error(f"Failed to end voice session: {e}")
        return jsonify({"error": "Failed to end voice session"}), 500


@voice_bp.route("/session/status", methods=["GET"])
def get_session_status():
    """Get current voice session status"""
    try:
        global current_session
        
        if current_session:
            return jsonify({"active": True, "session": current_session})
        else:
            return jsonify({"active": False, "session": None})
            
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        return jsonify({"error": "Failed to get session status"}), 500


@voice_bp.route("/transcribe-chunk", methods=["POST"])
def transcribe_chunk():
    """Transcribe audio chunk for real-time processing"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if not audio_file or audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Get chunk metadata
        session_id = request.form.get('session_id', 'demo')
        chunk_id = request.form.get('chunk_id', str(uuid.uuid4()))
        sequence_number = int(request.form.get('sequence_number', 0))
        
        # Get session context
        session_context = session_contexts.get(session_id, {
            "chunks": [],
            "full_transcription": "",
            "medical_context": [],
            "last_processed_chunk": -1
        })
        
        # Check for duplicate chunks
        existing_chunk = next((c for c in session_context["chunks"] if c["chunk_id"] == chunk_id), None)
        if existing_chunk:
            logger.info(f"Duplicate chunk {chunk_id}, returning cached result")
            return jsonify(existing_chunk["result"])
        
        # Process audio chunk
        start_time = datetime.utcnow()
        
        # Get user ID for secure storage
        user_id = get_current_user_id()
        
        # Save audio temporarily - detect format from filename
        file_extension = '.webm'  # Default for browser recordings
        if audio_file.filename:
            if audio_file.filename.endswith('.webm'):
                file_extension = '.webm'
            elif audio_file.filename.endswith('.wav'):
                file_extension = '.wav'
            elif audio_file.filename.endswith('.mp3'):
                file_extension = '.mp3'
        
        # Create temporary file with proper extension
        temp_fd, temp_audio_path = tempfile.mkstemp(suffix=file_extension)
        
        try:
            # Close the file descriptor first
            os.close(temp_fd)
            
            # Save the uploaded file to temporary location
            audio_file.save(temp_audio_path)
            
            # Store audio securely for processing
            audio_storage = secure_audio_handler.store_audio_securely(
                temp_audio_path, user_id, "transcription"
            )
            
            file_size = os.path.getsize(temp_audio_path)
            logger.info(f"Processing chunk {chunk_id}: {file_size} bytes")
            
            if file_size == 0:
                result = {
                    'success': True,
                    'chunk_id': chunk_id,
                    'transcription': '',
                    'confidence': 0.0,
                    'processing_time': 0,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                # For chunk uploads, defer full transcription for WebM/other streamed chunks.
                # We store the encrypted file and return an immediate success with file id.
                if file_extension == '.webm':
                    result = {
                        'success': True,
                        'chunk_id': chunk_id,
                        'transcription': '',
                        'deferred': True,
                        'file_id': audio_storage['file_id'] if audio_storage and isinstance(audio_storage, dict) else None,
                        'processing_time': (datetime.utcnow() - start_time).total_seconds(),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    logger.info(f"Deferred transcription for WebM chunk {chunk_id}, stored as {result['file_id']}")
                else:
                    # Non-webm (wav/mp3) - perform immediate transcription as before
                    model = get_or_load_whisper_model()
                    if not model:
                        return jsonify({
                            'success': False,
                            'error': 'Speech recognition not available',
                            'chunk_id': chunk_id,
                            'timestamp': datetime.utcnow().isoformat()
                        }), 500

                    try:
                        transcribe_start = datetime.utcnow()
                        if not os.path.exists(temp_audio_path):
                            raise FileNotFoundError(f"Temporary audio file not found: {temp_audio_path}")

                        if file_extension in ('.wav', '.mp3'):
                            whisper_result = model.transcribe(temp_audio_path, language="en")
                        else:
                            audio_data = convert_webm_to_numpy(temp_audio_path)
                            whisper_result = model.transcribe(audio_data, language="en") if len(audio_data) > 0 else {"text": ""}

                        transcription = whisper_result.get('text', '').strip()
                        processing_time = (datetime.utcnow() - start_time).total_seconds()

                        enhanced_transcription = enhance_sa_medical_text(transcription, session_context.get("medical_context", []))
                        try:
                            from core.medical_stt_enhancer import MedicalSTTEnhancer
                            enhancer = MedicalSTTEnhancer(model)
                            enhanced_transcription = enhancer.enhance_transcription_with_training(enhanced_transcription, user_id=user_id)
                        except Exception as e:
                            logger.error(f"Training enhancement failed: {e}")

                        result = {
                            'success': True,
                            'chunk_id': chunk_id,
                            'transcription': enhanced_transcription,
                            'confidence': 0.90,
                            'processing_time': processing_time,
                            'medical_terms_enhanced': transcription != enhanced_transcription,
                            'timestamp': datetime.utcnow().isoformat(),
                            'file_id': audio_storage['file_id'] if audio_storage and isinstance(audio_storage, dict) else None
                        }

                        logger.info(f"Chunk {chunk_id} transcribed: '{enhanced_transcription}' ({processing_time:.2f}s)")

                    except Exception as process_error:
                        import traceback
                        error_details = traceback.format_exc()
                        logger.error(f"Chunk processing failed: {process_error}")
                        logger.error(f"Full traceback: {error_details}")
                        result = {
                            'success': False,
                            'error': f'Audio processing failed: {str(process_error)}',
                            'chunk_id': chunk_id,
                            'timestamp': datetime.utcnow().isoformat(),
                            'debug_info': {
                                'file_path': temp_audio_path,
                                'file_exists': os.path.exists(temp_audio_path),
                                'file_size': file_size,
                                'file_extension': file_extension
                            }
                        }
            
            # Store chunk result and file id in session context
            chunk_record = {
                "chunk_id": chunk_id,
                "sequence_number": sequence_number,
                "timestamp": start_time.isoformat(),
                "result": result,
                # include stored audio file id (if stored)
                "file_id": audio_storage['file_id'] if audio_storage and isinstance(audio_storage, dict) and audio_storage.get('file_id') else None,
                "user_id": user_id,
                }

                # If this was a non-WAV/MP3 chunk we intentionally do not run Whisper here
            # to avoid frequent FFmpeg failures for short/partial WebM segments. We
            # process all stored chunks at session finalization time instead.
            session_context["chunks"].append(chunk_record)
            
            # Update full transcription if successful
            if result.get('success') and result.get('transcription'):
                if session_context["full_transcription"]:
                    session_context["full_transcription"] += " " + result['transcription']
                else:
                    session_context["full_transcription"] = result['transcription']
                
                # Update medical context
                medical_terms = extract_medical_terms(result['transcription'])
                session_context["medical_context"].extend(medical_terms)
            
            session_context["last_processed_chunk"] = sequence_number
            session_contexts[session_id] = session_context
            
            return jsonify(result)
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_audio_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Chunk transcription error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to transcribe audio chunk',
            'timestamp': datetime.utcnow().isoformat()
        }), 500


def enhance_sa_medical_text(text, medical_context=None):
    """Enhance text with South African medical terminology"""
    if not text:
        return text
    
    # SA medical term replacements
    sa_replacements = {
        'tb': 'tuberculosis',
        'mva': 'motor vehicle accident',
        'gsw': 'gunshot wound',
        'pcp': 'Pneumocystis pneumonia',
        'hiv': 'HIV',
        'aids': 'AIDS',
        'chest xray': 'chest X-ray',
        'x ray': 'X-ray',
        'ct scan': 'CT scan',
        'mri scan': 'MRI scan',
        'bp': 'blood pressure',
        'hr': 'heart rate',
        'rr': 'respiratory rate',
        'temp': 'temperature',
        'o2 sat': 'oxygen saturation',
        'ecg': 'ECG',
        'ekg': 'ECG',
        'cxr': 'chest X-ray',
        'abd': 'abdomen',
        'cvs': 'cardiovascular system',
        'rs': 'respiratory system',
        'cns': 'central nervous system',
        'ent': 'ear, nose and throat',
        'gi': 'gastrointestinal',
        'gu': 'genitourinary'
    }
    
    # Context-aware abbreviation expansion
    context_expansions = {
        'dm': 'diabetes mellitus' if medical_context and any('diabetes' in term.lower() for term in medical_context) else 'dm',
        'htn': 'hypertension' if medical_context and any('blood pressure' in term.lower() or 'hypertension' in term.lower() for term in medical_context) else 'htn',
        'mi': 'myocardial infarction' if medical_context and any('heart' in term.lower() or 'cardiac' in term.lower() for term in medical_context) else 'mi',
        'copd': 'chronic obstructive pulmonary disease' if medical_context and any('lung' in term.lower() or 'respiratory' in term.lower() for term in medical_context) else 'copd',
        'uti': 'urinary tract infection' if medical_context and any('urinary' in term.lower() or 'bladder' in term.lower() for term in medical_context) else 'uti'
    }
    
    enhanced = text.lower()
    
    # Apply basic replacements
    for term, replacement in sa_replacements.items():
        import re
        pattern = r'\b' + re.escape(term) + r'\b'
        enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
    
    # Apply context-aware replacements
    for term, replacement in context_expansions.items():
        import re
        pattern = r'\b' + re.escape(term) + r'\b'
        enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
    
    # South African specific medical terms
    sa_specific_terms = {
        'clinic sister': 'clinic sister',  # Keep as is - SA specific
        'community health worker': 'community health worker',
        'traditional healer': 'traditional healer',
        'sangoma': 'traditional healer (sangoma)',
        'muti': 'traditional medicine (muti)'
    }
    
    for term, replacement in sa_specific_terms.items():
        import re
        pattern = r'\b' + re.escape(term) + r'\b'
        enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
    
    # Capitalize first letter of sentences
    import re
    enhanced = re.sub(r'(^|[.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), enhanced)
    
    return enhanced


def convert_audio_to_wav(input_path, output_path):
    """Convert audio file to WAV format using FFmpeg"""
    try:
        if not check_ffmpeg_availability():
            raise Exception("FFmpeg not available for audio conversion")
        
        # Use FFmpeg to convert to WAV with proper settings for Whisper
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',      # Mono
            '-c:a', 'pcm_s16le',  # 16-bit PCM
            '-y',            # Overwrite output
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"✅ Audio converted to WAV: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg conversion failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg conversion timed out")
        return False
    except Exception as e:
        logger.error(f"Audio conversion error: {e}")
        return False

def convert_webm_to_numpy(webm_path):
    """Convert WebM audio to numpy array using FFmpeg"""
    try:
        # Quick size guard: tiny browser-generated WebM chunks are often
        # incomplete and will cause FFmpeg to fail when attempting to
        # parse/convert them. Avoid calling FFmpeg for very small files.
        try:
            file_size = os.path.getsize(webm_path)
            if file_size < MIN_WEBM_CONVERT_BYTES:
                logger.warning(f"WebM file too small for conversion ({file_size} bytes) -> skipping FFmpeg")
                import numpy as np
                return np.array([], dtype=np.float32)
        except Exception:
            # If we cannot stat the file, proceed and let FFmpeg fail
            pass
        import numpy as np
        
        # First try to convert to WAV using FFmpeg
        temp_wav_fd, temp_wav_path = tempfile.mkstemp(suffix='.wav')
        os.close(temp_wav_fd)
        
        try:
            if convert_audio_to_wav(webm_path, temp_wav_path):
                # Now read the WAV file with soundfile
                try:
                    import soundfile as sf
                    audio_data, sample_rate = sf.read(temp_wav_path)
                    logger.info(f"Successfully converted WebM to numpy: {len(audio_data)} samples at {sample_rate}Hz")
                    
                    # Ensure float32 format
                    return audio_data.astype(np.float32)
                    
                except Exception as sf_error:
                    logger.error(f"Failed to read converted WAV: {sf_error}")
                    
        finally:
            # Clean up temp WAV file
            try:
                os.unlink(temp_wav_path)
            except:
                pass
        
        # If FFmpeg conversion failed, return empty audio
        logger.error("WebM conversion failed - returning empty audio")
        return np.array([], dtype=np.float32)
        
    except Exception as e:
        logger.error(f"Failed to convert WebM to numpy: {e}")
        import numpy as np
        return np.array([], dtype=np.float32)


def extract_medical_terms(text):
    """Extract medical terms from text for context"""
    medical_terms = []
    common_medical_words = [
        'tuberculosis', 'pneumonia', 'hypertension', 'diabetes', 'HIV', 'AIDS',
        'chest X-ray', 'CT scan', 'MRI', 'ECG', 'blood pressure', 'heart rate',
        'respiratory', 'cardiovascular', 'gastrointestinal', 'neurological'
    ]
    
    text_lower = text.lower()
    for term in common_medical_words:
        if term.lower() in text_lower:
            medical_terms.append(term)
    
    return medical_terms


@voice_bp.route("/session/<session_id>/context", methods=["GET"])
def get_session_context(session_id):
    """Get session transcription context"""
    try:
        context = session_contexts.get(session_id)
        if not context:
            return jsonify({"error": "Session not found"}), 404
        
        return jsonify({
            "session_id": session_id,
            "context": context
        })
        
    except Exception as e:
        logger.error(f"Failed to get session context: {e}")
        return jsonify({"error": "Failed to get session context"}), 500


@voice_bp.route("/session/<session_id>/finalize", methods=["POST"])
def finalize_session_transcription(session_id):
    """Perform final pass optimization on complete session transcription"""
    try:
        context = session_contexts.get(session_id)
        if not context:
            return jsonify({"error": "Session not found"}), 404
        
        # If we already have a final transcription, return it
        full_text = context.get("final_transcription") or context.get("full_transcription", "")
        if context.get("final_transcription"):
            return jsonify({
                "success": True,
                "final_transcription": context.get("final_transcription"),
                "improvements": context.get("improvements", [])
            })

        # If there is no accumulated transcription, try to assemble stored audio chunks
        if not full_text:
            logger.info(f"No full transcription in session {session_id}; attempting to assemble audio chunks for final transcription")
            assembled_wav = assemble_session_audio(session_id)
            if assembled_wav:
                try:
                    model = get_or_load_whisper_model()
                    if model:
                        result = model.transcribe(assembled_wav, language="en")
                        full_text = result.get('text', '').strip()
                        # Clean up assembled file
                        try:
                            os.unlink(assembled_wav)
                        except:
                            pass
                    else:
                        logger.error("Whisper model not available for final transcription")
                except Exception as e:
                    logger.error(f"Final transcription failed: {e}")
        
        # Perform final medical terminology pass
        medical_context = context.get("medical_context", [])
        final_enhanced = enhance_sa_medical_text(full_text, medical_context)
        
        # Additional final pass improvements
        improvements = []
        
        # Fix common transcription issues
        final_enhanced = apply_final_corrections(final_enhanced, improvements)
        
        # Update session context
        context["final_transcription"] = final_enhanced
        context["improvements"] = improvements
        session_contexts[session_id] = context
        
        logger.info(f"Finalized session {session_id} transcription with {len(improvements)} improvements")
        
        return jsonify({
            "success": True,
            "final_transcription": final_enhanced,
            "improvements": improvements,
            "original_length": len(full_text),
            "final_length": len(final_enhanced)
        })
        
    except Exception as e:
        logger.error(f"Failed to finalize session transcription: {e}")
        return jsonify({"error": "Failed to finalize transcription"}), 500


def apply_final_corrections(text, improvements_list):
    """Apply final corrections to improve transcription accuracy"""
    corrected = text
    
    # Common medical transcription corrections
    corrections = [
        # Fix common misheard medical terms
        (r'\bpatient has\b', 'patient has'),
        (r'\bblood pressure is\b', 'blood pressure is'),
        (r'\bchest examination\b', 'chest examination'),
        (r'\babdomen is\b', 'abdomen is'),
        (r'\bheart sounds\b', 'heart sounds'),
        (r'\bbreath sounds\b', 'breath sounds'),
        
        # Fix punctuation around medical terms
        (r'(\d+)\s*over\s*(\d+)', r'\1/\2'),  # Blood pressure format
        (r'(\d+)\s*degrees\s*celsius', r'\1°C'),  # Temperature format
        (r'(\d+)\s*percent', r'\1%'),  # Percentage format
        
        # Ensure proper sentence structure
        (r'\.(\s+[a-z])', lambda m: '. ' + m.group(1).upper()),  # Capitalize after periods
        (r'\s+', ' '),  # Remove extra spaces
        (r'^\s+|\s+$', ''),  # Trim whitespace
    ]
    
    import re
    for pattern, replacement in corrections:
        old_text = corrected
        if callable(replacement):
            corrected = re.sub(pattern, replacement, corrected)
        else:
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        if old_text != corrected:
            improvements_list.append({
                "type": "correction",
                "pattern": pattern if isinstance(pattern, str) else "function",
                "description": "Applied medical transcription correction"
            })
    
    return corrected


def assemble_session_audio(session_id):
    """Retrieve stored encrypted chunk files for a session, assemble them into a single WAV and return its path.

    Returns path to WAV file or None on failure.
    """
    try:
        context = session_contexts.get(session_id)
        if not context:
            logger.error(f"No session context found for {session_id}")
            return None

        parts = [(c.get('file_id'), c.get('user_id')) for c in context.get('chunks', []) if c.get('file_id')]
        if not parts:
            logger.info(f"No stored chunk files for session {session_id}")
            return None

        temp_parts = []
        try:
            # Retrieve each encrypted audio, write to temp file
            for fid, uid in parts:
                user_for_file = uid or context.get('user_id', 'demo')
                retrieved = secure_audio_handler.retrieve_audio_securely(fid, user_for_file)
                if not retrieved or not retrieved.get('data'):
                    logger.warning(f"Failed to retrieve audio for file_id {fid}")
                    continue

                # Write decrypted bytes to temp WebM (or try WAV suffix)
                temp_fd, temp_path = tempfile.mkstemp(suffix='.webm')
                os.close(temp_fd)
                with open(temp_path, 'wb') as f:
                    f.write(retrieved['data'])
                temp_parts.append(temp_path)

            if not temp_parts:
                logger.error(f"No valid audio parts available for session {session_id}")
                return None

            # Create a concat list for ffmpeg
            list_fd, list_path = tempfile.mkstemp(suffix='.txt')
            os.close(list_fd)
            with open(list_path, 'w', encoding='utf-8') as lf:
                for p in temp_parts:
                    lf.write(f"file '{p.replace('\\', '/')}'\n")

            # Output WAV path
            out_fd, out_wav = tempfile.mkstemp(suffix='.wav')
            os.close(out_fd)

            # Run ffmpeg concat and conversion
            cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_path,
                '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', out_wav
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            try:
                os.unlink(list_path)
            except:
                pass

            if result.returncode != 0:
                logger.error(f"FFmpeg concat failed: {result.stderr}")
                # Clean up parts
                for p in temp_parts:
                    try:
                        os.unlink(p)
                    except:
                        pass
                try:
                    os.unlink(out_wav)
                except:
                    pass
                return None

            # Clean up part files, keep the out_wav for Whisper
            for p in temp_parts:
                try:
                    os.unlink(p)
                except:
                    pass

            logger.info(f"Assembled session audio to {out_wav}")
            return out_wav

        except Exception as e:
            logger.error(f"Failed to assemble session audio: {e}")
            for p in temp_parts:
                try:
                    os.unlink(p)
                except:
                    pass
            return None

    except Exception as e:
        logger.error(f"assemble_session_audio error: {e}")
        return None


@voice_bp.route("/transcribe", methods=["POST"])
def transcribe_audio():
    """Transcribe uploaded audio"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if not audio_file or audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Determine file extension based on content type or filename
        file_extension = '.webm'  # Default for browser recordings
        if audio_file.content_type:
            if 'wav' in audio_file.content_type:
                file_extension = '.wav'
            elif 'mp3' in audio_file.content_type:
                file_extension = '.mp3'
            elif 'webm' in audio_file.content_type:
                file_extension = '.webm'
        
        # Save audio temporarily with correct extension
        temp_fd, temp_audio_path = tempfile.mkstemp(suffix=file_extension)
        try:
            # Close the file descriptor first
            os.close(temp_fd)
            
            # Save the uploaded file to temporary location
            audio_file.save(temp_audio_path)
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")
            try:
                os.unlink(temp_audio_path)
            except:
                pass
            return jsonify({'error': 'Failed to save audio file'}), 500
        
        try:
            # Verify file exists and has content
            if not os.path.exists(temp_audio_path):
                logger.error(f"Temp file not found: {temp_audio_path}")
                return jsonify({'error': 'Audio file processing failed'}), 500
            
            file_size = os.path.getsize(temp_audio_path)
            logger.info(f"Processing audio file: {temp_audio_path} ({file_size} bytes)")
            
            if file_size == 0:
                logger.warning("Empty audio file received")
                return jsonify({
                    'success': True,
                    'transcription': '',
                    'message': 'Empty audio file',
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Try to use Whisper if available
            try:
                # Use cached model instead of loading fresh each time
                model = get_or_load_whisper_model()
                if not model:
                    return jsonify({
                        'success': False,
                        'error': 'Speech recognition not available',
                        'timestamp': datetime.utcnow().isoformat()
                    }), 500
                
                # Audio file is ready for processing
                processed_audio_path = temp_audio_path
                
                # Process audio with Whisper
                try:
                    logger.info(f"Processing audio file: {temp_audio_path}")
                    
                    # Verify file exists and is readable
                    if not os.path.exists(temp_audio_path):
                        raise FileNotFoundError(f"Temporary audio file not found: {temp_audio_path}")
                    
                    # Process audio with Whisper - prefer direct file processing for WAV/MP3
                    if file_extension == '.wav' or file_extension == '.mp3':
                        # For WAV/MP3, let Whisper handle directly (most reliable)
                        result = model.transcribe(temp_audio_path, language="en")
                    else:
                        # For other formats (WebM), try numpy conversion as fallback
                        audio_data = convert_webm_to_numpy(temp_audio_path)
                        if len(audio_data) > 0:
                            result = model.transcribe(audio_data, language="en")
                        else:
                            # If conversion failed, return empty result
                            result = {"text": ""}
                    
                    transcription = result["text"].strip()
                    logger.info(f"Transcription completed: {len(transcription)} characters")
                    
                except Exception as load_error:
                    logger.error(f"Audio processing failed: {load_error}")
                    return jsonify({
                        'success': False,
                        'error': f'Audio processing failed: {str(load_error)}',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                
                # No need to clean up converted file since we use temp_audio_path directly
                
                if transcription:
                    logger.info(f"Transcribed: {transcription}")
                    return jsonify({
                        'success': True,
                        'transcription': transcription,
                        'timestamp': datetime.utcnow().isoformat(),
                        'confidence': 0.90
                    })
                else:
                    return jsonify({
                        'success': True,
                        'transcription': '',
                        'message': 'No speech detected',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
            except ImportError:
                logger.warning("Whisper not available")
                return jsonify({
                    'success': False,
                    'error': 'Speech recognition not available',
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as whisper_error:
                logger.error(f"Whisper processing error: {whisper_error}")
                return jsonify({
                    'success': False,
                    'error': f'Speech recognition failed: {str(whisper_error)}',
                    'timestamp': datetime.utcnow().isoformat()
                })
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_audio_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({'error': 'Failed to transcribe audio'}), 500


# Basic status endpoint
@voice_bp.route("/status", methods=["GET"])
def voice_status():
    """Get voice system status"""
    try:
        return jsonify({
            "status": "active",
            "whisper_available": True,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Voice status error: {e}")
        return jsonify({"error": "Failed to get voice status"}), 500
# ============================================================================
# MEDICAL TRAINING API ENDPOINTS
# ============================================================================

def get_training_engine(user_id="demo_user"):
    """Get or create training engine for user"""
    global training_engines
    
    if user_id not in training_engines:
        model = get_or_load_whisper_model()
        if model:
            from core.training_engine import MedicalTrainingEngine
            training_engines[user_id] = MedicalTrainingEngine(model, user_id)
    
    return training_engines.get(user_id)

def get_voice_matcher(user_id="demo_user"):
    """Get or create voice matcher for user"""
    global voice_matchers
    
    if user_id not in voice_matchers:
        from core.voice_matcher import VoicePatternMatcher
        voice_matchers[user_id] = VoicePatternMatcher(user_id)
    
    return voice_matchers.get(user_id)

@voice_bp.route("/training/categories", methods=["GET"])
def get_training_categories():
    """Get medical term categories for training"""
    try:
        user_id = request.args.get('user_id', 'demo_user')
        training_engine = get_training_engine(user_id)
        
        if not training_engine:
            return jsonify({'error': 'Training engine not available'}), 500
        
        categories = training_engine.get_training_categories()
        
        return jsonify({
            'success': True,
            'categories': categories
        })
        
    except Exception as e:
        logger.error(f"Failed to get training categories: {e}")
        return jsonify({'error': 'Failed to get training categories'}), 500

@voice_bp.route("/training/terms/<category>", methods=["GET"])
def get_category_terms(category):
    """Get terms for a specific category"""
    try:
        user_id = request.args.get('user_id', 'demo_user')
        training_engine = get_training_engine(user_id)
        
        if not training_engine:
            return jsonify({'error': 'Training engine not available'}), 500
        
        terms = training_engine.get_terms_for_category(category)
        
        return jsonify({
            'success': True,
            'category': category,
            'terms': terms
        })
        
    except Exception as e:
        logger.error(f"Failed to get category terms: {e}")
        return jsonify({'error': 'Failed to get category terms'}), 500

# Removed duplicate routes - using secure versions below


# Training API Endpoints with Security

@voice_bp.route("/training/start", methods=["POST"])
@require_auth
def start_secure_training_session():
    """Start medical terminology training session"""
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        
        category = data.get('category', 'general')
        
        # Get training engine for user
        from core.training_engine import MedicalTrainingEngine
        if user_id not in training_engines:
            training_engines[user_id] = MedicalTrainingEngine(get_or_load_whisper_model(), user_id)
        
        training_engine = training_engines[user_id]
        
        # Get terms for category
        terms = training_engine.get_training_categories().get(category, [])
        
        return jsonify({
            "success": True,
            "category": category,
            "terms": terms,
            "session_id": str(uuid.uuid4())
        })
        
    except Exception as e:
        logger.error(f"Training session start error: {e}")
        return jsonify({"error": "Failed to start training session"}), 500

@voice_bp.route("/training/record", methods=["POST"])
@require_auth
def record_secure_training_audio():
    """Record training audio for medical term"""
    try:
        user_id = get_current_user_id()
        
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        medical_term = request.form.get('medical_term', '')
        category = request.form.get('category', 'general')
        
        if not medical_term:
            return jsonify({'error': 'Medical term required'}), 400
        
        # Save audio securely
        temp_fd, temp_path = tempfile.mkstemp(suffix='.webm')
        try:
            os.close(temp_fd)
            audio_file.save(temp_path)
            
            # Store encrypted audio
            audio_storage = store_training_audio(temp_path, user_id)
            if not audio_storage:
                return jsonify({'error': 'Failed to store audio securely'}), 500
            
            # Process with training engine
            from core.training_engine import MedicalTrainingEngine
            if user_id not in training_engines:
                training_engines[user_id] = MedicalTrainingEngine(get_or_load_whisper_model(), user_id)
            
            training_engine = training_engines[user_id]
            
            # Process training audio
            result = training_engine.process_training_audio(temp_path, medical_term, category)
            
            return jsonify({
                "success": True,
                "medical_term": medical_term,
                "category": category,
                "accuracy_score": result.get('accuracy_score', 0.0),
                "feedback": result.get('feedback', ''),
                "audio_id": audio_storage['file_id']
            })
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Training recording error: {e}")
        return jsonify({"error": "Failed to record training audio"}), 500

@voice_bp.route("/training/progress", methods=["GET"])
@require_auth
def get_secure_training_progress():
    """Get user's training progress"""
    try:
        user_id = get_current_user_id()
        
        from models.training_data import TrainingDataStore
        training_store = TrainingDataStore(user_id)
        
        progress = training_store.get_user_training_progress()
        problematic_terms = training_store.get_problematic_terms()
        
        return jsonify({
            "success": True,
            "progress": progress,
            "problematic_terms": problematic_terms
        })
        
    except Exception as e:
        logger.error(f"Training progress error: {e}")
        return jsonify({"error": "Failed to get training progress"}), 500

@voice_bp.route("/shortcuts/create", methods=["POST"])
@require_auth
def create_secure_voice_shortcut():
    """Create new voice shortcut"""
    try:
        user_id = get_current_user_id()
        
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        shortcut_name = request.form.get('name', '')
        template_id = request.form.get('template_id', '')
        template_content = request.form.get('template_content', '')
        
        if not shortcut_name:
            return jsonify({'error': 'Shortcut name required'}), 400

        # Save audio securely
        temp_fd, temp_path = tempfile.mkstemp(suffix='.webm')
        try:
            os.close(temp_fd)
            audio_file.save(temp_path)

            # Reject very small uploads which are likely partial browser
            # chunks; require a minimum size for creating a reliable
            # shortcut audio sample.
            try:
                sz = os.path.getsize(temp_path)
                if sz < MIN_WEBM_CONVERT_BYTES:
                    logger.warning(f"Shortcut creation failed: uploaded audio too small ({sz} bytes)")
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    return jsonify({'success': False, 'error': 'Uploaded audio too short for creating a shortcut'}), 400
            except Exception:
                # If size check can't be performed, continue cautiously
                pass
            
            # Store encrypted audio
            audio_storage = store_shortcut_audio(temp_path, user_id)
            if not audio_storage:
                return jsonify({'error': 'Failed to store audio securely'}), 500
            
            # Process with voice matcher - convert WebM to numpy first to avoid
            # passing a file path string into the matcher (which expects bytes/arrays)
            from core.voice_matcher import VoicePatternMatcher
            if user_id not in voice_matchers:
                voice_matchers[user_id] = VoicePatternMatcher(user_id)
            
            voice_matcher = voice_matchers[user_id]
            
            # For shortcuts we avoid server-side audio conversion and pass raw
            # bytes to the matcher. The matcher knows how to handle both raw
            # bytes and numpy arrays; passing bytes avoids FFmpeg/WEBM parsing
            # errors for short browser-generated segments.
            try:
                with open(temp_path, 'rb') as f:
                    audio_bytes = f.read()
            except Exception:
                audio_bytes = b''

            shortcut = voice_matcher.register_voice_shortcut(
                audio_bytes, shortcut_name, template_id, template_content
            )
            
            return jsonify({
                "success": True,
                "shortcut": {
                    "id": shortcut.id,
                    "name": shortcut_name,
                    "template_id": template_id,
                    "audio_id": audio_storage['file_id']
                }
            })
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Shortcut creation error: {e}")
        return jsonify({"error": "Failed to create voice shortcut"}), 500

@voice_bp.route("/shortcuts", methods=["GET"])
@require_auth
def get_secure_voice_shortcuts():
    """Get user's voice shortcuts"""
    try:
        user_id = get_current_user_id()
        
        from models.voice_shortcuts import VoiceShortcutStore
        shortcut_store = VoiceShortcutStore(user_id)
        
        shortcuts = shortcut_store.get_user_shortcuts()
        
        return jsonify({
            "success": True,
            "shortcuts": shortcuts
        })
        
    except Exception as e:
        logger.error(f"Shortcuts retrieval error: {e}")
        return jsonify({"error": "Failed to get voice shortcuts"}), 500

@voice_bp.route("/shortcuts/<int:shortcut_id>", methods=["DELETE"])
@require_auth
def delete_secure_voice_shortcut(shortcut_id):
    """Delete voice shortcut"""
    try:
        user_id = get_current_user_id()
        
        from models.voice_shortcuts import VoiceShortcutStore
        shortcut_store = VoiceShortcutStore(user_id)
        
        success = shortcut_store.delete_shortcut(shortcut_id)
        if not success:
            return jsonify({"error": "Shortcut not found"}), 404
        
        return jsonify({
            "success": True,
            "message": "Shortcut deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Shortcut deletion error: {e}")
        return jsonify({"error": "Failed to delete shortcut"}), 500

@voice_bp.route("/shortcuts/match", methods=["POST"])
@require_auth
def match_secure_voice_shortcut():
    """Match audio against voice shortcuts"""
    try:
        user_id = get_current_user_id()
        
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        
        # Save audio temporarily
        temp_fd, temp_path = tempfile.mkstemp(suffix='.webm')
        try:
            os.close(temp_fd)
            audio_file.save(temp_path)
            
            # Short-circuit very small uploads (common with browser chunking).
            # Tiny WebM fragments often cannot be parsed by FFmpeg and are
            # not useful for matching. Return no-match quickly.
            try:
                sz = os.path.getsize(temp_path)
                if sz < MIN_WEBM_CONVERT_BYTES:
                    logger.info(f"Short-circuiting shortcut match for tiny upload ({sz} bytes)")
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    return jsonify({
                        "success": True,
                        "match": {
                            "matched": False,
                            "confidence": 0.0,
                            "shortcut": None
                        }
                    })
            except Exception:
                pass

            # Match with voice matcher - convert audio to numpy first (preferred)
            from core.voice_matcher import VoicePatternMatcher
            if user_id not in voice_matchers:
                voice_matchers[user_id] = VoicePatternMatcher(user_id)
            
            voice_matcher = voice_matchers[user_id]
            
            # Avoid server-side conversion; pass raw bytes to matcher to avoid
            # FFmpeg/WebM parsing errors for short browser segments.
            try:
                with open(temp_path, 'rb') as f:
                    audio_bytes = f.read()
            except Exception:
                audio_bytes = b''

            match_result = voice_matcher.match_voice_command(audio_bytes)
            
            return jsonify({
                "success": True,
                "match": match_result
            })
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Shortcut matching error: {e}")
        return jsonify({"error": "Failed to match voice shortcut"}), 500

@voice_bp.route("/security/cleanup", methods=["POST"])
@require_auth
def cleanup_user_audio():
    """Clean up user's audio files"""
    try:
        user_id = get_current_user_id()
        
        # Get current stats
        stats_before = secure_audio_handler.get_user_audio_stats(user_id)
        
        # Run cleanup
        cleanup_count = secure_audio_handler.cleanup_expired_files()
        
        # Get updated stats
        stats_after = secure_audio_handler.get_user_audio_stats(user_id)
        
        return jsonify({
            "success": True,
            "cleanup_count": cleanup_count,
            "stats_before": stats_before,
            "stats_after": stats_after
        })
        
    except Exception as e:
        logger.error(f"Audio cleanup error: {e}")
        return jsonify({"error": "Failed to cleanup audio files"}), 500

@voice_bp.route("/security/stats", methods=["GET"])
@require_auth
def get_audio_security_stats():
    """Get audio security and storage statistics"""
    try:
        user_id = get_current_user_id()
        
        stats = secure_audio_handler.get_user_audio_stats(user_id)
        
        return jsonify({
            "success": True,
            "stats": stats,
            "retention_policy": {
                "audio_retention_hours": secure_audio_handler.retention_hours,
                "cleanup_interval_hours": secure_audio_handler.cleanup_interval.total_seconds() / 3600
            }
        })
        
    except Exception as e:
        logger.error(f"Security stats error: {e}")
        return jsonify({"error": "Failed to get security stats"}), 500
# ============================================================================
# DEMO ENDPOINTS (No Authentication Required)
# ============================================================================

@voice_bp.route("/shortcuts/demo", methods=["GET"])
def get_demo_voice_shortcuts():
    """Get demo voice shortcuts (no auth required)"""
    try:
        user_id = request.args.get('user_id', 'demo_user')
        
        # Return sample shortcuts for demo
        demo_shortcuts = [
            {
                'id': 1,
                'name': 'Consultation Template',
                'trigger_phrase': 'consultation note',
                'template_id': 'consultation',
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat()
            },
            {
                'id': 2,
                'name': 'Discharge Summary',
                'trigger_phrase': 'discharge summary',
                'template_id': 'discharge',
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat()
            }
        ]
        
        return jsonify({
            "success": True,
            "shortcuts": demo_shortcuts,
            "total": len(demo_shortcuts)
        })
        
    except Exception as e:
        logger.error(f"Demo shortcuts error: {e}")
        return jsonify({"error": "Failed to get demo shortcuts"}), 500

@voice_bp.route("/shortcuts/demo/match", methods=["POST"])
def match_demo_voice_shortcut():
    """Match audio against demo voice shortcuts (no auth required)"""
    try:
        user_id = request.form.get('user_id', 'demo_user')
        
        # For demo purposes, just return no match
        return jsonify({
            "success": True,
            "match": {
                "matched": False,
                "confidence": 0.0,
                "shortcut": None
            }
        })
        
    except Exception as e:
        logger.error(f"Demo shortcut matching error: {e}")
        return jsonify({"error": "Failed to match demo voice shortcut"}), 500

@voice_bp.route("/session/<session_id>/finalize", methods=["POST"])
def finalize_session(session_id):
    """Finalize a voice session and return final results"""
    try:
        global session_contexts
        
        # Get session context
        session_context = session_contexts.get(session_id, {})
        
        if not session_context:
            return jsonify({"error": "Session not found"}), 404
        
        # Return final transcription
        final_transcription = session_context.get("full_transcription", "")
        total_chunks = len(session_context.get("chunks", []))
        
        result = {
            "session_id": session_id,
            "status": "finalized",
            "final_transcription": final_transcription,
            "total_chunks": total_chunks,
            "finalized_at": datetime.utcnow().isoformat()
        }
        
        # Clean up session context
        if session_id in session_contexts:
            del session_contexts[session_id]
        
        logger.info(f"Finalized session {session_id} with {total_chunks} chunks")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to finalize session {session_id}: {e}")
        return jsonify({"error": "Failed to finalize session"}), 500


@voice_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for voice API"""
    return jsonify({
        "status": "healthy",
        "service": "voice_api",
        "whisper_loaded": whisper_model is not None,
        "ffmpeg_available": check_ffmpeg_availability(),
        "timestamp": datetime.utcnow().isoformat()
    })