// Text-to-Speech Logic

// Play TTS for a message (Legacy/Direct call)
async function playTTS(text) {
    const apiKey = localStorage.getItem('elevenlabs-api-key');
    const voiceId = localStorage.getItem('tts-voice') || '21m00Tcm4TlvDq8ikWAM'; // Default Rachel
    const stability = localStorage.getItem('tts-stability') || '0.5';
    const clarity = localStorage.getItem('tts-clarity') || '0.75';
    const rate = localStorage.getItem('tts-rate') || '1.0';
    const pitch = localStorage.getItem('tts-pitch') || '0';

    // If no API key, use browser TTS
    if (!apiKey) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = parseFloat(rate);
        utterance.pitch = 1.0 + (parseFloat(pitch) / 20); // Approximate pitch mapping
        window.speechSynthesis.speak(utterance);
        return;
    }

    // ElevenLabs API Call
    try {
        const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
            method: 'POST',
            headers: {
                'xi-api-key': apiKey,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                model_id: 'eleven_monolingual_v1',
                voice_settings: {
                    stability: parseFloat(stability),
                    similarity_boost: parseFloat(clarity)
                }
            })
        });

        if (!response.ok) throw new Error('TTS API failed');

        const blob = await response.blob();
        const audio = new Audio(URL.createObjectURL(blob));
        audio.play();
    } catch (e) {
        console.error('TTS Error:', e);
        // Fallback to browser TTS
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
    }
}

// Start TTS from button click (Robust method)
window.startTTS = function(button) {
    // Read text from data attribute instead of function parameter
    const text = button.getAttribute('data-text');
    if (!text) {
        console.error('No text found for TTS');
        return;
    }
    
    // If already playing, stop it
    if (button.classList.contains('playing')) {
        window.speechSynthesis.cancel();
        button.classList.remove('playing');
        button.textContent = '🔊 LISTEN';
        button.disabled = false;
        return;
    }
    
    // Start playing
    button.classList.add('playing');
    button.textContent = '[PLAYING...]';
    button.disabled = true;
    
    window.speechSynthesis.cancel(); // Clear any queued speech
    
    // Get settings from localStorage
    const rate = localStorage.getItem('tts-rate') || '1.0';
    const pitch = localStorage.getItem('tts-pitch') || '0';

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = parseFloat(rate); 
    utterance.pitch = 1.0 + (parseFloat(pitch) / 20); // Approximate pitch mapping (0 is neutral)
    utterance.volume = 1.0;
    
    utterance.onend = () => {
        button.classList.remove('playing');
        button.textContent = '🔊 LISTEN';
        button.disabled = false;
    };
    
    utterance.onerror = (e) => {
        console.error('TTS error:', e);
        button.classList.remove('playing');
        button.textContent = '🔊 LISTEN';
        button.disabled = false;
    };
    
    window.speechSynthesis.speak(utterance);
};

// Preview Voice Settings
window.previewVoice = function() {
    const text = "This is a preview of your selected voice settings. Adjust the rate and pitch to your liking.";
    playTTS(text);
};
