#!/usr/bin/env python3
"""
Patient Routes for Medical Reporting Module
Patient management with POPIA compliance
"""

import logging

logger = logging.getLogger(__name__)

def render_patients():
    """Render the patient management interface"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Patients - SA Medical Reporting</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link href="/static/css/sa-dashboard.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h1 class="text-3xl font-bold mb-6 text-blue-700">
                    <i class="fas fa-users mr-3"></i>Patient Management
                </h1>
                
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                    <div class="flex items-center">
                        <i class="fas fa-shield-alt text-blue-500 mr-3"></i>
                        <div>
                            <h3 class="font-semibold text-blue-800">POPIA Compliant</h3>
                            <p class="text-blue-700">Patient records are managed with full POPIA compliance and SA healthcare standards.</p>
                        </div>
                    </div>
                </div>

                <!-- Patient Search and Actions -->
                <div class="flex flex-col md:flex-row gap-4 mb-8">
                    <div class="flex-1">
                        <div class="relative">
                            <input type="text" id="patient-search" placeholder="Search patients by name, SA ID, or patient number..." 
                                   class="w-full p-3 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                            <i class="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <button id="add-patient-btn" class="bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 transition-colors">
                            <i class="fas fa-plus mr-2"></i>Add Patient
                        </button>
                        <button id="import-btn" class="bg-green-600 text-white px-4 py-3 rounded-lg hover:bg-green-700 transition-colors">
                            <i class="fas fa-upload mr-2"></i>Import
                        </button>
                    </div>
                </div>

                <!-- Patient List -->
                <div id="patient-list" class="space-y-4 mb-8">
                    <!-- Sample Patient Card -->
                    <div class="patient-card bg-gray-50 border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-4">
                                <div class="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center text-white font-semibold">
                                    <i class="fas fa-user"></i>
                                </div>
                                <div>
                                    <h3 class="font-semibold text-lg text-gray-800">Sample Patient</h3>
                                    <p class="text-gray-600">SA ID: 8001015009087 • Patient #: P001</p>
                                    <p class="text-sm text-gray-500">DOB: 01 Jan 1980 • Age: 44 • Gender: Male</p>
                                </div>
                            </div>
                            <div class="flex items-center space-x-2">
                                <span class="bg-green-100 text-green-800 px-2 py-1 rounded text-sm">Active</span>
                                <button class="text-blue-600 hover:text-blue-800 p-2">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="text-green-600 hover:text-green-800 p-2">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="text-red-600 hover:text-red-800 p-2">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div class="mt-4 pt-4 border-t border-gray-200">
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                                <div>
                                    <span class="font-medium text-gray-700">Medical Aid:</span>
                                    <span class="text-gray-600">Discovery Health</span>
                                </div>
                                <div>
                                    <span class="font-medium text-gray-700">Last Visit:</span>
                                    <span class="text-gray-600">15 Aug 2024</span>
                                </div>
                                <div>
                                    <span class="font-medium text-gray-700">Studies:</span>
                                    <span class="text-gray-600">3 studies</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Empty State -->
                <div id="empty-state" class="hidden text-center py-12">
                    <i class="fas fa-users text-6xl text-gray-300 mb-4"></i>
                    <h3 class="text-xl font-semibold text-gray-600 mb-2">No Patients Found</h3>
                    <p class="text-gray-500 mb-6">Add your first patient to get started with the SA Medical system.</p>
                    <button class="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors">
                        <i class="fas fa-plus mr-2"></i>Add First Patient
                    </button>
                </div>

                <!-- Quick Stats -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                        <i class="fas fa-users text-2xl text-blue-500 mb-2"></i>
                        <div class="text-2xl font-bold text-blue-700">1</div>
                        <div class="text-sm text-blue-600">Total Patients</div>
                    </div>
                    <div class="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                        <i class="fas fa-user-check text-2xl text-green-500 mb-2"></i>
                        <div class="text-2xl font-bold text-green-700">1</div>
                        <div class="text-sm text-green-600">Active Patients</div>
                    </div>
                    <div class="bg-orange-50 border border-orange-200 rounded-lg p-4 text-center">
                        <i class="fas fa-calendar-day text-2xl text-orange-500 mb-2"></i>
                        <div class="text-2xl font-bold text-orange-700">0</div>
                        <div class="text-sm text-orange-600">Today's Visits</div>
                    </div>
                    <div class="bg-purple-50 border border-purple-200 rounded-lg p-4 text-center">
                        <i class="fas fa-x-ray text-2xl text-purple-500 mb-2"></i>
                        <div class="text-2xl font-bold text-purple-700">3</div>
                        <div class="text-sm text-purple-600">Total Studies</div>
                    </div>
                </div>

                <!-- POPIA Compliance Notice -->
                <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                    <div class="flex items-start">
                        <i class="fas fa-info-circle text-yellow-500 mr-3 mt-1"></i>
                        <div>
                            <h4 class="font-semibold text-yellow-800 mb-2">POPIA Compliance Notice</h4>
                            <p class="text-yellow-700 text-sm">
                                All patient data is handled in accordance with the Protection of Personal Information Act (POPIA). 
                                Access is logged and monitored. Only authorized healthcare professionals may view patient information.
                            </p>
                        </div>
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

        <!-- Add Patient Modal -->
        <div id="add-patient-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
            <div class="bg-white rounded-lg p-6 w-full max-w-2xl mx-4">
                <div class="flex justify-between items-center mb-6">
                    <h2 class="text-2xl font-bold text-gray-800">Add New Patient</h2>
                    <button id="close-modal" class="text-gray-500 hover:text-gray-700">
                        <i class="fas fa-times text-xl"></i>
                    </button>
                </div>
                
                <form id="add-patient-form" class="space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">First Name *</label>
                            <input type="text" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Last Name *</label>
                            <input type="text" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">SA ID Number *</label>
                            <input type="text" required pattern="[0-9]{13}" class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Date of Birth *</label>
                            <input type="date" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Gender *</label>
                            <select required class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                                <option value="">Select Gender</option>
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Medical Aid</label>
                            <input type="text" class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                        </div>
                    </div>
                    
                    <div class="flex justify-end space-x-4 pt-6">
                        <button type="button" id="cancel-btn" class="px-6 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
                            Cancel
                        </button>
                        <button type="submit" class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                            <i class="fas fa-save mr-2"></i>Save Patient
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <script>
            // Initialize patient management functionality
            document.addEventListener('DOMContentLoaded', function() {
                console.log('Patient management interface initialized');
                
                const addPatientBtn = document.getElementById('add-patient-btn');
                const addPatientModal = document.getElementById('add-patient-modal');
                const closeModal = document.getElementById('close-modal');
                const cancelBtn = document.getElementById('cancel-btn');
                const addPatientForm = document.getElementById('add-patient-form');
                const patientSearch = document.getElementById('patient-search');
                
                // Show add patient modal
                addPatientBtn.addEventListener('click', function() {
                    addPatientModal.classList.remove('hidden');
                });
                
                // Hide modal
                function hideModal() {
                    addPatientModal.classList.add('hidden');
                    addPatientForm.reset();
                }
                
                closeModal.addEventListener('click', hideModal);
                cancelBtn.addEventListener('click', hideModal);
                
                // Handle form submission
                addPatientForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    alert('Patient would be saved to database');
                    hideModal();
                });
                
                // Handle patient search
                patientSearch.addEventListener('input', function() {
                    const searchTerm = this.value.toLowerCase();
                    // Implement search functionality
                    console.log('Searching for:', searchTerm);
                });
            });
        </script>
    </body>
    </html>
    '''