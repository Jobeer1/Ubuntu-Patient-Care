/**
 * MCP Bridge - Connects SA-RIS Backend to MCP Medical Authorization Server
 * Provides REST API endpoints with mock data for medical authorization
 * 
 * Note: This is a mock implementation. In production, this would connect to
 * a real medical aid authorization system.
 */

const express = require('express');
const router = express.Router();

// Mock database for pre-auth requests
const preAuthRequests = [];
let preAuthIdCounter = 1000;

// Mock medical aid validation
function validateMedicalAid(memberNumber, schemeCode, idNumber) {
    // Mock validation - in production, this would call the actual medical aid API
    const mockMembers = {
        '123456789': {
            valid: true,
            member: {
                member_number: '123456789',
                full_name: 'John Nkosi',
                scheme_code: 'DISCOVERY',
                plan_code: 'EXEC',
                plan_name: 'Executive Plan',
                status: 'active',
                dependants: 3
            }
        },
        '987654321': {
            valid: true,
            member: {
                member_number: '987654321',
                full_name: 'Sarah Zulu',
                scheme_code: 'MOMENTUM',
                plan_code: 'EXTENDER',
                plan_name: 'Extender Plan',
                status: 'active',
                dependants: 2
            }
        }
    };

    const result = mockMembers[memberNumber];
    if (result && result.member.scheme_code === schemeCode) {
        return result;
    }

    return {
        valid: false,
        error: 'Invalid member number or scheme code'
    };
}

// Mock pre-auth requirements check
function checkPreAuthRequirements(schemeCode, planCode, procedureCode) {
    // Mock requirements - in production, this would check actual scheme rules
    const requiresPreAuth = ['CT', 'MRI', 'PET'].some(mod => procedureCode.includes(mod));
    
    return {
        requires_preauth: requiresPreAuth,
        procedure_code: procedureCode,
        scheme_code: schemeCode,
        plan_code: planCode,
        typical_turnaround: requiresPreAuth ? '24-48 hours' : 'N/A',
        required_documents: requiresPreAuth ? [
            'Clinical indication',
            'Previous imaging reports',
            'Referring doctor details'
        ] : []
    };
}

// Mock cost estimation
function estimatePatientCost(memberNumber, schemeCode, procedureCode) {
    // Mock cost calculation - in production, this would use actual tariff codes
    const baseCosts = {
        'CT': 3500,
        'MRI': 5500,
        'XRAY': 450,
        'ULTRASOUND': 850,
        'PET': 12000
    };

    let totalCost = 0;
    for (const [key, cost] of Object.entries(baseCosts)) {
        if (procedureCode.includes(key)) {
            totalCost = cost;
            break;
        }
    }

    if (totalCost === 0) totalCost = 1000; // Default

    const medicalAidPortion = totalCost * 0.8; // 80% covered
    const patientPortion = totalCost * 0.2; // 20% co-payment

    return {
        total_cost: totalCost,
        medical_aid_portion: medicalAidPortion,
        patient_portion: patientPortion,
        currency: 'ZAR',
        procedure_code: procedureCode,
        member_number: memberNumber
    };
}

// Mock pre-auth request creation
function createPreAuthRequest(data) {
    const preAuthId = `PA${preAuthIdCounter++}`;
    const request = {
        preauth_id: preAuthId,
        patient_id: data.patient_id,
        member_number: data.member_number,
        scheme_code: data.scheme_code,
        procedure_code: data.procedure_code,
        clinical_indication: data.clinical_indication,
        icd10_codes: data.icd10_codes || [],
        urgency: data.urgency || 'routine',
        status: 'queued',
        created_at: new Date().toISOString(),
        estimated_turnaround: '24-48 hours'
    };

    preAuthRequests.push(request);

    return {
        success: true,
        preauth_id: preAuthId,
        status: 'queued',
        message: 'Pre-authorization request created successfully',
        estimated_turnaround: '24-48 hours'
    };
}

// Mock pre-auth status check
function checkPreAuthStatus(preAuthId) {
    const request = preAuthRequests.find(r => r.preauth_id === preAuthId);
    
    if (!request) {
        return {
            found: false,
            error: 'Pre-authorization request not found'
        };
    }

    return {
        found: true,
        preauth_id: preAuthId,
        status: request.status,
        created_at: request.created_at,
        procedure_code: request.procedure_code,
        estimated_turnaround: request.estimated_turnaround
    };
}

// Mock list pending pre-auths
function listPendingPreAuths(status = 'queued') {
    const filtered = preAuthRequests.filter(r => r.status === status);
    
    return {
        requests: filtered,
        total: filtered.length
    };
}

// REST API Endpoints

/**
 * POST /api/mcp/validate-medical-aid
 * Validate medical aid member
 */
router.post('/validate-medical-aid', (req, res) => {
    try {
        const { member_number, scheme_code, id_number } = req.body;

        if (!member_number || !scheme_code) {
            return res.status(400).json({
                success: false,
                error: 'member_number and scheme_code are required'
            });
        }

        const result = validateMedicalAid(member_number, scheme_code, id_number);

        res.json({
            success: true,
            data: result
        });
    } catch (error) {
        console.error('Validate medical aid error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * POST /api/mcp/validate-preauth-requirements
 * Check if procedure requires pre-authorization
 */
router.post('/validate-preauth-requirements', (req, res) => {
    try {
        const { scheme_code, plan_code, procedure_code } = req.body;

        if (!scheme_code || !plan_code || !procedure_code) {
            return res.status(400).json({
                success: false,
                error: 'scheme_code, plan_code, and procedure_code are required'
            });
        }

        const result = checkPreAuthRequirements(scheme_code, plan_code, procedure_code);

        res.json({
            success: true,
            data: result
        });
    } catch (error) {
        console.error('Validate preauth requirements error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * POST /api/mcp/estimate-patient-cost
 * Calculate patient portion for procedure
 */
router.post('/estimate-patient-cost', (req, res) => {
    try {
        const { member_number, scheme_code, procedure_code } = req.body;

        if (!member_number || !scheme_code || !procedure_code) {
            return res.status(400).json({
                success: false,
                error: 'member_number, scheme_code, and procedure_code are required'
            });
        }

        const result = estimatePatientCost(member_number, scheme_code, procedure_code);

        res.json({
            success: true,
            data: result
        });
    } catch (error) {
        console.error('Estimate patient cost error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * POST /api/mcp/create-preauth-request
 * Create pre-authorization request
 */
router.post('/create-preauth-request', (req, res) => {
    try {
        const {
            patient_id,
            member_number,
            scheme_code,
            procedure_code,
            clinical_indication,
            icd10_codes,
            urgency
        } = req.body;

        if (!patient_id || !member_number || !scheme_code || !procedure_code || !clinical_indication) {
            return res.status(400).json({
                success: false,
                error: 'Required fields missing'
            });
        }

        const result = createPreAuthRequest({
            patient_id,
            member_number,
            scheme_code,
            procedure_code,
            clinical_indication,
            icd10_codes: icd10_codes || [],
            urgency: urgency || 'routine'
        });

        res.json({
            success: true,
            data: result
        });
    } catch (error) {
        console.error('Create preauth request error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/mcp/check-preauth-status/:preauth_id
 * Check status of pre-authorization request
 */
router.get('/check-preauth-status/:preauth_id', (req, res) => {
    try {
        const { preauth_id } = req.params;

        const result = checkPreAuthStatus(preauth_id);

        res.json({
            success: true,
            data: result
        });
    } catch (error) {
        console.error('Check preauth status error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/mcp/list-pending-preauths
 * List all pending pre-authorization requests
 */
router.get('/list-pending-preauths', (req, res) => {
    try {
        const { status } = req.query;

        const result = listPendingPreAuths(status || 'queued');

        res.json({
            success: true,
            data: result
        });
    } catch (error) {
        console.error('List pending preauths error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/mcp/health
 * Check MCP server health
 */
router.get('/health', (req, res) => {
    res.json({
        success: true,
        mcp_ready: true,
        mcp_running: true,
        mode: 'mock',
        message: 'Mock MCP server is running'
    });
});

module.exports = router;
