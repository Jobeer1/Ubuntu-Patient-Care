import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  CardActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ExpandMore,
  PlayArrow,
  Stop,
  ContentCopy,
  CheckCircle,
  Error,
  Warning,
  Info,
} from '@mui/icons-material';
import ReactJsonView from 'react-json-view';
import toast from 'react-hot-toast';

const MCP_TOOLS = [
  {
    name: 'validate_medical_aid',
    title: 'Validate Medical Aid',
    description: 'Validate medical aid member (works offline)',
    category: 'validation',
    fields: [
      { name: 'member_number', type: 'text', required: true, placeholder: '12345678901' },
      { name: 'scheme_code', type: 'select', required: true, options: ['DISCOVERY', 'MOMENTUM', 'BONITAS', 'MEDSHIELD', 'BESTMED'] },
      { name: 'id_number', type: 'text', required: false, placeholder: '9001010001088' }
    ]
  },
  {
    name: 'validate_preauth_requirements',
    title: 'Validate Pre-auth Requirements',
    description: 'Check if procedure requires pre-authorization (offline)',
    category: 'validation',
    fields: [
      { name: 'scheme_code', type: 'select', required: true, options: ['DISCOVERY', 'MOMENTUM', 'BONITAS', 'MEDSHIELD', 'BESTMED'] },
      { name: 'plan_code', type: 'text', required: true, placeholder: 'EXEC' },
      { name: 'procedure_code', type: 'text', required: true, placeholder: '0190' }
    ]
  },
  {
    name: 'estimate_patient_cost',
    title: 'Estimate Patient Cost',
    description: 'Calculate patient portion for procedure (offline)',
    category: 'calculation',
    fields: [
      { name: 'member_number', type: 'text', required: true, placeholder: '12345678901' },
      { name: 'scheme_code', type: 'select', required: true, options: ['DISCOVERY', 'MOMENTUM', 'BONITAS', 'MEDSHIELD', 'BESTMED'] },
      { name: 'procedure_code', type: 'text', required: true, placeholder: '0190' }
    ]
  },
  {
    name: 'create_preauth_request',
    title: 'Create Pre-auth Request',
    description: 'Create pre-authorization request with validation',
    category: 'authorization',
    fields: [
      { name: 'patient_id', type: 'text', required: true, placeholder: 'P001' },
      { name: 'member_number', type: 'text', required: true, placeholder: '12345678901' },
      { name: 'scheme_code', type: 'select', required: true, options: ['DISCOVERY', 'MOMENTUM', 'BONITAS', 'MEDSHIELD', 'BESTMED'] },
      { name: 'procedure_code', type: 'text', required: true, placeholder: '0190' },
      { name: 'clinical_indication', type: 'textarea', required: true, placeholder: 'Patient presents with chest pain, requires CT scan' },
      { name: 'icd10_codes', type: 'text', required: false, placeholder: 'R06.02,Z51.11' },
      { name: 'urgency', type: 'select', required: false, options: ['routine', 'urgent', 'emergency'] }
    ]
  },
  {
    name: 'check_preauth_status',
    title: 'Check Pre-auth Status',
    description: 'Check status of pre-authorization request',
    category: 'status',
    fields: [
      { name: 'preauth_id', type: 'text', required: true, placeholder: 'PA001' }
    ]
  },
  {
    name: 'list_pending_preauths',
    title: 'List Pending Pre-auths',
    description: 'List all pending pre-authorization requests',
    category: 'status',
    fields: [
      { name: 'status', type: 'select', required: false, options: ['queued', 'submitted', 'approved', 'rejected'] }
    ]
  },
  {
    name: 'transcribe_medical_report',
    title: 'Transcribe Medical Report',
    description: 'Convert speech to text for medical reports (offline)',
    category: 'ai',
    fields: [
      { name: 'audio_file', type: 'file', required: true, accept: 'audio/*' },
      { name: 'language', type: 'select', required: false, options: ['eng', 'zul', 'xho', 'afr', 'sot'] },
      { name: 'extract_fields', type: 'checkbox', required: false }
    ]
  },
  {
    name: 'identify_patient_by_photo',
    title: 'Identify Patient by Photo',
    description: 'Identify patient from photo using face recognition (offline)',
    category: 'ai',
    fields: [
      { name: 'image_file', type: 'file', required: true, accept: 'image/*' },
      { name: 'tolerance', type: 'number', required: false, placeholder: '0.6', min: 0, max: 1, step: 0.1 }
    ]
  },
  {
    name: 'extract_text_from_document',
    title: 'Extract Text from Document',
    description: 'Extract text from medical documents/forms using OCR (offline)',
    category: 'ai',
    fields: [
      { name: 'image_file', type: 'file', required: true, accept: 'image/*' },
      { name: 'document_type', type: 'select', required: false, options: ['preauth_form', 'patient_info', 'insurance_card', 'id_document', 'generic'] },
      { name: 'language', type: 'select', required: false, options: ['eng', 'zul', 'xho', 'afr', 'sot'] }
    ]
  }
];

function MCPToolTester() {
  const [selectedTool, setSelectedTool] = useState(MCP_TOOLS[0]);
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState({});
  const [expandedResults, setExpandedResults] = useState({});

  const handleToolSelect = (tool) => {
    setSelectedTool(tool);
    setFormData({});
    // Initialize form data with default values
    const initialData = {};
    tool.fields.forEach(field => {
      if (field.type === 'checkbox') {
        initialData[field.name] = false;
      } else if (field.options && field.options.length > 0) {
        initialData[field.name] = field.options[0];
      } else {
        initialData[field.name] = '';
      }
    });
    setFormData(initialData);
  };

  const handleFieldChange = (fieldName, value) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  const executeTool = async () => {
    setLoading(true);
    try {
      // Prepare the request data
      const requestData = { ...formData };
      
      // Handle special field types
      selectedTool.fields.forEach(field => {
        if (field.name === 'icd10_codes' && requestData[field.name]) {
          // Convert comma-separated string to array
          requestData[field.name] = requestData[field.name].split(',').map(code => code.trim());
        }
      });

      const response = await fetch('/api/mcp/call-tool', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: selectedTool.name,
          arguments: requestData
        })
      });

      const result = await response.json();
      
      if (response.ok) {
        setResults(prev => ({
          ...prev,
          [selectedTool.name]: {
            ...result,
            timestamp: new Date().toISOString(),
            status: 'success'
          }
        }));
        toast.success(`${selectedTool.title} executed successfully!`);
      } else {
        setResults(prev => ({
          ...prev,
          [selectedTool.name]: {
            error: result.error || 'Unknown error',
            timestamp: new Date().toISOString(),
            status: 'error'
          }
        }));
        toast.error(`Failed to execute ${selectedTool.title}`);
      }
    } catch (error) {
      console.error('Tool execution failed:', error);
      setResults(prev => ({
        ...prev,
        [selectedTool.name]: {
          error: error.message,
          timestamp: new Date().toISOString(),
          status: 'error'
        }
      }));
      toast.error('Network error occurred');
    } finally {
      setLoading(false);
    }
  };

  const copyResult = (toolName) => {
    const result = results[toolName];
    navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    toast.success('Result copied to clipboard!');
  };

  const getCategoryColor = (category) => {
    const colors = {
      validation: 'primary',
      calculation: 'success',
      authorization: 'warning',
      status: 'info',
      ai: 'secondary'
    };
    return colors[category] || 'default';
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success': return <CheckCircle color="success" />;
      case 'error': return <Error color="error" />;
      case 'warning': return <Warning color="warning" />;
      default: return <Info color="info" />;
    }
  };

  const renderField = (field) => {
    const value = formData[field.name] || '';

    switch (field.type) {
      case 'select':
        return (
          <FormControl fullWidth>
            <InputLabel>{field.name.replace('_', ' ').toUpperCase()}</InputLabel>
            <Select
              value={value}
              label={field.name.replace('_', ' ').toUpperCase()}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
            >
              {field.options.map(option => (
                <MenuItem key={option} value={option}>{option}</MenuItem>
              ))}
            </Select>
          </FormControl>
        );
      
      case 'textarea':
        return (
          <TextField
            fullWidth
            multiline
            rows={3}
            label={field.name.replace('_', ' ').toUpperCase()}
            placeholder={field.placeholder}
            value={value}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            required={field.required}
          />
        );
      
      case 'checkbox':
        return (
          <Box>
            <label>
              <input
                type="checkbox"
                checked={value}
                onChange={(e) => handleFieldChange(field.name, e.target.checked)}
              />
              {field.name.replace('_', ' ').toUpperCase()}
            </label>
          </Box>
        );
      
      case 'number':
        return (
          <TextField
            fullWidth
            type="number"
            label={field.name.replace('_', ' ').toUpperCase()}
            placeholder={field.placeholder}
            value={value}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            required={field.required}
            inputProps={{
              min: field.min,
              max: field.max,
              step: field.step
            }}
          />
        );
      
      case 'file':
        return (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              {field.name.replace('_', ' ').toUpperCase()}
            </Typography>
            <input
              type="file"
              accept={field.accept}
              onChange={(e) => {
                const file = e.target.files[0];
                if (file) {
                  handleFieldChange(field.name, file.name);
                  // In a real implementation, you'd handle file upload here
                }
              }}
              style={{ width: '100%' }}
            />
          </Box>
        );
      
      default:
        return (
          <TextField
            fullWidth
            label={field.name.replace('_', ' ').toUpperCase()}
            placeholder={field.placeholder}
            value={value}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            required={field.required}
          />
        );
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        🔧 MCP Tool Tester
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Test all MCP server tools with real data. Results are processed by Claude AI for enhanced insights.
      </Typography>

      <Grid container spacing={3}>
        {/* Tool Selection */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, maxHeight: '70vh', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              Available Tools ({MCP_TOOLS.length})
            </Typography>
            
            {MCP_TOOLS.map((tool) => (
              <Card 
                key={tool.name}
                sx={{ 
                  mb: 2, 
                  cursor: 'pointer',
                  border: selectedTool.name === tool.name ? 2 : 1,
                  borderColor: selectedTool.name === tool.name ? 'primary.main' : 'grey.300'
                }}
                onClick={() => handleToolSelect(tool)}
              >
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                    <Typography variant="h6" component="div">
                      {tool.title}
                    </Typography>
                    <Chip 
                      label={tool.category}
                      color={getCategoryColor(tool.category)}
                      size="small"
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {tool.description}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Paper>
        </Grid>

        {/* Tool Configuration */}
        <Grid item xs={12} md={8}>
          {selectedTool && (
            <Paper sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom>
                {selectedTool.title}
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                {selectedTool.description}
              </Typography>

              <Grid container spacing={2}>
                {selectedTool.fields.map((field) => (
                  <Grid item xs={12} sm={6} key={field.name}>
                    {renderField(field)}
                  </Grid>
                ))}
              </Grid>

              <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  startIcon={loading ? <CircularProgress size={20} /> : <PlayArrow />}
                  onClick={executeTool}
                  disabled={loading}
                >
                  {loading ? 'Executing...' : 'Execute Tool'}
                </Button>
                
                <Button
                  variant="outlined"
                  startIcon={<Stop />}
                  disabled={!loading}
                >
                  Cancel
                </Button>
              </Box>
            </Paper>
          )}
        </Grid>

        {/* Results */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Execution Results
            </Typography>
            
            {Object.keys(results).length === 0 ? (
              <Alert severity="info">
                No results yet. Execute a tool to see results here.
              </Alert>
            ) : (
              Object.entries(results).map(([toolName, result]) => (
                <Accordion 
                  key={toolName}
                  expanded={expandedResults[toolName] || false}
                  onChange={(event, isExpanded) => {
                    setExpandedResults(prev => ({
                      ...prev,
                      [toolName]: isExpanded
                    }));
                  }}
                >
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Box display="flex" alignItems="center" gap={1}>
                      {getStatusIcon(result.status)}
                      <Typography variant="h6">
                        {toolName}
                      </Typography>
                      <Chip 
                        label={result.status}
                        color={result.status === 'success' ? 'success' : 'error'}
                        size="small"
                      />
                      <Typography variant="caption" color="text.secondary">
                        {new Date(result.timestamp).toLocaleString()}
                      </Typography>
                    </Box>
                    <Box sx={{ ml: 'auto' }}>
                      <Tooltip title="Copy Result">
                        <IconButton 
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            copyResult(toolName);
                          }}
                        >
                          <ContentCopy />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <ReactJsonView
                      src={result}
                      theme="rjv-default"
                      collapsed={1}
                      displayDataTypes={false}
                      enableClipboard={true}
                      name="result"
                    />
                  </AccordionDetails>
                </Accordion>
              ))
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default MCPToolTester;