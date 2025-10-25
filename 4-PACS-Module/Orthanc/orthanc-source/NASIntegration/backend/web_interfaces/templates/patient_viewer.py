#!/usr/bin/env python3
"""
🇿🇦 Patient Viewer Interface Template
Patient management and viewing interface with SA healthcare features
"""

PATIENT_VIEWER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🇿🇦 Patient Viewer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .main-container { 
            background: rgba(255, 255, 255, 0.95); 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
            margin: 20px auto; 
            padding: 30px; 
            max-width: 1400px;
        }
        .header-section {
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .search-section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .patient-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .patient-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 5px solid #28a745;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .patient-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }
        .patient-card.selected {
            border-left-color: #007bff;
            background: #f8f9ff;
        }
        .patient-header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 15px;
        }
        .patient-name {
            font-size: 1.3rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .patient-id {
            color: #666;
            font-size: 0.9rem;
            font-family: monospace;
        }
        .patient-details {
            margin-bottom: 15px;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }
        .detail-label {
            font-weight: 500;
            color: #555;
        }
        .detail-value {
            color: #333;
        }
        .sa-info {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 15px;
        }
        .sa-info h6 {
            color: #856404;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }
        .medical-aid-badge {
            background: #17a2b8;
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
        }
        .study-list {
            margin-top: 15px;
        }
        .study-item {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .study-info {
            flex: 1;
        }
        .study-title {
            font-weight: 500;
            color: #333;
            margin-bottom: 3px;
        }
        .study-meta {
            font-size: 0.8rem;
            color: #666;
        }
        .study-actions {
            display: flex;
            gap: 5px;
        }
        .btn-study {
            padding: 4px 8px;
            font-size: 0.8rem;
            border-radius: 4px;
        }
        .patient-actions {
            display: flex;
            gap: 8px;
            margin-top: 15px;
        }
        .btn-patient {
            flex: 1;
            padding: 8px;
            font-size: 0.9rem;
            border-radius: 6px;
        }
        .filters-section {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .filter-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .stats-bar {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-around;
            text-align: center;
        }
        .stat-item {
            flex: 1;
        }
        .stat-number {
            font-size: 1.5rem;
            font-weight: bold;
            color: #28a745;
        }
        .stat-label {
            font-size: 0.9rem;
            color: #666;
        }
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .loading-content {
            background: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
        }
        .nav-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .language-selector {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 20px;
        }
        .language-btn {
            background: #ffc107;
            border: none;
            color: #212529;
            padding: 5px 10px;
            border-radius: 4px;
            margin-right: 5px;
            font-size: 0.8rem;
            cursor: pointer;
        }
        .language-btn:hover {
            background: #e0a800;
        }
        .language-btn.active {
            background: #d39e00;
        }
        @media (max-width: 768px) {
            .patient-grid {
                grid-template-columns: 1fr;
            }
            .filters-section {
                flex-direction: column;
                align-items: stretch;
            }
            .stats-bar {
                flex-direction: column;
                gap: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- Header -->
        <div class="header-section">
            <h1><i class="fas fa-user-injured"></i> 🇿🇦 Patient Management System</h1>
            <p class="mb-0">Comprehensive patient viewing and management for SA healthcare</p>
        </div>

        <!-- Navigation -->
        <div class="nav-buttons">
            <a href="/" class="btn btn-outline-primary"><i class="fas fa-home"></i> Home</a>
            <a href="/orthanc-server" class="btn btn-outline-secondary"><i class="fas fa-server"></i> Server</a>
            <a href="/dicom-viewer" class="btn btn-outline-info"><i class="fas fa-eye"></i> DICOM Viewer</a>
            <a href="/user-management" class="btn btn-outline-warning"><i class="fas fa-users"></i> Users</a>
            <button class="btn btn-outline-success" onclick="addNewPatient()"><i class="fas fa-plus"></i> Add Patient</button>
            <button class="btn btn-outline-dark" onclick="refreshPatients()"><i class="fas fa-sync-alt"></i> Refresh</button>
        </div>

        <!-- Language Selector -->
        <div class="language-selector">
            <h6><i class="fas fa-language"></i> Language / Taal / Ulimi</h6>
            <button class="language-btn active" onclick="setLanguage('en')">English</button>
            <button class="language-btn" onclick="setLanguage('af')">Afrikaans</button>
            <button class="language-btn" onclick="setLanguage('zu')">isiZulu</button>
            <button class="language-btn" onclick="setLanguage('xh')">isiXhosa</button>
            <button class="language-btn" onclick="setLanguage('st')">Sesotho</button>
            <button class="language-btn" onclick="setLanguage('tn')">Setswana</button>
        </div>

        <!-- Statistics Bar -->
        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-number" id="totalPatients">--</div>
                <div class="stat-label">Total Patients</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="activeStudies">--</div>
                <div class="stat-label">Active Studies</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="todayScans">--</div>
                <div class="stat-label">Today's Scans</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="medicalAidPatients">--</div>
                <div class="stat-label">Medical Aid</div>
            </div>
        </div>

        <!-- Search and Filters -->
        <div class="search-section">
            <div class="row">
                <div class="col-md-6">
                    <div class="input-group">
                        <span class="input-group-text"><i class="fas fa-search"></i></span>
                        <input type="text" class="form-control" placeholder="Search patients by name, ID, or medical aid..." 
                               id="patientSearch" onkeyup="searchPatients()">
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="filters-section">
                        <div class="filter-group">
                            <label class="form-label mb-0">Medical Aid:</label>
                            <select class="form-select form-select-sm" id="medicalAidFilter" onchange="filterPatients()">
                                <option value="">All Medical Aids</option>
                                <option value="Discovery Health">Discovery Health</option>
                                <option value="Bonitas Medical Fund">Bonitas</option>
                                <option value="Momentum Health">Momentum</option>
                                <option value="Medihelp">Medihelp</option>
                                <option value="Bestmed">Bestmed</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label class="form-label mb-0">Gender:</label>
                            <select class="form-select form-select-sm" id="genderFilter" onchange="filterPatients()">
                                <option value="">All</option>
                                <option value="M">Male</option>
                                <option value="F">Female</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Patient Grid -->
        <div class="patient-grid" id="patientGrid">
            <!-- Patients will be loaded here -->
        </div>

        <!-- Loading Overlay -->
        <div class="loading-overlay" id="loadingOverlay">
            <div class="loading-content">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <h5>Loading Patients</h5>
                <p>Please wait while we fetch patient data...</p>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Global state
        let allPatients = [];
        let filteredPatients = [];
        let currentLanguage = 'en';
        let selectedPatient = null;

        // Language translations
        const translations = {
            en: {
                totalPatients: 'Total Patients',
                activeStudies: 'Active Studies',
                todayScans: "Today's Scans",
                medicalAidPatients: 'Medical Aid',
                searchPlaceholder: 'Search patients by name, ID, or medical aid...',
                viewStudies: 'View Studies',
                viewDicom: 'View DICOM',
                editPatient: 'Edit Patient',
                patientDetails: 'Patient Details'
            },
            af: {
                totalPatients: 'Totale Pasiënte',
                activeStudies: 'Aktiewe Studies',
                todayScans: 'Vandag se Skanderings',
                medicalAidPatients: 'Mediese Fonds',
                searchPlaceholder: 'Soek pasiënte volgens naam, ID, of mediese fonds...',
                viewStudies: 'Bekyk Studies',
                viewDicom: 'Bekyk DICOM',
                editPatient: 'Wysig Pasiënt',
                patientDetails: 'Pasiënt Besonderhede'
            },
            zu: {
                totalPatients: 'Iziguli Zonke',
                activeStudies: 'Izifundo Ezisebenzayo',
                todayScans: 'Ukuskena Kwanamuhla',
                medicalAidPatients: 'Usizo Lwezempilo',
                searchPlaceholder: 'Sesha iziguli ngegama, i-ID, noma usizo lwezempilo...',
                viewStudies: 'Buka Izifundo',
                viewDicom: 'Buka i-DICOM',
                editPatient: 'Hlela Isiguli',
                patientDetails: 'Imininingwane Yesiguli'
            }
        };

        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {
            loadPatients();
            updateLanguage();
        });

        // Load patients (demo data for now)
        function loadPatients() {
            showLoading();
            
            // Simulate API call
            setTimeout(() => {
                const demoPatients = [
                    {
                        id: 'pat001',
                        name: 'Sipho Mthembu',
                        patientId: '8501015800089',
                        birthDate: '1985-01-01',
                        age: 40,
                        gender: 'M',
                        medicalAid: 'Discovery Health',
                        memberNumber: 'DH123456789',
                        phone: '+27 82 123 4567',
                        address: 'Johannesburg, Gauteng',
                        language: 'zu',
                        studies: [
                            {
                                id: 'study001',
                                date: '2025-01-13',
                                description: 'Chest X-Ray',
                                modality: 'CR',
                                status: 'Completed'
                            },
                            {
                                id: 'study002',
                                date: '2025-01-10',
                                description: 'CT Abdomen',
                                modality: 'CT',
                                status: 'In Progress'
                            }
                        ]
                    },
                    {
                        id: 'pat002',
                        name: 'Nomsa Dlamini',
                        patientId: '9203127890123',
                        birthDate: '1992-03-12',
                        age: 32,
                        gender: 'F',
                        medicalAid: 'Bonitas Medical Fund',
                        memberNumber: 'BM987654321',
                        phone: '+27 83 987 6543',
                        address: 'Durban, KwaZulu-Natal',
                        language: 'zu',
                        studies: [
                            {
                                id: 'study003',
                                date: '2025-01-12',
                                description: 'Mammography',
                                modality: 'MG',
                                status: 'Completed'
                            }
                        ]
                    },
                    {
                        id: 'pat003',
                        name: 'Pieter van der Merwe',
                        patientId: '7508201234567',
                        birthDate: '1975-08-20',
                        age: 49,
                        gender: 'M',
                        medicalAid: 'Momentum Health',
                        memberNumber: 'MH456789123',
                        phone: '+27 21 555 0123',
                        address: 'Cape Town, Western Cape',
                        language: 'af',
                        studies: [
                            {
                                id: 'study004',
                                date: '2025-01-11',
                                description: 'MRI Brain',
                                modality: 'MR',
                                status: 'Completed'
                            }
                        ]
                    },
                    {
                        id: 'pat004',
                        name: 'Thandiwe Nkomo',
                        patientId: '8807159876543',
                        birthDate: '1988-07-15',
                        age: 36,
                        gender: 'F',
                        medicalAid: 'Medihelp',
                        memberNumber: 'MH789123456',
                        phone: '+27 11 444 5678',
                        address: 'Pretoria, Gauteng',
                        language: 'st',
                        studies: [
                            {
                                id: 'study005',
                                date: '2025-01-13',
                                description: 'Ultrasound Abdomen',
                                modality: 'US',
                                status: 'Scheduled'
                            }
                        ]
                    }
                ];
                
                allPatients = demoPatients;
                filteredPatients = [...allPatients];
                displayPatients();
                updateStatistics();
                hideLoading();
            }, 1500);
        }

        // Display patients
        function displayPatients() {
            const grid = document.getElementById('patientGrid');
            
            if (filteredPatients.length === 0) {
                grid.innerHTML = `
                    <div class="col-12">
                        <div class="alert alert-info text-center">
                            <i class="fas fa-info-circle"></i>
                            No patients found matching your criteria.
                        </div>
                    </div>
                `;
                return;
            }
            
            let html = '';
            filteredPatients.forEach(patient => {
                const t = translations[currentLanguage];
                html += `
                    <div class="patient-card" onclick="selectPatient('${patient.id}')">
                        <div class="patient-header">
                            <div>
                                <div class="patient-name">${patient.name}</div>
                                <div class="patient-id">ID: ${patient.patientId}</div>
                            </div>
                            <div class="text-end">
                                <span class="medical-aid-badge">${patient.medicalAid}</span>
                            </div>
                        </div>
                        
                        <div class="patient-details">
                            <div class="detail-row">
                                <span class="detail-label">Age:</span>
                                <span class="detail-value">${patient.age} years</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Gender:</span>
                                <span class="detail-value">${patient.gender === 'M' ? 'Male' : 'Female'}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Phone:</span>
                                <span class="detail-value">${patient.phone}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Address:</span>
                                <span class="detail-value">${patient.address}</span>
                            </div>
                        </div>
                        
                        <div class="sa-info">
                            <h6><i class="fas fa-flag"></i> SA Healthcare Info</h6>
                            <div class="detail-row">
                                <span class="detail-label">Medical Aid:</span>
                                <span class="detail-value">${patient.medicalAid}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Member #:</span>
                                <span class="detail-value">${patient.memberNumber}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Language:</span>
                                <span class="detail-value">${getLanguageName(patient.language)}</span>
                            </div>
                        </div>
                        
                        <div class="study-list">
                            <h6><i class="fas fa-clipboard-list"></i> Recent Studies (${patient.studies.length})</h6>
                            ${patient.studies.map(study => `
                                <div class="study-item">
                                    <div class="study-info">
                                        <div class="study-title">${study.description}</div>
                                        <div class="study-meta">${study.date} | ${study.modality} | ${study.status}</div>
                                    </div>
                                    <div class="study-actions">
                                        <button class="btn btn-outline-primary btn-study" onclick="viewStudy('${study.id}', event)">
                                            <i class="fas fa-eye"></i>
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        
                        <div class="patient-actions">
                            <button class="btn btn-primary btn-patient" onclick="viewPatientStudies('${patient.id}', event)">
                                <i class="fas fa-clipboard-list"></i> ${t.viewStudies}
                            </button>
                            <button class="btn btn-success btn-patient" onclick="viewPatientDicom('${patient.id}', event)">
                                <i class="fas fa-eye"></i> ${t.viewDicom}
                            </button>
                            <button class="btn btn-outline-secondary btn-patient" onclick="editPatient('${patient.id}', event)">
                                <i class="fas fa-edit"></i> ${t.editPatient}
                            </button>
                        </div>
                    </div>
                `;
            });
            
            grid.innerHTML = html;
        }

        // Search patients
        function searchPatients() {
            const query = document.getElementById('patientSearch').value.toLowerCase();
            
            if (!query.trim()) {
                filteredPatients = [...allPatients];
            } else {
                filteredPatients = allPatients.filter(patient => 
                    patient.name.toLowerCase().includes(query) ||
                    patient.patientId.includes(query) ||
                    patient.medicalAid.toLowerCase().includes(query) ||
                    patient.phone.includes(query) ||
                    patient.address.toLowerCase().includes(query)
                );
            }
            
            applyFilters();
        }

        // Filter patients
        function filterPatients() {
            applyFilters();
        }

        // Apply all filters
        function applyFilters() {
            const medicalAidFilter = document.getElementById('medicalAidFilter').value;
            const genderFilter = document.getElementById('genderFilter').value;
            
            let filtered = [...filteredPatients];
            
            if (medicalAidFilter) {
                filtered = filtered.filter(patient => patient.medicalAid === medicalAidFilter);
            }
            
            if (genderFilter) {
                filtered = filtered.filter(patient => patient.gender === genderFilter);
            }
            
            filteredPatients = filtered;
            displayPatients();
            updateStatistics();
        }

        // Update statistics
        function updateStatistics() {
            document.getElementById('totalPatients').textContent = allPatients.length;
            document.getElementById('activeStudies').textContent = allPatients.reduce((sum, p) => sum + p.studies.length, 0);
            document.getElementById('todayScans').textContent = allPatients.reduce((sum, p) => 
                sum + p.studies.filter(s => s.date === '2025-01-13').length, 0);
            document.getElementById('medicalAidPatients').textContent = allPatients.filter(p => p.medicalAid).length;
        }

        // Patient actions
        function selectPatient(patientId) {
            // Clear previous selection
            document.querySelectorAll('.patient-card').forEach(card => {
                card.classList.remove('selected');
            });
            
            // Select new patient
            event.target.closest('.patient-card').classList.add('selected');
            selectedPatient = allPatients.find(p => p.id === patientId);
        }

        function viewPatientStudies(patientId, event) {
            event.stopPropagation();
            const patient = allPatients.find(p => p.id === patientId);
            alert(`Viewing studies for ${patient.name}:\\n\\n${patient.studies.map(s => `• ${s.description} (${s.date})`).join('\\n')}`);
        }

        function viewPatientDicom(patientId, event) {
            event.stopPropagation();
            const patient = allPatients.find(p => p.id === patientId);
            // In a real implementation, this would open the DICOM viewer
            window.location.href = `/dicom-viewer?patient=${patientId}`;
        }

        function editPatient(patientId, event) {
            event.stopPropagation();
            const patient = allPatients.find(p => p.id === patientId);
            alert(`Edit patient: ${patient.name}\\n\\nThis would open a patient editing form.`);
        }

        function viewStudy(studyId, event) {
            event.stopPropagation();
            alert(`Opening study ${studyId} in DICOM viewer...`);
        }

        function addNewPatient() {
            alert('Add New Patient\\n\\nThis would open a form to register a new patient with SA healthcare requirements.');
        }

        function refreshPatients() {
            loadPatients();
        }

        // Language functions
        function setLanguage(lang) {
            currentLanguage = lang;
            
            // Update active button
            document.querySelectorAll('.language-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            updateLanguage();
            displayPatients();
        }

        function updateLanguage() {
            const t = translations[currentLanguage];
            
            // Update static text
            document.querySelector('[data-stat="totalPatients"]')?.textContent = t.totalPatients;
            document.querySelector('[data-stat="activeStudies"]')?.textContent = t.activeStudies;
            document.querySelector('[data-stat="todayScans"]')?.textContent = t.todayScans;
            document.querySelector('[data-stat="medicalAidPatients"]')?.textContent = t.medicalAidPatients;
            
            // Update placeholder
            const searchInput = document.getElementById('patientSearch');
            if (searchInput) {
                searchInput.placeholder = t.searchPlaceholder;
            }
        }

        function getLanguageName(code) {
            const names = {
                'en': 'English',
                'af': 'Afrikaans',
                'zu': 'isiZulu',
                'xh': 'isiXhosa',
                'st': 'Sesotho',
                'tn': 'Setswana'
            };
            return names[code] || 'English';
        }

        // Utility functions
        function showLoading() {
            document.getElementById('loadingOverlay').style.display = 'flex';
        }

        function hideLoading() {
            document.getElementById('loadingOverlay').style.display = 'none';
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                document.getElementById('patientSearch').focus();
            }
        });
    </script>
</body>
</html>
"""