const express = require('express');
const router = express.Router();

// Mock patient database
let patients = [
  {
    id: 'P001',
    firstName: 'Thabo',
    lastName: 'Mokoena',
    idNumber: '8501015800081',
    dateOfBirth: '1985-01-01',
    gender: 'Male',
    phone: '+27 82 123 4567',
    email: 'thabo.mokoena@email.com',
    address: '123 Main St, Johannesburg, 2000',
    medicalAid: 'Discovery Health',
    medicalAidNumber: 'DH123456',
    status: 'Active',
    lastVisit: '2025-10-15',
    totalStudies: 12
  }
];

// Get all patients
router.get('/', (req, res) => {
  res.json({ success: true, data: patients });
});

// Get patient by ID
router.get('/:id', (req, res) => {
  const patient = patients.find(p => p.id === req.params.id);
  if (!patient) {
    return res.status(404).json({ success: false, error: 'Patient not found' });
  }
  res.json({ success: true, data: patient });
});

// Create new patient
router.post('/', (req, res) => {
  const newPatient = {
    id: `P${String(patients.length + 1).padStart(3, '0')}`,
    ...req.body,
    status: 'Active',
    totalStudies: 0,
    lastVisit: null
  };
  patients.push(newPatient);
  res.json({ success: true, data: newPatient });
});

// Update patient
router.put('/:id', (req, res) => {
  const index = patients.findIndex(p => p.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ success: false, error: 'Patient not found' });
  }
  patients[index] = { ...patients[index], ...req.body };
  res.json({ success: true, data: patients[index] });
});

// Delete patient
router.delete('/:id', (req, res) => {
  const index = patients.findIndex(p => p.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ success: false, error: 'Patient not found' });
  }
  patients.splice(index, 1);
  res.json({ success: true, message: 'Patient deleted' });
});

module.exports = router;
