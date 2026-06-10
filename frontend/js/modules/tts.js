// Text-to-Speech Logic

// Global reference for stopping audio
let currentAudio = null;

// Pre-load voices for mobile browsers
if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.getVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }
}

// Play TTS for a message (Smart Fallback: Server -> Browser)
async function playTTS(text) {
    const voiceId = localStorage.getItem('tts-voice') || '21m00Tcm4TlvDq8ikWAM';
    const stability = localStorage.getItem('tts-stability') || '0.5';
    const clarity = localStorage.getItem('tts-clarity') || '0.75';

    // 0. Force Browser if selected
    if (voiceId === 'browser') {
        console.log("🔊 [TTS] Browser (Native) selected, skipping server.");
        return useBrowserFallback(text);
    }

    // 1. Try Backend TTS (ElevenLabs -> Silero Fallback)
    try {
        console.log("🔊 [TTS] Requesting audio from server...");
        
        // Add a timeout of 6 seconds for the server request
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 6000);

        const response = await window.fetchWithAuth('/tts/speak', {
            method: 'POST',
            signal: controller.signal,
            body: JSON.stringify({
                text: text,
                voice_id: voiceId,
                stability: parseFloat(stability),
                clarity: parseFloat(clarity)
            })
        });

        clearTimeout(timeoutId);

        if (response && response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            currentAudio = new Audio(url);
            
            return new Promise((resolve, reject) => {
                currentAudio.onended = () => {
                    URL.revokeObjectURL(url);
                    currentAudio = null;
                    resolve();
                };
                currentAudio.onerror = (e) => {
                    URL.revokeObjectURL(url);
                    currentAudio = null;
                    reject(e);
                };
                currentAudio.play().catch(reject);
            });
        }
    } catch (e) {
        console.warn('⚠️ Server TTS failed, using browser fallback:', e);
    }

    // 2. Browser Fallback (Local Speech Synthesis)
    return useBrowserFallback(text);
}

// Browser Fallback (Local Speech Synthesis)
async function useBrowserFallback(text) {
    console.log("🔊 [TTS] Starting Browser Fallback (Speech Synthesis)...");
    
    // Clean up text
    const cleanText = text
        .replace(/\[QUEST_DATA\].*$/g, '') 
        .replace(/[^\x00-\x7F]/g, "")      
        .replace(/[*_#`~]/g, '')           
        .replace(/https?:\/\/\S+/g, 'link') 
        .trim();
        
    if (!cleanText) return;

    // Mobile/Tablet Stability Fix: Use Paragraph-based splitting (fewer, larger chunks)
    // We queue these ALL AT ONCE without awaiting. This keeps the "User Activation" chain
    // alive on mobile browsers that block playback if deferred by a promise.
    const chunks = cleanText.split(/\n\n|\n|\.\.\s+/g).filter(p => p.trim().length > 2);
    if (chunks.length === 0) chunks.push(cleanText);

    const total = chunks.length;

    // Preparation: Full reset
    window.speechSynthesis.cancel();
    if (window.speechSynthesis.paused) window.speechSynthesis.resume();

    // Get Settings
    const rateStr = localStorage.getItem('tts-rate') || '1.0';
    const pitchStr = localStorage.getItem('tts-pitch') || '0';
    let rate = parseFloat(rateStr);
    let pitch = 1.0 + (parseFloat(pitchStr) / 20);

    return new Promise((resolve) => {
        let completed = 0;
        
        // Safety timeout for the entire session
        const sessionTimeout = setTimeout(() => {
            console.warn("⚠️ [TTS] Session safety timeout");
            resolve();
        }, 120000); // 120s max

        chunks.forEach((chunk, index) => {
            const utterance = new SpeechSynthesisUtterance(chunk.trim());
            utterance.rate = Math.max(0.5, Math.min(2.0, rate));
            utterance.pitch = Math.max(0.5, Math.min(2.0, pitch));
            
            // Voice selection: Try to find a local high-quality voice
            const voices = window.speechSynthesis.getVoices();
            if (voices.length > 0) {
                // Prefer local voices (usually better quality/less lag)
                utterance.voice = voices.find(v => v.lang.startsWith('en') && v.localService) || 
                                  voices.find(v => v.lang.startsWith('en')) || 
                                  voices[0];
            }

            utterance.onstart = () => {
                console.log(`▶️ [TTS] Playing part ${index + 1}/${total}`);
            };

            utterance.onend = () => {
                completed++;
                if (completed >= total) {
                    clearTimeout(sessionTimeout);
                    resolve();
                }
            };

            utterance.onerror = (err) => {
                console.error(`❌ [TTS] Part ${index + 1} error:`, err);
                completed++;
                if (completed >= total) {
                    clearTimeout(sessionTimeout);
                    resolve();
                }
            };

            // Call SYNCHRONOUSLY. Do not await here.
            window.speechSynthesis.speak(utterance);
        });

        // Some browsers need a resume trigger after queuing
        window.speechSynthesis.resume();
    });
}

// Start TTS from button click (Robust method)
window.startTTS = async function(button) {
    let text = button.getAttribute('data-text');
    
    // Fallback: Check for frag-id (Hall of Heroes/Memory optimization)
    if (!text) {
        const fragId = button.getAttribute('data-frag-id');
        if (fragId) {
            const contentEl = document.getElementById(`frag-content-${fragId}`);
            if (contentEl) {
                text = contentEl.textContent || contentEl.innerText;
            }
        }
    }

    if (!text) {
        console.error('No text found for TTS');
        return;
    }
    
    // If already playing, stop everything
    if (button.classList.contains('playing')) {
        window.speechSynthesis.cancel();
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
        button.classList.remove('playing');
        button.textContent = button.getAttribute('data-original-text') || '🔊 LISTEN';
        button.disabled = false;
        return;
    }
    
    // Tiny delay to allow DOM/Scroll to settle
    await new Promise(r => setTimeout(r, 100));

    // UI State: Loading
    button.classList.add('playing');
    button.dataset.originalText = button.textContent;
    button.textContent = '[LOADING...]';
    button.disabled = true;
    
    window.speechSynthesis.cancel();
    
    try {
        // Use the smart playTTS logic
        button.textContent = '[PLAYING...]';
        await playTTS(text);
    } catch (e) {
        console.error('TTS execution failed:', e);
    } finally {
        // Reset UI
        button.classList.remove('playing');
        button.textContent = button.getAttribute('data-original-text') || '🔊 LISTEN';
        button.disabled = false;
        
        // Final heartbeat cleanup
        if (window.ttsKeepAlive) {
            clearInterval(window.ttsKeepAlive);
            window.ttsKeepAlive = null;
        }
    }
};

// Start Sectioned TTS for long stories
window.startSectionedTTS = async function(button) {
    const text = button.getAttribute('data-text');
    if (!text) return;

    if (button.classList.contains('playing')) {
        window.speechSynthesis.cancel();
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
        button.classList.remove('playing');
        button.textContent = '🔊 LISTEN TO STORY';
        return;
    }

    button.classList.add('playing');
    button.textContent = '⏹️ STOP LISTENING';
    window.speechSynthesis.cancel();

    // Split text into chunks (sentences or paragraphs)
    const chunks = text.match(/[^.!?]+[.!?]+(\s|$)/g) || [text];
    
    try {
        for (let i = 0; i < chunks.length; i++) {
            if (!button.classList.contains('playing')) break;
            
            const chunk = chunks[i].trim();
            if (!chunk) continue;
            
            // Progress indicator
            const percent = Math.round(((i+1) / chunks.length) * 100);
            button.textContent = `⏹️ STOP (${percent}%)`;
            
            // Use the smart playTTS logic for each chunk
            await playTTS(chunk);
        }
    } catch (e) {
        console.error('Sectioned TTS Error:', e);
    } finally {
        button.classList.remove('playing');
        button.textContent = '🔊 LISTEN TO STORY';
    }
};

// Export to window for access from HTML
window.playTTS = playTTS;
window.useBrowserFallback = useBrowserFallback;
