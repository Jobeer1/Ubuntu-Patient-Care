#!/usr/bin/env python3
"""
Voice Routes for Medical Reporting Module
Voice demo and dictation interfaces
"""

import logging

logger = logging.getLogger(__name__)

def render_voice_demo():
    """Render the voice demo page with SA medical optimization"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Voice Demo - SA Medical Reporting</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link href="/static/css/sa-dashboard.css" rel="stylesheet">
        
        <style>
            .voice-container {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 2rem 0;
            }
            
            .voice-card {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                padding: 2rem;
                margin: 1rem;
            }
            
            .microphone-button {
                width: 120px;
                height: 120px;
                border-radius: 50%;
                border: none;
                background: linear-gradient(135deg, #4CAF50, #45a049);
                color: white;
                font-size: 3rem;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 8px 20px rgba(76, 175, 80, 0.3);
            }
            
            .microphone-button:hover {
                transform: scale(1.05);
                box-shadow: 0 12px 30px rgba(76, 175, 80, 0.4);
            }
            
            .microphone-button.recording {
                background: linear-gradient(135deg, #f44336, #d32f2f);
                animation: pulse 1.5s infinite;
            }
            
            .microphone-button.processing {
                background: linear-gradient(135deg, #ff9800, #f57c00);
                animation: spin 2s linear infinite;
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); }
                100% { transform: scale(1); }
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .audio-visualizer {
                height: 60px;
                background: #f5f5f5;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 1rem 0;
                position: relative;
                overflow: hidden;
            }
            
            .audio-bar {
                width: 4px;
                background: #4CAF50;
                margin: 0 1px;
                border-radius: 2px;
                transition: height 0.1s ease;
            }
            
            .transcription-area {
                min-height: 200px;
                background: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 10px;
                padding: 1.5rem;
                font-size: 1.1rem;
                line-height: 1.6;
                transition: all 0.3s ease;
            }
            
            .transcription-area.active {
                border-color: #4CAF50;
                background: #f0f8f0;
            }
            
            .status-indicator {
                display: inline-flex;
                align-items: center;
                padding: 0.5rem 1rem;
                border-radius: 20px;
                font-size: 0.9rem;
                font-weight: 500;
                margin: 0.25rem;
            }
            
            .status-ready { background: #e8f5e8; color: #2e7d32; }
            .status-listening { background: #fff3e0; color: #ef6c00; }
            .status-processing { background: #e3f2fd; color: #1976d2; }
            .status-error { background: #ffebee; color: #c62828; }
            
            .demo-btn {
                padding: 0.75rem 1.5rem;
                border: none;
                border-radius: 25px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                margin: 0.5rem;
            }
            
            .demo-btn-primary {
                background: linear-gradient(135deg, #2196F3, #1976D2);
                color: white;
            }
            
            .demo-btn-secondary {
                background: #f5f5f5;
                color: #333;
                border: 2px solid #ddd;
            }
            
            .demo-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
            
            .medical-term {
                display: inline-block;
                background: #e3f2fd;
                color: #1976d2;
                padding: 0.25rem 0.75rem;
                border-radius: 15px;
                font-size: 0.85rem;
                margin: 0.25rem;
            }
        </style>
    </head>
    <body>
        <div class="voice-container">
            <!-- Header -->
            <div class="container mx-auto px-4">
                <div class="text-center mb-8">
                    <h1 class="text-4xl font-bold text-white mb-4">
                        <i class="fas fa-microphone mr-3"></i>
                        SA Medical Voice Demo
                    </h1>
                    <p class="text-xl text-white opacity-90">
                        Professional voice dictation optimized for South African medical terminology
                    </p>
                    <div class="inline-block bg-orange-500 text-white px-4 py-2 rounded-full mt-4">
                        <i class="fas fa-flag mr-2"></i>
                        🇿🇦 South African English Optimized
                    </div>
                </div>
            </div>

            <!-- Main Voice Interface -->
            <div class="container mx-auto px-4">
                <div class="voice-card max-w-4xl mx-auto">
                    
                    <!-- Status Indicators -->
                    <div class="text-center mb-6">
                        <div id="status-indicators">
                            <div class="status-indicator status-ready" id="status-ready">
                                <i class="fas fa-check-circle mr-2"></i>
                                Ready
                            </div>
                            <div class="status-indicator status-listening hidden" id="status-listening">
                                <i class="fas fa-microphone mr-2"></i>
                                Listening...
                            </div>
                            <div class="status-indicator status-processing hidden" id="status-processing">
                                <i class="fas fa-cog fa-spin mr-2"></i>
                                Processing...
                            </div>
                            <div class="status-indicator status-error hidden" id="status-error">
                                <i class="fas fa-exclamation-triangle mr-2"></i>
                                Error
                            </div>
                        </div>
                    </div>

                    <!-- Microphone Button -->
                    <div class="text-center mb-8">
                        <button id="microphone-btn" class="microphone-button">
                            <i class="fas fa-microphone"></i>
                        </button>
                        <div class="mt-4">
                            <p class="text-gray-600 text-lg">Click to start voice dictation</p>
                            <p class="text-sm text-gray-500">Optimized for SA English medical terminology</p>
                        </div>
                    </div>

                    <!-- Audio Visualizer -->
                    <div class="audio-visualizer" id="audio-visualizer">
                        <div class="text-gray-400">
                            <i class="fas fa-volume-up mr-2"></i>
                            Audio visualization will appear here
                        </div>
                    </div>

                    <!-- Transcription Area -->
                    <div class="mb-6">
                        <h3 class="text-xl font-semibold mb-3">Live Transcription</h3>
                        <div id="transcription-area" class="transcription-area">
                            <div class="text-gray-500 text-center">
                                <i class="fas fa-microphone-alt text-3xl mb-3"></i>
                                <p>Your voice transcription will appear here...</p>
                                <p class="text-sm mt-2">Speak clearly for best results with SA English medical terms</p>
                            </div>
                        </div>
                    </div>

                    <!-- Control Buttons -->
                    <div class="text-center mb-6">
                        <button id="clear-btn" class="demo-btn demo-btn-secondary">
                            <i class="fas fa-trash"></i>
                            Clear Text
                        </button>
                        <button id="copy-btn" class="demo-btn demo-btn-primary">
                            <i class="fas fa-copy"></i>
                            Copy Text
                        </button>
                        <button id="save-btn" class="demo-btn demo-btn-primary">
                            <i class="fas fa-save"></i>
                            Save Report
                        </button>
                    </div>

                    <!-- SA Medical Terms Examples -->
                    <div class="mb-6">
                        <h4 class="text-lg font-semibold mb-3">SA Medical Terms Recognition</h4>
                        <div class="text-center">
                            <span class="medical-term">Pneumonia</span>
                            <span class="medical-term">Hypertension</span>
                            <span class="medical-term">Diabetes mellitus</span>
                            <span class="medical-term">Tuberculosis</span>
                            <span class="medical-term">Myocardial infarction</span>
                            <span class="medical-term">Cerebrovascular accident</span>
                        </div>
                        <p class="text-sm text-gray-600 mt-3 text-center">
                            The system is optimized to recognize these and many more SA medical terms
                        </p>
                    </div>

                    <!-- Navigation -->
                    <div class="text-center">
                        <a href="/" class="demo-btn demo-btn-secondary">
                            <i class="fas fa-home"></i>
                            Back to Dashboard
                        </a>
                        <a href="/new-report" class="demo-btn demo-btn-primary">
                            <i class="fas fa-file-medical"></i>
                            Create Full Report
                        </a>
                    </div>
                </div>
            </div>
        </div>

        <!-- JavaScript -->
        <script src="/static/js/voice-demo.js"></script>
        
        <script>
            // Initialize voice demo
            document.addEventListener('DOMContentLoaded', function() {
                console.log('🇿🇦 SA Medical Voice Demo initialized');
                
                // Initialize voice demo functionality
                if (typeof SAVoiceDemo !== 'undefined') {
                    window.voiceDemo = new SAVoiceDemo();
                } else {
                    console.warn('Voice demo JavaScript not loaded, using fallback');
                    initializeFallbackVoiceDemo();
                }
            });
            
            function initializeFallbackVoiceDemo() {
                const micBtn = document.getElementById('microphone-btn');
                const transcriptionArea = document.getElementById('transcription-area');
                
                micBtn.addEventListener('click', function() {
                    transcriptionArea.innerHTML = '<p class="text-blue-600">Voice demo functionality is being loaded...</p>';
                });
            }
        </script>
    </body>
    </html>
    '''