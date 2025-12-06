#!/usr/bin/env python3
"""
Complete test of the STT fix - simulates real WebM chunks
"""

import os
import sys
import tempfile
import logging
import requests
import numpy as np
import soundfile as sf
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_webm_like_audio():
    """Create a test audio file that simulates WebM chunks"""
    try:
        # Generate speech-like audio (multiple tones)
        sample_rate = 16000
        duration = 1.5  # 1.5 seconds like real chunks
        
        # Create a more complex waveform that resembles speech
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Mix multiple frequencies to simulate speech
        audio_data = (
            0.1 * np.sin(2 * np.pi * 200 * t) +  # Low frequency
            0.1 * np.sin(2 * np.pi * 400 * t) +  # Mid frequency
            0.05 * np.sin(2 * np.pi * 800 * t)   # High frequency
        )
        
        # Add some noise to make it more realistic
        noise = 0.01 * np.random.randn(len(audio_data))
        audio_data += noise
        
        # Save as WAV file (browsers typically send WebM but we'll test with WAV first)
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
        os.close(temp_fd)
        
        sf.write(temp_path, audio_data, sample_rate)
        
        logger.info(f"✅ Created test audio chunk: {temp_path} ({len(audio_data)} samples)")
        return temp_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create test audio: {e}")
        return None

def test_voice_session():
    """Test starting a voice session"""
    try:
        url = 'https://localhost:5443/api/voice/session/start'
        
        response = requests.post(url, 
                               json={'language': 'en-ZA', 'medical_mode': True},
                               verify=False, 
                               timeout=10)
        
        if response.status_code == 201:
            data = response.json()
            session_id = data['session']['session_id']
            logger.info(f"✅ Voice session started: {session_id}")
            return session_id
        else:
            logger.error(f"❌ Session start failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Session test failed: {e}")
        return None

def test_chunk_transcription(session_id, audio_file_path, chunk_id):
    """Test chunk transcription"""
    try:
        url = 'https://localhost:5443/api/voice/transcribe-chunk'
        
        with open(audio_file_path, 'rb') as f:
            files = {'audio': (f'chunk_{chunk_id}.wav', f, 'audio/wav')}
            data = {
                'session_id': session_id,
                'chunk_id': f'test_chunk_{chunk_id}',
                'sequence_number': str(chunk_id)
            }
            
            logger.info(f"🚀 Testing chunk transcription: chunk_{chunk_id}")
            start_time = time.time()
            
            response = requests.post(url, files=files, data=data, verify=False, timeout=30)
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    transcription = result.get('transcription', '')
                    logger.info(f"✅ Chunk {chunk_id} processed in {processing_time:.2f}s: '{transcription}'")
                    return True, transcription, processing_time
                else:
                    error = result.get('error', 'Unknown error')
                    logger.error(f"❌ Chunk {chunk_id} failed: {error}")
                    return False, error, processing_time
            else:
                logger.error(f"❌ Chunk {chunk_id} HTTP error: {response.status_code} - {response.text}")
                return False, f"HTTP {response.status_code}", processing_time
                
    except Exception as e:
        logger.error(f"❌ Chunk transcription test failed: {e}")
        return False, str(e), 0

def test_session_finalization(session_id):
    """Test session finalization"""
    try:
        url = f'https://localhost:5443/api/voice/session/{session_id}/finalize'
        
        response = requests.post(url, verify=False, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                final_text = result.get('final_transcription', '')
                improvements = result.get('improvements', [])
                logger.info(f"✅ Session finalized: '{final_text}' ({len(improvements)} improvements)")
                return True
            else:
                logger.error(f"❌ Finalization failed: {result}")
                return False
        else:
            logger.error(f"❌ Finalization HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Finalization test failed: {e}")
        return False

def main():
    """Run complete STT test"""
    logger.info("🧪 Starting complete STT fix test...")
    
    # Test 1: Start voice session
    logger.info("\n1️⃣ Testing voice session start...")
    session_id = test_voice_session()
    if not session_id:
        logger.error("❌ Cannot proceed without session")
        return False
    
    # Test 2: Process multiple chunks
    logger.info("\n2️⃣ Testing chunk processing...")
    chunk_results = []
    total_processing_time = 0
    
    for i in range(3):  # Test 3 chunks
        audio_file = create_webm_like_audio()
        if not audio_file:
            continue
            
        try:
            success, result, processing_time = test_chunk_transcription(session_id, audio_file, i)
            chunk_results.append(success)
            total_processing_time += processing_time
            
            # Small delay between chunks (like real recording)
            time.sleep(0.5)
            
        finally:
            if audio_file and os.path.exists(audio_file):
                os.unlink(audio_file)
    
    # Test 3: Finalize session
    logger.info("\n3️⃣ Testing session finalization...")
    finalization_success = test_session_finalization(session_id)
    
    # Summary
    logger.info("\n📋 Complete Test Summary:")
    logger.info(f"Session start: {'✅ PASS' if session_id else '❌ FAIL'}")
    
    successful_chunks = sum(chunk_results)
    total_chunks = len(chunk_results)
    logger.info(f"Chunk processing: {successful_chunks}/{total_chunks} successful")
    
    if total_chunks > 0:
        avg_processing_time = total_processing_time / total_chunks
        logger.info(f"Average processing time: {avg_processing_time:.2f}s per chunk")
    
    logger.info(f"Session finalization: {'✅ PASS' if finalization_success else '❌ FAIL'}")
    
    # Overall success
    overall_success = (
        session_id is not None and
        successful_chunks == total_chunks and
        finalization_success
    )
    
    if overall_success:
        logger.info("🎉 All tests passed! STT system is working correctly.")
        logger.info("✨ Doctors can now use real-time voice dictation without errors.")
    else:
        logger.error("❌ Some tests failed. Check the errors above.")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)