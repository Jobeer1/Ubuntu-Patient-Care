#!/usr/bin/env python3
"""
Template Routes for Medical Reporting Module
SA Medical template management
"""

import logging

logger = logging.getLogger(__name__)

def render_templates():
    """Render the templates management interface"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Templates - SA Medical Reporting</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link href="/static/css/sa-dashboard.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h1 class="text-3xl font-bold mb-6 text-orange-600">
                    <i class="fas fa-file-alt mr-3"></i>SA Medical Report Templates
                </h1>
                
                <div class="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-6">
                    <div class="flex items-center">
                        <i class="fas fa-certificate text-orange-500 mr-3"></i>
                        <div>
                            <h3 class="font-semibold text-orange-800">HPCSA Compliant Templates</h3>
                            <p class="text-orange-700">Professional medical report templates designed for South African healthcare standards.</p>
                        </div>
                    </div>
                </div>

                <!-- Template Categories -->
                <div class="mb-8">
                    <h2 class="text-2xl font-bold mb-4 text-gray-800">Template Categories</h2>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <button class="template-category-btn active" data-category="all">
                            <i class="fas fa-th-large"></i>
                            All Templates
                        </button>
                        <button class="template-category-btn" data-category="radiology">
                            <i class="fas fa-x-ray"></i>
                            Radiology
                        </button>
                        <button class="template-category-btn" data-category="cardiology">
                            <i class="fas fa-heartbeat"></i>
                            Cardiology
                        </button>
                        <button class="template-category-btn" data-category="general">
                            <i class="fas fa-user-md"></i>
                            General Medicine
                        </button>
                    </div>
                </div>

                <!-- Template Grid -->
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                    <!-- CT Chest Template -->
                    <div class="template-card" data-category="radiology">
                        <div class="template-header">
                            <i class="fas fa-lungs text-blue-500"></i>
                            <h3>CT Chest Template</h3>
                            <span class="template-badge">Radiology</span>
                        </div>
                        <div class="template-body">
                            <p class="template-description">Comprehensive chest CT reporting template with SA medical standards</p>
                            <div class="template-features">
                                <span class="feature-tag">HPCSA Compliant</span>
                                <span class="feature-tag">Structured Report</span>
                                <span class="feature-tag">Voice Optimized</span>
                            </div>
                        </div>
                        <div class="template-actions">
                            <button class="btn-primary">
                                <i class="fas fa-play mr-2"></i>Use Template
                            </button>
                            <button class="btn-secondary">
                                <i class="fas fa-eye mr-2"></i>Preview
                            </button>
                        </div>
                    </div>

                    <!-- X-Ray Template -->
                    <div class="template-card" data-category="radiology">
                        <div class="template-header">
                            <i class="fas fa-x-ray text-green-500"></i>
                            <h3>X-Ray Template</h3>
                            <span class="template-badge">Radiology</span>
                        </div>
                        <div class="template-body">
                            <p class="template-description">General X-ray reporting template for all anatomical regions</p>
                            <div class="template-features">
                                <span class="feature-tag">Multi-Region</span>
                                <span class="feature-tag">Quick Entry</span>
                                <span class="feature-tag">SA Standards</span>
                            </div>
                        </div>
                        <div class="template-actions">
                            <button class="btn-primary">
                                <i class="fas fa-play mr-2"></i>Use Template
                            </button>
                            <button class="btn-secondary">
                                <i class="fas fa-eye mr-2"></i>Preview
                            </button>
                        </div>
                    </div>

                    <!-- MRI Brain Template -->
                    <div class="template-card" data-category="radiology">
                        <div class="template-header">
                            <i class="fas fa-brain text-purple-500"></i>
                            <h3>MRI Brain Template</h3>
                            <span class="template-badge">Radiology</span>
                        </div>
                        <div class="template-body">
                            <p class="template-description">Detailed brain MRI reporting with neurological assessment</p>
                            <div class="template-features">
                                <span class="feature-tag">Neurological</span>
                                <span class="feature-tag">Detailed</span>
                                <span class="feature-tag">Multi-Sequence</span>
                            </div>
                        </div>
                        <div class="template-actions">
                            <button class="btn-primary">
                                <i class="fas fa-play mr-2"></i>Use Template
                            </button>
                            <button class="btn-secondary">
                                <i class="fas fa-eye mr-2"></i>Preview
                            </button>
                        </div>
                    </div>

                    <!-- Echocardiogram Template -->
                    <div class="template-card" data-category="cardiology">
                        <div class="template-header">
                            <i class="fas fa-heartbeat text-red-500"></i>
                            <h3>Echocardiogram Template</h3>
                            <span class="template-badge">Cardiology</span>
                        </div>
                        <div class="template-body">
                            <p class="template-description">Comprehensive echocardiogram reporting with cardiac measurements</p>
                            <div class="template-features">
                                <span class="feature-tag">Cardiac Function</span>
                                <span class="feature-tag">Measurements</span>
                                <span class="feature-tag">Guidelines</span>
                            </div>
                        </div>
                        <div class="template-actions">
                            <button class="btn-primary">
                                <i class="fas fa-play mr-2"></i>Use Template
                            </button>
                            <button class="btn-secondary">
                                <i class="fas fa-eye mr-2"></i>Preview
                            </button>
                        </div>
                    </div>

                    <!-- General Consultation Template -->
                    <div class="template-card" data-category="general">
                        <div class="template-header">
                            <i class="fas fa-user-md text-teal-500"></i>
                            <h3>General Consultation</h3>
                            <span class="template-badge">General</span>
                        </div>
                        <div class="template-body">
                            <p class="template-description">Standard consultation template for general medical practice</p>
                            <div class="template-features">
                                <span class="feature-tag">SOAP Format</span>
                                <span class="feature-tag">ICD-10</span>
                                <span class="feature-tag">Prescription</span>
                            </div>
                        </div>
                        <div class="template-actions">
                            <button class="btn-primary">
                                <i class="fas fa-play mr-2"></i>Use Template
                            </button>
                            <button class="btn-secondary">
                                <i class="fas fa-eye mr-2"></i>Preview
                            </button>
                        </div>
                    </div>

                    <!-- Discharge Summary Template -->
                    <div class="template-card" data-category="general">
                        <div class="template-header">
                            <i class="fas fa-file-medical text-indigo-500"></i>
                            <h3>Discharge Summary</h3>
                            <span class="template-badge">General</span>
                        </div>
                        <div class="template-body">
                            <p class="template-description">Hospital discharge summary with treatment history and follow-up</p>
                            <div class="template-features">
                                <span class="feature-tag">Hospital</span>
                                <span class="feature-tag">Follow-up</span>
                                <span class="feature-tag">Medications</span>
                            </div>
                        </div>
                        <div class="template-actions">
                            <button class="btn-primary">
                                <i class="fas fa-play mr-2"></i>Use Template
                            </button>
                            <button class="btn-secondary">
                                <i class="fas fa-eye mr-2"></i>Preview
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Template Management Actions -->
                <div class="bg-gray-50 rounded-lg p-6 mb-6">
                    <h3 class="text-lg font-semibold mb-4">Template Management</h3>
                    <div class="flex flex-wrap gap-4">
                        <button class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors">
                            <i class="fas fa-plus mr-2"></i>Create New Template
                        </button>
                        <button class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors">
                            <i class="fas fa-upload mr-2"></i>Import Template
                        </button>
                        <button class="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 transition-colors">
                            <i class="fas fa-download mr-2"></i>Export Templates
                        </button>
                        <button class="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 transition-colors">
                            <i class="fas fa-cogs mr-2"></i>Template Settings
                        </button>
                    </div>
                </div>

                <!-- Navigation -->
                <div class="pt-6 border-t border-gray-200">
                    <a href="/" class="text-blue-600 hover:text-blue-800 font-medium">
                        <i class="fas fa-arrow-left mr-2"></i>Back to Dashboard
                    </a>
                </div>
            </div>
        </div>

        <style>
            .template-category-btn {
                @apply flex flex-col items-center p-4 border-2 border-gray-200 rounded-lg hover:border-orange-300 transition-colors cursor-pointer;
            }
            
            .template-category-btn.active {
                @apply border-orange-500 bg-orange-50 text-orange-700;
            }
            
            .template-category-btn i {
                @apply text-2xl mb-2;
            }
            
            .template-card {
                @apply bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow;
            }
            
            .template-header {
                @apply p-4 border-b border-gray-100;
            }
            
            .template-header i {
                @apply text-2xl mb-2;
            }
            
            .template-header h3 {
                @apply font-semibold text-lg text-gray-800 mb-2;
            }
            
            .template-badge {
                @apply inline-block bg-gray-100 text-gray-600 px-2 py-1 rounded text-sm;
            }
            
            .template-body {
                @apply p-4;
            }
            
            .template-description {
                @apply text-gray-600 mb-3;
            }
            
            .template-features {
                @apply flex flex-wrap gap-2;
            }
            
            .feature-tag {
                @apply bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs;
            }
            
            .template-actions {
                @apply p-4 border-t border-gray-100 flex gap-2;
            }
            
            .btn-primary {
                @apply bg-orange-600 text-white px-3 py-2 rounded text-sm hover:bg-orange-700 transition-colors flex items-center;
            }
            
            .btn-secondary {
                @apply bg-gray-200 text-gray-700 px-3 py-2 rounded text-sm hover:bg-gray-300 transition-colors flex items-center;
            }
        </style>

        <script>
            // Initialize templates functionality
            document.addEventListener('DOMContentLoaded', function() {
                console.log('Templates interface initialized');
                
                const categoryBtns = document.querySelectorAll('.template-category-btn');
                const templateCards = document.querySelectorAll('.template-card');
                
                categoryBtns.forEach(btn => {
                    btn.addEventListener('click', function() {
                        const category = this.dataset.category;
                        
                        // Update active category button
                        categoryBtns.forEach(b => b.classList.remove('active'));
                        this.classList.add('active');
                        
                        // Filter template cards
                        templateCards.forEach(card => {
                            if (category === 'all' || card.dataset.category === category) {
                                card.style.display = 'block';
                            } else {
                                card.style.display = 'none';
                            }
                        });
                    });
                });
                
                // Handle template actions
                document.querySelectorAll('.btn-primary').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const templateName = this.closest('.template-card').querySelector('h3').textContent;
                        alert(`Using template: ${templateName}`);
                        // Redirect to voice reporting with template
                        window.location.href = '/voice-reporting?template=' + encodeURIComponent(templateName);
                    });
                });
                
                document.querySelectorAll('.btn-secondary').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const templateName = this.closest('.template-card').querySelector('h3').textContent;
                        alert(`Previewing template: ${templateName}`);
                        // Show template preview modal
                    });
                });
            });
        </script>
    </body>
    </html>
    '''