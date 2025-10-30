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
  Chip,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  Psychology,
  Send,
  ContentCopy,
  ExpandMore,
  Lightbulb,
  Assessment,
  CheckCircle,
  Error,
  Warning,
  AutoAwesome,
} from '@mui/icons-material';
import ReactJsonView from 'react-json-view';
import toast from 'react-hot-toast';

const SAMPLE_QUERIES = [
  {
    category: 'Medical Analysis',
    queries: [
      'Analyze pre-authorization for CT scan with chest pain indication',
      'What are the requirements for MRI approval in Discovery Health?',
      'Patient has diabetes, needs insulin pump - approval probability?',
      'Urgent cardiac catheterization - what documentation is needed?'
    ]
  },
  {
    category: 'Cost Estimation',
    queries: [
      'Estimate patient cost for arthroscopic knee surgery on Momentum',
      'What is the typical co-payment for oncology procedures?',
      'Compare costs between different medical schemes for hip replacement',
      'Annual benefit limits for chronic medication on Bonitas'
    ]
  },
  {
    category: 'Clinical Decision Support',
    queries: [
      'Alternative treatments for hypertension in elderly patients',
      'When is pre-authorization not required for emergency procedures?',
      'ICD-10 codes for chronic kidney disease management',
      'Risk assessment for same-day discharge after surgery'
    ]
  },
  {
    category: 'Regulatory Compliance',
    queries: [
      'HPCSA guidelines for telemedicine consultations',
      'CMS requirements for medical aid scheme benefits',
      'Documentation needed for high-cost procedure approval',
      'Appeals process for rejected pre-authorizations'
    ]
  }
];

function ClaudeAIBrain() {
  const [query, setQuery] = useState('');
  const [context, setContext] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [expandedResults, setExpandedResults] = useState({});
  const [selectedCategory, setSelectedCategory] = useState('');
  const [serviceStatus, setServiceStatus] = useState(null);

  useEffect(() => {
    checkServiceStatus();
  }, []);

  const checkServiceStatus = async () => {
    try {
      const response = await fetch('/api/ai-brain/status');
      const data = await response.json();
      setServiceStatus(data);
    } catch (error) {
      console.error('Failed to check Claude service status:', error);
      setServiceStatus({ status: 'error', error: 'Connection failed' });
    }
  };

  const askClaude = async () => {
    if (!query.trim()) {
      toast.error('Please enter a question for Claude');
      return;
    }

    setLoading(true);
    try {
      const requestData = {
        query: query.trim(),
        context: context.trim() ? JSON.parse(context) : null
      };

      const response = await fetch('/api/ai-brain/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });

      const result = await response.json();
      
      if (response.ok) {
        const newResult = {
          id: Date.now(),
          query: query,
          context: requestData.context,
          response: result,
          timestamp: new Date().toISOString(),
          status: result.status || 'success'
        };
        
        setResults(prev => [newResult, ...prev]);
        setExpandedResults(prev => ({
          ...prev,
          [newResult.id]: true
        }));
        
        toast.success('Claude responded successfully!');
        setQuery(''); // Clear the query after successful submission
      } else {
        toast.error(`Claude analysis failed: ${result.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Claude query failed:', error);
      toast.error('Network error occurred');
    } finally {
      setLoading(false);
    }
  };

  const useSampleQuery = (sampleQuery) => {
    setQuery(sampleQuery);
  };

  const copyResult = (result) => {
    navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    toast.success('Result copied to clipboard!');
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return 'success';
      case 'error': return 'error';
      case 'warning': return 'warning';
      default: return 'info';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success': return <CheckCircle color="success" />;
      case 'error': return <Error color="error" />;
      case 'warning': return <Warning color="warning" />;
      default: return <Psychology color="info" />;
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 90) return 'success';
    if (confidence >= 70) return 'warning';
    return 'error';
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        🧠 Claude AI Brain - Medical Intelligence
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Interact with Claude 4 Sonnet for intelligent medical analysis, decision support, and recommendations.
        All responses are tailored for South African healthcare systems.
      </Typography>

      {/* Service Status */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          {serviceStatus && (
            <Alert 
              severity={serviceStatus.status === 'ready' ? 'success' : 'error'}
              icon={serviceStatus.status === 'ready' ? <AutoAwesome /> : <Error />}
            >
              <Typography variant="body2">
                <strong>Claude Service Status:</strong> {serviceStatus.status === 'ready' ? 'Connected and Ready' : 'Service Unavailable'}
                {serviceStatus.model_id && (
                  <span> | Model: {serviceStatus.model_id}</span>
                )}
                {serviceStatus.region && (
                  <span> | Region: {serviceStatus.region}</span>
                )}
              </Typography>
            </Alert>
          )}
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Query Input */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Ask Claude Anything
            </Typography>
            
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Medical Question or Request"
              placeholder="e.g., Analyze this pre-authorization request for CT scan with chest pain indication..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              rows={3}
              label="Context (Optional JSON)"
              placeholder={`{
  "patient_id": "P001",
  "scheme_code": "DISCOVERY",
  "procedure_code": "0190",
  "clinical_indication": "Chest pain"
}`}
              value={context}
              onChange={(e) => setContext(e.target.value)}
              sx={{ mb: 2 }}
              helperText="Provide additional context as JSON (patient data, procedures, etc.)"
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="contained"
                startIcon={loading ? <CircularProgress size={20} /> : <Send />}
                onClick={askClaude}
                disabled={loading || !query.trim()}
                size="large"
              >
                {loading ? 'Analyzing...' : 'Ask Claude'}
              </Button>
              
              <Button
                variant="outlined"
                startIcon={<Psychology />}
                onClick={() => setQuery('')}
                disabled={loading}
              >
                Clear
              </Button>
            </Box>
          </Paper>
        </Grid>

        {/* Sample Queries */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, maxHeight: '60vh', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              <Lightbulb sx={{ mr: 1, verticalAlign: 'middle' }} />
              Sample Questions
            </Typography>
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Filter by Category</InputLabel>
              <Select
                value={selectedCategory}
                label="Filter by Category"
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <MenuItem value="">All Categories</MenuItem>
                {SAMPLE_QUERIES.map(cat => (
                  <MenuItem key={cat.category} value={cat.category}>
                    {cat.category}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {SAMPLE_QUERIES
              .filter(cat => !selectedCategory || cat.category === selectedCategory)
              .map((category) => (
                <Box key={category.category} sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" gutterBottom color="primary">
                    {category.category}
                  </Typography>
                  {category.queries.map((sampleQuery, index) => (
                    <Card 
                      key={index}
                      sx={{ 
                        mb: 1, 
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'action.hover' }
                      }}
                      onClick={() => useSampleQuery(sampleQuery)}
                    >
                      <CardContent sx={{ py: 1 }}>
                        <Typography variant="body2">
                          {sampleQuery}
                        </Typography>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              ))}
          </Paper>
        </Grid>

        {/* Results */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              <Assessment sx={{ mr: 1, verticalAlign: 'middle' }} />
              Claude's Responses ({results.length})
            </Typography>
            
            {results.length === 0 ? (
              <Alert severity="info">
                No responses yet. Ask Claude a question to see intelligent analysis here.
              </Alert>
            ) : (
              results.map((result) => (
                <Accordion 
                  key={result.id}
                  expanded={expandedResults[result.id] || false}
                  onChange={(event, isExpanded) => {
                    setExpandedResults(prev => ({
                      ...prev,
                      [result.id]: isExpanded
                    }));
                  }}
                  sx={{ mb: 2 }}
                >
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Box display="flex" alignItems="center" gap={1} sx={{ width: '100%' }}>
                      {getStatusIcon(result.status)}
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography variant="h6" noWrap>
                          {result.query.length > 60 ? `${result.query.substring(0, 60)}...` : result.query}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(result.timestamp).toLocaleString()}
                        </Typography>
                      </Box>
                      
                      {result.response.confidence && (
                        <Chip 
                          label={`${result.response.confidence}% confident`}
                          color={getConfidenceColor(result.response.confidence)}
                          size="small"
                        />
                      )}
                      
                      <Chip 
                        label={result.status}
                        color={getStatusColor(result.status)}
                        size="small"
                      />
                      
                      <Tooltip title="Copy Response">
                        <IconButton 
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            copyResult(result);
                          }}
                        >
                          <ContentCopy />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12}>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          <strong>Original Query:</strong>
                        </Typography>
                        <Typography variant="body1" paragraph>
                          {result.query}
                        </Typography>
                      </Grid>
                      
                      {result.context && (
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            <strong>Context Provided:</strong>
                          </Typography>
                          <ReactJsonView
                            src={result.context}
                            theme="rjv-default"
                            collapsed={1}
                            displayDataTypes={false}
                            name="context"
                          />
                          <Divider sx={{ my: 2 }} />
                        </Grid>
                      )}
                      
                      <Grid item xs={12}>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          <strong>Claude's Analysis:</strong>
                        </Typography>
                        
                        {typeof result.response === 'string' ? (
                          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                            {result.response}
                          </Typography>
                        ) : (
                          <ReactJsonView
                            src={result.response}
                            theme="rjv-default"
                            collapsed={1}
                            displayDataTypes={false}
                            enableClipboard={true}
                            name="claude_response"
                          />
                        )}
                      </Grid>
                    </Grid>
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

export default ClaudeAIBrain;