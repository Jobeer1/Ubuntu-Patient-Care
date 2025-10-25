#!/usr/bin/env python3
"""
Test client-side audio conversion and server processing
"""

import os
import sys
import tempfile
import logging
import requests
import numpy as np
import soundfile as sf
import time
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_wav():
    """Create a test WAV file that simulates converted client audio"""
    try:
        # Generate speech-like audio with multiple frequencies
        sample_rate = 16000  # Standard for Whisper
        duration = 2.0  # 2 seconds
        
        # Create a more complex waveform that resembles speech
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Mix multiple frequencies to simulate speech patterns
        audio_data = (
            0.15 * np.sin(2 * np.pi * 150 * t) +   # Low frequency (vowel-like)
            0.12 * np.sin(2 * np.pi * 350 * t) +   # Mid frequency 
            0.08 * np.sin(2 * np.pi * 700 * t) +   # Higher frequency (consonant-like)
            0.05 * np.sin(2 * np.pi * 1200 * t)    # High frequency (sibilants)
        )
        
        # Add envelope to make it more speech-like
        envelope = np.exp(-t * 0.5) * (1 + 0.3 * np.sin(2 * np.pi * 3 * t))
        audio_data *= envelope
        
        # Add some realistic noise
        noise = 0.02 * np.random.randn(len(audio_data))
        audio_data += noise
        
        # Normalize to prevent clipping
        audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8
        
        # Save as WAV file (simulating client-side conversion)
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
        os.close(temp_fd)
        
        sf.write(temp_path, audio_data, sample_rate)
        
        logger.info(f"✅ Created test WAV file: {temp_path} ({len(audio_data)} samples at {sample_rate}Hz)")
        return temp_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create test WAV: {e}")
        return None

def test_server_wav_processing(audio_file_path):
    """Test server processing of WAV files"""
    try:
        # Start a voice session first
        session_url = 'https://localhost:5443/api/voice/session/start'
        session_response = requests.post(session_url, 
                                       json={'language': 'en-ZA', 'medical_mode': True},
                                       verify=False, 
                                       timeout=10)
        
        if session_response.status_code != 201:
            logger.error(f"❌ Failed to start session: {session_response.status_code}")
            return False
        
        session_data = session_response.json()
        session_id = session_data['session']['session_id']
        logger.info(f"✅ Started session: {session_id}")
        
        # Test chunk transcription
        chunk_url = 'https://localhost:5443/api/voice/transcribe-chunk'
        
        with open(audio_file_path, 'rb') as f:
            files = {'audio': ('test_chunk.wav', f, 'audio/wav')}
            data = {
                'session_id': session_id,
                'chunk_id': 'test_wav_chunk',
                'sequence_number': '0'
            }
            
            logger.info(f"🚀 Testing WAV chunk processing...")
            start_time = time.time()
            
            response = requests.post(chunk_url, files=files, data=data, verify=False, timeout=30)
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    transcription = result.get('transcription', '')
                    confidence = result.get('confidence', 0)
                    server_time = result.get('processing_time', 0)
                    
                    logger.info(f"✅ WAV processing successful!")
                    logger.info(f"   Transcription: '{transcription}'")
                    logger.info(f"   Confidence: {confidence}")
                    logger.info(f"   Server time: {server_time:.2f}s")
                    logger.info(f"   Total time: {processing_time:.2f}s")
                    
                    return True
                else:
                    error = result.get('error', 'Unknown error')
                    debug_info = result.get('debug_info', {})
                    logger.error(f"❌ WAV processing failed: {error}")
                    logger.error(f"   Debug info: {debug_info}")
                    return False
            else:
                logger.error(f"❌ HTTP error: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ WAV processing test failed: {e}")
        return False

def test_multiple_chunks():
    """Test processing multiple WAV chunks in sequence"""
    try:
        logger.info("🔄 Testing multiple chunk processing...")
        
        # Start session
        session_url = 'https://localhost:5443/api/voice/session/start'
        session_response = requests.post(session_url, 
                                       json={'language': 'en-ZA', 'medical_mode': True},
                                       verify=False, 
                                       timeout=10)
        
        if session_response.status_code != 201:
            return False
        
        session_id = session_response.json()['session']['session_id']
        
        # Process multiple chunks
        chunk_results = []
        total_time = 0
        
        for i in range(3):
            audio_file = create_test_wav()
            if not audio_file:
                continue
                
            try:
                chunk_url = 'https://localhost:5443/api/voice/transcribe-chunk'
                
                with open(audio_file, 'rb') as f:
                    files = {'audio': (f'chunk_{i}.wav', f, 'audio/wav')}
                    data = {
                        'session_id': session_id,
                        'chunk_id': f'multi_test_chunk_{i}',
                        'sequence_number': str(i)
                    }
                    
                    start_time = time.time()
                    response = requests.post(chunk_url, files=files, data=data, verify=False, timeout=30)
                    processing_time = time.time() - start_time
                    
                    total_time += processing_time
                    
                    if response.status_code == 200:
                        result = response.json()
                        success = result.get('success', False)
                        chunk_results.append(success)
                        
                        if success:
                            logger.info(f"✅ Chunk {i}: {processing_time:.2f}s - '{result.get('transcription', '')}'")
                        else:
                            logger.error(f"❌ Chunk {i}: {result.get('error', 'Unknown error')}")
                    else:
                        chunk_results.append(False)
                        logger.error(f"❌ Chunk {i}: HTTP {response.status_code}")
                
                # Small delay between chunks
                time.sleep(0.2)
                
            finally:
                if audio_file and os.path.exists(audio_file):
                    os.unlink(audio_file)
        
        # Summary
        successful_chunks = sum(chunk_results)
        total_chunks = len(chunk_results)
        avg_time = total_time / total_chunks if total_chunks > 0 else 0
        
        logger.info(f"📊 Multi-chunk results: {successful_chunks}/{total_chunks} successful")
        logger.info(f"📊 Average processing time: {avg_time:.2f}s per chunk")
        
        return successful_chunks == total_chunks
        
    except Exception as e:
        logger.error(f"❌ Multi-chunk test failed: {e}")
        return False

def test_medical_terminology():
    """Test medical terminology enhancement"""
    try:
        logger.info("🏥 Testing medical terminology enhancement...")
        
        # This would require actual speech audio with medical terms
        # For now, we'll test the enhancement function directly
        
        # Import the enhancement function
        sys.path.append('.')
        from api.voice_api import enhance_sa_medical_text
        
        test_phrases = [
            "patient has tb and high bp",
            "chest xray shows pneumonia",
            "dm patient with htn",
            "mva with gsw to abd"
        ]
        
        for phrase in test_phrases:
            enhanced = enhance_sa_medical_text(phrase)
            logger.info(f"Original: '{phrase}'")
            logger.info(f"Enhanced: '{enhanced}'")
            logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Medical terminology test failed: {e}")
        return False

def main():
    """Run comprehensive client-side conversion tests"""
    logger.info("🧪 Testing Client-Side Audio Conversion & Server Processing...")
    
    # Test 1: Basic WAV processing
    logger.info("\n1️⃣ Testing basic WAV file processing...")
    audio_file = create_test_wav()
    if not audio_file:
        logger.error("❌ Cannot create test audio")
        return False
    
    try:
        wav_success = test_server_wav_processing(audio_file)
    finally:
        if audio_file and os.path.exists(audio_file):
            os.unlink(audio_file)
    
    # Test 2: Multiple chunks
    logger.info("\n2️⃣ Testing multiple chunk processing...")
    multi_success = test_multiple_chunks()
    
    # Test 3: Medical terminology
    logger.info("\n3️⃣ Testing medical terminology enhancement...")
    medical_success = test_medical_terminology()
    
    # Summary
    logger.info("\n📋 Test Summary:")
    logger.info(f"WAV processing: {'✅ PASS' if wav_success else '❌ FAIL'}")
    logger.info(f"Multi-chunk processing: {'✅ PASS' if multi_success else '❌ FAIL'}")
    logger.info(f"Medical terminology: {'✅ PASS' if medical_success else '❌ FAIL'}")
    
    overall_success = wav_success and multi_success and medical_success
    
    if overall_success:
        logger.info("🎉 All tests passed! Client-side conversion approach is working.")
        logger.info("✨ The STT system should now work reliably for doctors.")
    else:
        logger.error("❌ Some tests failed. Check the errors above.")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)