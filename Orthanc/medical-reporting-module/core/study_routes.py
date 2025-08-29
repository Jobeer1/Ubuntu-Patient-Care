#!/usr/bin/env python3
"""
Study Routes for Medical Reporting Module
Patient study search and DICOM management
"""

import logging

logger = logging.getLogger(__name__)

def render_find_studies():
    """Render the find studies interface"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Find Studies - SA Medical Reporting</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link href="/static/css/sa-dashboard.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h1 class="text-3xl font-bold mb-6 text-green-700">
                    <i class="fas fa-search mr-3"></i>Find Patient Studies
                </h1>
                
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                    <div class="flex items-center">
                        <i class="fas fa-info-circle text-blue-500 mr-3"></i>
                        <div>
                            <h3 class="font-semibold text-blue-800">PACS Integration</h3>
                            <p class="text-blue-700">Search for patient studies and DICOM images in the SA Medical system with POPIA compliance.</p>
                        </div>
                    </div>
                </div>

                <!-- Search Form -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Patient Name</label>
                        <input type="text" id="patient-name" placeholder="Enter patient name..." 
                               class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500">
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Patient ID / SA ID</label>
                        <input type="text" id="patient-id" placeholder="Enter patient ID or SA ID..." 
                               class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500">
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Study Date From</label>
                        <input type="date" id="date-from" 
                               class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500">
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Study Date To</label>
                        <input type="date" id="date-to" 
                               class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500">
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Modality</label>
                        <select id="modality" class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500">
                            <option value="">All Modalities</option>
                            <option value="CT">CT - Computed Tomography</option>
                            <option value="MR">MR - Magnetic Resonance</option>
                            <option value="CR">CR - Computed Radiography</option>
                            <option value="DX">DX - Digital Radiography</option>
                            <option value="US">US - Ultrasound</option>
                            <option value="NM">NM - Nuclear Medicine</option>
                            <option value="PT">PT - Positron Emission Tomography</option>
                            <option value="MG">MG - Mammography</option>
                        </select>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Study Description</label>
                        <input type="text" id="study-description" placeholder="Enter study description..." 
                               class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500">
                    </div>
                </div>

                <!-- Search Buttons -->
                <div class="flex flex-wrap gap-4 mb-8">
                    <button id="search-btn" class="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors">
                        <i class="fas fa-search mr-2"></i>Search Studies
                    </button>
                    <button id="clear-btn" class="bg-gray-500 text-white px-6 py-3 rounded-lg hover:bg-gray-600 transition-colors">
                        <i class="fas fa-eraser mr-2"></i>Clear Form
                    </button>
                    <button id="advanced-btn" class="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors">
                        <i class="fas fa-cogs mr-2"></i>Advanced Search
                    </button>
                </div>

                <!-- Results Area -->
                <div id="results-area" class="hidden">
                    <h2 class="text-2xl font-bold mb-4 text-gray-800">
                        <i class="fas fa-list mr-2"></i>Search Results
                    </h2>
                    <div id="results-container" class="space-y-4">
                        <!-- Results will be populated here -->
                    </div>
                </div>

                <!-- No Results Message -->
                <div id="no-results" class="hidden text-center py-12">
                    <i class="fas fa-search text-6xl text-gray-300 mb-4"></i>
                    <h3 class="text-xl font-semibold text-gray-600 mb-2">No Studies Found</h3>
                    <p class="text-gray-500">Try adjusting your search criteria or check the PACS connection.</p>
                </div>

                <!-- Loading State -->
                <div id="loading-state" class="hidden text-center py-12">
                    <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mb-4"></div>
                    <h3 class="text-xl font-semibold text-gray-600 mb-2">Searching PACS...</h3>
                    <p class="text-gray-500">Please wait while we search for studies.</p>
                </div>

                <!-- Quick Actions -->
                <div class="mt-8 pt-6 border-t border-gray-200">
                    <h3 class="text-lg font-semibold mb-4">Quick Actions</h3>
                    <div class="flex flex-wrap gap-4">
                        <a href="/dicom-viewer" class="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 transition-colors">
                            <i class="fas fa-eye mr-2"></i>Open DICOM Viewer
                        </a>
                        <a href="/patients" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors">
                            <i class="fas fa-users mr-2"></i>Patient Management
                        </a>
                        <a href="/orthanc-manager" class="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 transition-colors">
                            <i class="fas fa-database mr-2"></i>PACS Manager
                        </a>
                    </div>
                </div>

                <!-- Navigation -->
                <div class="mt-8 pt-6 border-t border-gray-200">
                    <a href="/" class="text-blue-600 hover:text-blue-800 font-medium">
                        <i class="fas fa-arrow-left mr-2"></i>Back to Dashboard
                    </a>
                </div>
            </div>
        </div>

        <script>
            // Initialize find studies functionality
            document.addEventListener('DOMContentLoaded', function() {
                console.log('Find Studies interface initialized');
                
                const searchBtn = document.getElementById('search-btn');
                const clearBtn = document.getElementById('clear-btn');
                const loadingState = document.getElementById('loading-state');
                const resultsArea = document.getElementById('results-area');
                const noResults = document.getElementById('no-results');
                
                searchBtn.addEventListener('click', function() {
                    // Show loading state
                    loadingState.classList.remove('hidden');
                    resultsArea.classList.add('hidden');
                    noResults.classList.add('hidden');
                    
                    // Simulate search (replace with actual PACS query)
                    setTimeout(() => {
                        loadingState.classList.add('hidden');
                        noResults.classList.remove('hidden');
                    }, 2000);
                });
                
                clearBtn.addEventListener('click', function() {
                    // Clear all form fields
                    document.getElementById('patient-name').value = '';
                    document.getElementById('patient-id').value = '';
                    document.getElementById('date-from').value = '';
                    document.getElementById('date-to').value = '';
                    document.getElementById('modality').value = '';
                    document.getElementById('study-description').value = '';
                    
                    // Hide results
                    resultsArea.classList.add('hidden');
                    noResults.classList.add('hidden');
                    loadingState.classList.add('hidden');
                });
            });
        </script>
    </body>
    </html>
    '''