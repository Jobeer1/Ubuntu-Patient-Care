const express = require('express');
const router = express.Router();

// Mock reports database
let reports = [
  {
    id: 'R001',
    studyId: 'S001',
    patientName: 'Thabo Mokoena',
    patientId: 'P001',
    modality: 'CT',
    bodyPart: 'Brain',
    reportDate: '2025-10-17',
    radiologist: 'Dr. Mokoena',
    status: 'Draft',
    findings: 'Preliminary findings...',
    impression: 'To be completed'
  }
];

// Get all reports
router.get('/', (req, res) => {
  const { status, radiologist } = req.query;
  let filtered = reports;
  
  if (status) {
    filtered = filtered.filter(r => r.status === status);
  }
  if (radiologist) {
    filtered = filtered.filter(r => r.radiologist === radiologist);
  }
  
  res.json({ success: true, data: filtered });
});

// Get report by ID
router.get('/:id', (req, res) => {
  const report = reports.find(r => r.id === req.params.id);
  if (!report) {
    return res.status(404).json({ success: false, error: 'Report not found' });
  }
  res.json({ success: true, data: report });
});

// Create new report
router.post('/', (req, res) => {
  const newReport = {
    id: `R${String(reports.length + 1).padStart(3, '0')}`,
    ...req.body,
    reportDate: new Date().toISOString().split('T')[0],
    status: 'Draft'
  };
  reports.push(newReport);
  res.json({ success: true, data: newReport });
});

// Update report
router.put('/:id', (req, res) => {
  const index = reports.findIndex(r => r.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ success: false, error: 'Report not found' });
  }
  reports[index] = { ...reports[index], ...req.body };
  res.json({ success: true, data: reports[index] });
});

// Finalize report
router.post('/:id/finalize', (req, res) => {
  const index = reports.findIndex(r => r.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ success: false, error: 'Report not found' });
  }
  reports[index].status = 'Finalized';
  res.json({ success: true, data: reports[index] });
});

module.exports = router;
