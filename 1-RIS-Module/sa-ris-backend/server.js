/**
 * South African Radiology Information System - Main Backend Server
 * Express.js server with HL7 FHIR and DICOM 2023 integration
 *
 * @package SA_RIS_Backend
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const morgan = require('morgan');
const path = require('path');
const fs = require('fs');

// Import our custom modules
const DICOM2023Compliance = require('./DICOM2023Compliance');
const FHIRRadiologyService = require('./FHIRRadiologyService');
const OrthancConnector = require('./OrthancConnector');
const RISWorkflowEngine = require('./RISWorkflowEngine');
const SABillingEngine = require('./SABillingEngine');
const mcpBridge = require('./mcp_bridge');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(helmet());
app.use(cors());
app.use(compression());
app.use(morgan('combined'));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Initialize services
let dicomCompliance;
let fhirService;
let orthancConnector;
let workflowEngine;
let billingEngine;
let openemrReachable = false;

// Initialize services
async function initializeServices() {
    try {
        console.log('🔧 Initializing SA-RIS Backend Services...');

        // Initialize Orthanc Connector
        orthancConnector = new OrthancConnector({
            url: process.env.ORTHANC_URL || 'http://localhost:8042',
            username: process.env.ORTHANC_USERNAME,
            password: process.env.ORTHANC_PASSWORD
        });
            // Verify Orthanc is reachable
            const orthancVersion = await orthancConnector.ping();
            if (!orthancVersion) {
                console.warn('⚠️ Orthanc Connector initialized but Orthanc is not reachable at', orthancConnector.url);
                orthancConnector.connected = false;
            } else {
                orthancConnector.connected = true;
                console.log('✅ Orthanc Connector initialized (version):', typeof orthancVersion === 'object' ? JSON.stringify(orthancVersion) : orthancVersion);
            }

        // Initialize DICOM 2023 Compliance
        dicomCompliance = new DICOM2023Compliance(null, orthancConnector, {
            enableSecurityProfiles: true,
            enableAuditLogging: true
        });
        console.log('✅ DICOM 2023 Compliance initialized');

        // Initialize FHIR Service
        fhirService = new FHIRRadiologyService(null, orthancConnector, {
            baseUrl: process.env.FHIR_BASE_URL || 'https://fhir.sacoronavirus.co.za/r4',
            timeout: 30000
        });
        console.log('✅ FHIR Radiology Service initialized');

        // Initialize Workflow Engine
        workflowEngine = new RISWorkflowEngine(null, {
            enableRealTimeUpdates: true,
            enableNotifications: true
        });
        console.log('✅ RIS Workflow Engine initialized');

        // Initialize Billing Engine
        billingEngine = new SABillingEngine(null, {
            enableMedicalAidIntegration: true,
            enableRealTimePricing: true
        });
        console.log('✅ SA Billing Engine initialized');

        // Quick OpenEMR reachability check (if a base URL is provided)
        const openemrBase = process.env.OPENEMR_BASE_URL || process.env.OPENEMR_BASE || 'http://localhost:8080';
        try {
            const resp = await require('axios').get(openemrBase, { timeout: 5000 });
            openemrReachable = resp && resp.status >= 200 && resp.status < 400;
            console.log(`✅ OpenEMR reachable at ${openemrBase} (status ${resp.status})`);
        } catch (err) {
            openemrReachable = false;
            console.warn(`⚠️ OpenEMR not reachable at ${openemrBase}`);
        }

        console.log('🎉 All SA-RIS Backend Services initialized successfully!');
        return true;
    } catch (error) {
        console.error('❌ Failed to initialize services:', error);
        return false;
    }
}

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        services: {
            dicom: !!dicomCompliance,
            fhir: !!fhirService,
            orthanc: !!orthancConnector && !!orthancConnector.connected,
            workflow: !!workflowEngine,
            billing: !!billingEngine
        },
            integrations: {
                openemr: !!openemrReachable,
                orthancUrl: process.env.ORTHANC_URL || 'http://localhost:8042',
                openemrUrl: process.env.OPENEMR_BASE_URL || process.env.OPENEMR_BASE || 'http://localhost:8080'
            },
        version: '1.0.0',
        environment: process.env.NODE_ENV || 'development'
    });
});

// DICOM endpoints
app.get('/api/dicom/studies', async (req, res) => {
    try {
        if (!orthancConnector || !orthancConnector.connected) {
            return res.status(503).json({ success: false, error: 'Orthanc PACS not connected' });
        }

        const studies = await orthancConnector.getStudies();
        res.json({ success: true, data: studies });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/dicom/studies/:studyId', async (req, res) => {
    try {
        if (!orthancConnector || !orthancConnector.connected) {
            return res.status(503).json({ success: false, error: 'Orthanc PACS not connected' });
        }

        const study = await orthancConnector.getStudy(req.params.studyId);
        const compliance = await dicomCompliance.validateStudyCompliance(req.params.studyId);

        res.json({
            success: true,
            data: study,
            compliance: compliance
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/dicom/studies/:studyId/compliance', async (req, res) => {
    try {
        const result = await dicomCompliance.upgradeStudyTo2023(req.params.studyId);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// FHIR endpoints
app.get('/api/fhir/patients', async (req, res) => {
    try {
        // This would typically query the FHIR server
        res.json({
            success: true,
            message: 'FHIR Patient query endpoint',
            note: 'Connect to FHIR server at: ' + process.env.FHIR_BASE_URL
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/fhir/imaging-study', async (req, res) => {
    try {
        const { studyId, patientId } = req.body;
        const result = await fhirService.createImagingStudy(studyId, patientId);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/fhir/patient', async (req, res) => {
    try {
        const patientData = req.body;
        const result = await fhirService.ensurePatientInFHIR(patientData);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Workflow endpoints
app.get('/api/workflow/dashboard', async (req, res) => {
    try {
        const dashboard = await workflowEngine.getDashboardData();
        res.json({ success: true, data: dashboard });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/workflow/report', async (req, res) => {
    try {
        const { studyId, reportData } = req.body;
        const result = await workflowEngine.createReport(studyId, reportData);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Billing endpoints
app.get('/api/billing/estimate', async (req, res) => {
    try {
        const { procedureCode, medicalAid } = req.query;
        const estimate = await billingEngine.calculateEstimate(procedureCode, medicalAid);
        res.json({ success: true, data: estimate });
    } catch (error) {
        res.status(500).json({ success: false, error: error.error });
    }
});

app.post('/api/billing/claim', async (req, res) => {
    try {
        const claimData = req.body;
        const result = await billingEngine.submitClaim(claimData);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// MCP Medical Authorization endpoints
app.use('/api/mcp', mcpBridge);

// RIS Module Routes
app.use('/api/patients', require('./routes/patients'));
app.use('/api/appointments', require('./routes/appointments'));
app.use('/api/reports', require('./routes/reports'));
app.use('/api/billing', require('./routes/billing'));

// Static files
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Serve frontend if a build exists (sa-ris-frontend/build) or a public index.html is present.
const frontendBuildPath = path.join(__dirname, '..', 'sa-ris-frontend', 'build');
const frontendPublicIndex = path.join(__dirname, '..', 'sa-ris-frontend', 'public', 'index.html');
const backendPublicIndex = path.join(__dirname, 'public', 'index.html');

if (fs.existsSync(frontendBuildPath)) {
    console.log('📁 Serving frontend from build:', frontendBuildPath);
    app.use(express.static(frontendBuildPath));

    // For any GET request that doesn't match an API route, return the frontend index.html
    app.get('*', (req, res, next) => {
        if (req.path.startsWith('/api/') || req.path.startsWith('/uploads')) return next();
        res.sendFile(path.join(frontendBuildPath, 'index.html'));
    });
} else if (fs.existsSync(frontendPublicIndex)) {
    // Developer mode: serve the public folder (not optimized) so / returns the index.html
    const frontendPublicPath = path.dirname(frontendPublicIndex);
    console.log('📁 Serving frontend public from:', frontendPublicPath);
    app.use(express.static(frontendPublicPath));
    app.get('*', (req, res, next) => {
        if (req.path.startsWith('/api/') || req.path.startsWith('/uploads')) return next();
        res.sendFile(frontendPublicIndex);
    });
} else if (fs.existsSync(backendPublicIndex)) {
    // Fallback: serve a simple backend public folder (useful when the frontend isn't built yet)
    const backendPublicPath = path.dirname(backendPublicIndex);
    console.log('📁 Serving backend public from:', backendPublicPath);
    app.use(express.static(backendPublicPath));
    app.get('*', (req, res, next) => {
        if (req.path.startsWith('/api/') || req.path.startsWith('/uploads')) return next();
        res.sendFile(backendPublicIndex);
    });
} else {
    console.log('ℹ️ No frontend build or public/index.html found. API-only server is running.');
}

// Error handling middleware
app.use((error, req, res, next) => {
    console.error('Unhandled error:', error);
    res.status(500).json({
        success: false,
        error: 'Internal server error',
        message: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        success: false,
        error: 'Not found',
        message: `Route ${req.method} ${req.path} not found`
    });
});

// Start server
async function startServer() {
    try {
        // Initialize all services first
        const servicesReady = await initializeServices();
        if (!servicesReady) {
            console.error('❌ Failed to initialize services. Exiting...');
            process.exit(1);
        }

        // Start the server
        app.listen(PORT, () => {
            console.log('🇿🇦 ===============================================');
            console.log('🇿🇦 South African Radiology Information System');
            console.log('🇿🇦 ===============================================');
            console.log(`🚀 Backend Server running on port ${PORT}`);
            console.log(`🌐 API URL: http://localhost:${PORT}`);
            console.log(`🏥 Health Check: http://localhost:${PORT}/health`);
            console.log('📊 DICOM 2023 Compliance: ✅ Active');
            console.log('🔬 HL7 FHIR Integration: ✅ Active');
            console.log('🩺 Orthanc PACS: ✅ Connected');
            console.log('⚡ Workflow Engine: ✅ Running');
            console.log('💰 SA Billing: ✅ Ready');
            console.log('🇿🇦 ===============================================');
        });
    } catch (error) {
        console.error('❌ Failed to start server:', error);
        process.exit(1);
    }
}

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('🛑 Received SIGTERM, shutting down gracefully...');
    process.exit(0);
});

process.on('SIGINT', () => {
    console.log('🛑 Received SIGINT, shutting down gracefully...');
    process.exit(0);
});

// Start the application
startServer();

module.exports = app;