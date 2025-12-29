// Voice Input Logic (Whisper & Recording)

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingTimer = null;
let recordingStartTime = 0;

// 1. Toggle Microphone Recording
async function toggleRecording() {
    const btn = document.getElementById('record-btn');
    const timerDisplay = document.getElementById('recording-timer');
    const timerSpan = document.getElementById('timer');

    if (!isRecording) {
        // START RECORDING
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                await uploadAudio(audioBlob);
                
                // Stop all tracks to release microphone
                stream.getTracks().forEach(track => track.stop());
            };

            // Use a smaller timeslice to make data available sooner, though we only use it on stop
            mediaRecorder.start(1000); 
            isRecording = true;
            
            // UI Updates
            btn.classList.add('recording');
            btn.innerHTML = '⏹ STOP';
            timerDisplay.style.display = 'block';
            
            // Start Timer
            recordingStartTime = Date.now();
            recordingTimer = setInterval(() => {
                const diff = Math.floor((Date.now() - recordingStartTime) / 1000);
                const mins = Math.floor(diff / 60);
                const secs = diff % 60;
                timerSpan.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
            }, 1000);

        } catch (err) {
            console.error("Microphone access denied:", err);
            alert("Could not access microphone. Please ensure you have granted permission.");
            isRecording = false; // Reset state
        }
    } else {
        // STOP RECORDING
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        
        isRecording = false;
        clearInterval(recordingTimer);
        
        // UI Updates
        btn.classList.remove('recording');
        btn.innerHTML = '🎙️ REC';
        timerDisplay.style.display = 'none';
        timerSpan.textContent = '0:00';
    }
}

// 2. Toggle File Upload
function toggleVoiceInput() {
    document.getElementById('voice-file-input').click();
}

// 3. Handle File Selection
async function handleVoiceFile(event) {
    const file = event.target.files[0];
    if (file) {
        await uploadAudio(file);
    }
    // Reset input so same file can be selected again
    event.target.value = '';
}

// 4. Upload Audio to Backend
async function uploadAudio(audioBlob) {
    const input = document.getElementById('msg-input');
    const originalPlaceholder = input.placeholder;
    
    input.disabled = true;
    input.placeholder = "Transcribing audio...";
    input.value = ""; // Clear current text

    const formData = new FormData();
    // Ensure filename has extension for backend detection
    formData.append('file', audioBlob, 'recording.wav');

    try {
        // Use the global 'token' variable from config.js instead of reading localStorage directly
        // config.js reads it as 'token', but voice_input.js was looking for 'sdoh_token'
        const authToken = localStorage.getItem('token'); 
        
        // Debug: Check if token exists
        if (!authToken) {
            console.error("No auth token found in localStorage (key='token')");
            alert("You are not logged in. Please refresh and login again.");
            input.disabled = false;
            input.placeholder = originalPlaceholder;
            return;
        }

        const res = await fetch('/api/sdoh/dictation/transcribe', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });

        if (res.ok) {
            const data = await res.json();
            if (data.text) {
                input.value = data.text;
                input.focus();
            } else {
                alert("Transcription returned empty text.");
            }
        } else {
            const err = await res.json();
            console.error("Transcription failed:", err);
            alert(`Transcription failed: ${err.error || 'Unknown error'}`);
        }
    } catch (e) {
        console.error("Upload error:", e);
        alert("Error uploading audio. Check console.");
    } finally {
        input.disabled = false;
        input.placeholder = originalPlaceholder;
    }
}
