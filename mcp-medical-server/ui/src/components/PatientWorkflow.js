import React, { useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Button,
  Card,
  CardContent,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Chip,
  LinearProgress,
  Divider,
} from '@mui/material';
import {
  Person,
  CameraAlt,
  Mic,
  Assignment,
  Send,
  CheckCircle,
  Error,
  LocalHospital,
} from '@mui/icons-material';
import toast from 'react-hot-toast';
import ReactJsonView from 'react-json-view';

const WORKFLOW_STEPS = [
  'Patient Identification',
  'Medical Documentation',
  'Procedure Selection', 
  'AI Analysis',
  'Pre-Authorization',
  'Approval'
];

const SAMPLE_PATIENTS = [
  {
    id: 'P001',
    name: 'John Smith',
    member_number: '12345678901',
    scheme_code: 'DISCOVERY',
    plan_code: 'EXEC'
  },
  {
    id: 'P002', 
    name: 'Sarah Johnson',
    member_number: '98765432109',
    scheme_code: 'MOMENTUM',
    plan_code: 'INGWE'
  },
  {
    id: 'P003',
    name: 'Michael Brown',
    member_number: '11122233344',
    scheme_code: 'BONITAS',
    plan_code: 'BONITAS_SELECT'
  }
];

const COMMON_PROCEDURES = [
  { code: '0190', name: 'CT Scan - Chest', cost: 'R2,500' },
  { code: '0191', name: 'MRI - Brain', cost: 'R4,200' },
  { code: '0015', name: 'Ultrasound - Abdominal', cost: 'R850' },
  { code: '0301', name: 'Arthroscopy - Knee', cost: 'R12,000' },
  { code: '0405', name: 'Cardiac Catheterization', cost: 'R18,500' }
];

function PatientWorkflow() {
  const [activeStep, setActiveStep] = useState(0);
  const [workflowData, setWorkflowData] = useState({
    patient: null,
    audio_transcription: '',
    clinical_indication: '',
    procedure_code: '',
    urgency: 'routine',
    files: {
      patient_photo: null,
      audio_dictation: null,
      id_card: null
    }
  });
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [workflowComplete, setWorkflowComplete] = useState(false);

  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleReset = () => {
    setActiveStep(0);
    setWorkflowData({
      patient: null,
      audio_transcription: '',
      clinical_indication: '',
      procedure_code: '',
      urgency: 'routine',
      files: {
        patient_photo: null,
        audio_dictation: null,
        id_card: null
      }
    });
    setResults([]);
    setWorkflowComplete(false);
  };

  const selectPatient = (patient) => {
    setWorkflowData(prev => ({
      ...prev,
      patient: patient
    }));
  };

  const updateWorkflowData = (field, value) => {
    setWorkflowData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const updateFileData = (fileType, file) => {
    setWorkflowData(prev => ({
      ...prev,
      files: {
        ...prev.files,
        [fileType]: file
      }
    }));
  };

  const executeWorkflowStep = async (stepName, toolName, data) => {
    try {
      const response = await fetch('/api/mcp/call-tool', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: toolName,
          arguments: data
        })
      });

      const result = await response.json();
      
      setResults(prev => [...prev, {
        step: stepName,
        tool: toolName,
        data: data,
        result: result,
        timestamp: new Date().toISOString(),
        status: response.ok ? 'success' : 'error'
      }]);

      return response.ok ? result : null;
    } catch (error) {
      console.error(`Step ${stepName} failed:`, error);
      setResults(prev => [...prev, {
        step: stepName,
        tool: toolName,
        data: data,
        result: { error: error.message },
        timestamp: new Date().toISOString(),
        status: 'error'
      }]);
      return null;
    }
  };

  const runCompleteWorkflow = async () => {
    if (!workflowData.patient || !workflowData.clinical_indication || !workflowData.procedure_code) {
      toast.error('Please complete all required fields');
      return;
    }

    setLoading(true);
    try {
      // Step 1: Validate Medical Aid
      toast.info('Step 1: Validating medical aid membership...');
      const validationResult = await executeWorkflowStep(
        'Validate Medical Aid',
        'validate_medical_aid',
        {
          member_number: workflowData.patient.member_number,
          scheme_code: workflowData.patient.scheme_code
        }
      );

      if (!validationResult || !validationResult.valid) {
        toast.error('Medical aid validation failed');
        return;
      }

      // Step 2: Check Pre-auth Requirements
      toast.info('Step 2: Checking pre-authorization requirements...');
      const preAuthCheck = await executeWorkflowStep(
        'Check Pre-auth Requirements',
        'validate_preauth_requirements',
        {
          scheme_code: workflowData.patient.scheme_code,
          plan_code: workflowData.patient.plan_code,
          procedure_code: workflowData.procedure_code
        }
      );

      // Step 3: Estimate Patient Cost
      toast.info('Step 3: Calculating patient costs...');
      const costEstimate = await executeWorkflowStep(
        'Estimate Patient Cost',
        'estimate_patient_cost',
        {
          member_number: workflowData.patient.member_number,
          scheme_code: workflowData.patient.scheme_code,
          procedure_code: workflowData.procedure_code
        }
      );

      // Step 4: Claude AI Analysis
      toast.info('Step 4: Getting Claude AI analysis...');
      const aiAnalysis = await fetch('/api/ai-brain/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: `Analyze this pre-authorization request and provide approval probability`,
          context: {
            patient: workflowData.patient,
            procedure_code: workflowData.procedure_code,
            clinical_indication: workflowData.clinical_indication,
            urgency: workflowData.urgency,
            validation_result: validationResult,
            cost_estimate: costEstimate
          }
        })
      });

      const aiResult = await aiAnalysis.json();
      setResults(prev => [...prev, {
        step: 'Claude AI Analysis',
        tool: 'claude_analysis',
        data: { query: 'Pre-auth analysis', context: workflowData },
        result: aiResult,
        timestamp: new Date().toISOString(),
        status: aiAnalysis.ok ? 'success' : 'error'
      }]);

      // Step 5: Create Pre-authorization Request
      toast.info('Step 5: Creating pre-authorization request...');
      const preAuthResult = await executeWorkflowStep(
        'Create Pre-authorization',
        'create_preauth_request',
        {
          patient_id: workflowData.patient.id,
          member_number: workflowData.patient.member_number,
          scheme_code: workflowData.patient.scheme_code,
          procedure_code: workflowData.procedure_code,
          clinical_indication: workflowData.clinical_indication,
          urgency: workflowData.urgency
        }
      );

      if (preAuthResult) {
        setWorkflowComplete(true);
        setActiveStep(WORKFLOW_STEPS.length);
        toast.success('Complete workflow executed successfully!');
      } else {
        toast.error('Pre-authorization creation failed');
      }

    } catch (error) {
      console.error('Workflow execution failed:', error);
      toast.error('Workflow execution failed');
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = (step) => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Select or Register Patient
            </Typography>
            <Grid container spacing={2}>
              {SAMPLE_PATIENTS.map((patient) => (
                <Grid item xs={12} md={4} key={patient.id}>
                  <Card 
                    sx={{ 
                      cursor: 'pointer',
                      border: workflowData.patient?.id === patient.id ? 2 : 1,
                      borderColor: workflowData.patient?.id === patient.id ? 'primary.main' : 'grey.300'
                    }}
                    onClick={() => selectPatient(patient)}
                  >
                    <CardContent>
                      <Typography variant="h6">{patient.name}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        ID: {patient.id}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Member: {patient.member_number}
                      </Typography>
                      <Chip label={patient.scheme_code} size="small" />
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        );

      case 1:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Upload Medical Documents
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                <Paper sx={{ p: 2, textAlign: 'center' }}>
                  <CameraAlt sx={{ fontSize: 48, color: 'grey.400', mb: 1 }} />
                  <Typography variant="subtitle1" gutterBottom>
                    Patient Photo
                  </Typography>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => updateFileData('patient_photo', e.target.files[0])}
                    style={{ width: '100%' }}
                  />
                  {workflowData.files.patient_photo && (
                    <Typography variant="caption" color="success.main">
                      ✓ Photo uploaded
                    </Typography>
                  )}
                </Paper>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <Paper sx={{ p: 2, textAlign: 'center' }}>
                  <Mic sx={{ fontSize: 48, color: 'grey.400', mb: 1 }} />
                  <Typography variant="subtitle1" gutterBottom>
                    Audio Dictation
                  </Typography>
                  <input
                    type="file"
                    accept="audio/*"
                    onChange={(e) => updateFileData('audio_dictation', e.target.files[0])}
                    style={{ width: '100%' }}
                  />
                  {workflowData.files.audio_dictation && (
                    <Typography variant="caption" color="success.main">
                      ✓ Audio uploaded
                    </Typography>
                  )}
                </Paper>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <Paper sx={{ p: 2, textAlign: 'center' }}>
                  <Assignment sx={{ fontSize: 48, color: 'grey.400', mb: 1 }} />
                  <Typography variant="subtitle1" gutterBottom>
                    ID Card/Document
                  </Typography>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => updateFileData('id_card', e.target.files[0])}
                    style={{ width: '100%' }}
                  />
                  {workflowData.files.id_card && (
                    <Typography variant="caption" color="success.main">
                      ✓ ID document uploaded
                    </Typography>
                  )}
                </Paper>
              </Grid>
            </Grid>
          </Box>
        );

      case 2:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Select Procedure and Clinical Details
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Procedure</InputLabel>
                  <Select
                    value={workflowData.procedure_code}
                    label="Procedure"
                    onChange={(e) => updateWorkflowData('procedure_code', e.target.value)}
                  >
                    {COMMON_PROCEDURES.map(proc => (
                      <MenuItem key={proc.code} value={proc.code}>
                        {proc.code} - {proc.name} ({proc.cost})
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Urgency</InputLabel>
                  <Select
                    value={workflowData.urgency}
                    label="Urgency"
                    onChange={(e) => updateWorkflowData('urgency', e.target.value)}
                  >
                    <MenuItem value="routine">Routine</MenuItem>
                    <MenuItem value="urgent">Urgent</MenuItem>
                    <MenuItem value="emergency">Emergency</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Clinical Indication"
                  placeholder="Describe the medical reason for this procedure..."
                  value={workflowData.clinical_indication}
                  onChange={(e) => updateWorkflowData('clinical_indication', e.target.value)}
                />
              </Grid>
            </Grid>
          </Box>
        );

      case 3:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              AI Analysis & Recommendations
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              Claude AI will analyze all the provided information and give recommendations for the pre-authorization.
            </Alert>
            
            <Card>
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  Analysis Summary:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Patient validation and eligibility check
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Procedure cost estimation and benefit calculations
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Clinical indication assessment
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Approval probability prediction
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Required documentation verification
                </Typography>
              </CardContent>
            </Card>
          </Box>
        );

      case 4:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Pre-Authorization Request
            </Typography>
            <Alert severity="warning" sx={{ mb: 2 }}>
              Ready to submit pre-authorization request. This will create an official request in the system.
            </Alert>
            
            <Card>
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  Request Summary:
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      <strong>Patient:</strong> {workflowData.patient?.name}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      <strong>Member No:</strong> {workflowData.patient?.member_number}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      <strong>Scheme:</strong> {workflowData.patient?.scheme_code}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      <strong>Procedure:</strong> {workflowData.procedure_code}
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2">
                      <strong>Clinical Indication:</strong> {workflowData.clinical_indication}
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Box>
        );

      case 5:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Final Approval
            </Typography>
            {workflowComplete ? (
              <Alert severity="success">
                Pre-authorization workflow completed successfully! 🎉
              </Alert>
            ) : (
              <Alert severity="info">
                Execute the complete workflow to see final results.
              </Alert>
            )}
          </Box>
        );

      default:
        return <Typography>Unknown step</Typography>;
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        🏥 Patient Workflow Simulator
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Simulate complete patient journeys from arrival to pre-authorization approval.
        This demonstrates the full MCP server capabilities with Claude AI integration.
      </Typography>

      <Grid container spacing={3}>
        {/* Workflow Stepper */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Stepper activeStep={activeStep} alternativeLabel>
              {WORKFLOW_STEPS.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </Paper>
        </Grid>

        {/* Step Content */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, minHeight: 400 }}>
            {loading && <LinearProgress sx={{ mb: 2 }} />}
            {renderStepContent(activeStep)}
            
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
              <Button
                disabled={activeStep === 0}
                onClick={handleBack}
              >
                Back
              </Button>
              
              <Box sx={{ display: 'flex', gap: 1 }}>
                {activeStep < WORKFLOW_STEPS.length - 1 ? (
                  <Button
                    variant="contained"
                    onClick={handleNext}
                    disabled={
                      (activeStep === 0 && !workflowData.patient) ||
                      (activeStep === 2 && (!workflowData.procedure_code || !workflowData.clinical_indication))
                    }
                  >
                    Next
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    color="success"
                    startIcon={<Send />}
                    onClick={runCompleteWorkflow}
                    disabled={loading}
                  >
                    Execute Complete Workflow
                  </Button>
                )}
                
                <Button
                  variant="outlined"
                  onClick={handleReset}
                >
                  Reset
                </Button>
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Workflow Progress */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Workflow Progress
            </Typography>
            
            {results.length === 0 ? (
              <Alert severity="info">
                No workflow steps executed yet.
              </Alert>
            ) : (
              <Box>
                {results.map((result, index) => (
                  <Box key={index} sx={{ mb: 2, p: 1, border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }}>
                    <Box display="flex" alignItems="center" gap={1}>
                      {result.status === 'success' ? 
                        <CheckCircle color="success" fontSize="small" /> : 
                        <Error color="error" fontSize="small" />
                      }
                      <Typography variant="body2" fontWeight="bold">
                        {result.step}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {result.tool} - {new Date(result.timestamp).toLocaleTimeString()}
                    </Typography>
                  </Box>
                ))}
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Results */}
        {results.length > 0 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Detailed Results
              </Typography>
              
              {results.map((result, index) => (
                <Box key={index} sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" color="primary" gutterBottom>
                    {result.step} ({result.tool})
                  </Typography>
                  <ReactJsonView
                    src={result.result}
                    theme="rjv-default"
                    collapsed={1}
                    displayDataTypes={false}
                    enableClipboard={true}
                    name={`result_${index}`}
                  />
                  {index < results.length - 1 && <Divider sx={{ mt: 2 }} />}
                </Box>
              ))}
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

export default PatientWorkflow;