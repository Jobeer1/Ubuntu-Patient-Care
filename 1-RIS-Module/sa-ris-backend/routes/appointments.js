const express = require('express');
const router = express.Router();

// Mock appointments database
let appointments = [
  {
    id: 1,
    patientName: 'Thabo Mokoena',
    patientId: 'P001',
    date: '2025-10-17',
    time: '09:00',
    modality: 'CT Scan',
    bodyPart: 'Brain',
    status: 'Scheduled',
    notes: 'Urgent case'
  }
];

// Get all appointments
router.get('/', (req, res) => {
  const { date, status } = req.query;
  let filtered = appointments;
  
  if (date) {
    filtered = filtered.filter(apt => apt.date === date);
  }
  if (status) {
    filtered = filtered.filter(apt => apt.status === status);
  }
  
  res.json({ success: true, data: filtered });
});

// Get appointment by ID
router.get('/:id', (req, res) => {
  const appointment = appointments.find(a => a.id === parseInt(req.params.id));
  if (!appointment) {
    return res.status(404).json({ success: false, error: 'Appointment not found' });
  }
  res.json({ success: true, data: appointment });
});

// Create new appointment
router.post('/', (req, res) => {
  const newAppointment = {
    id: appointments.length + 1,
    ...req.body,
    status: 'Scheduled'
  };
  appointments.push(newAppointment);
  res.json({ success: true, data: newAppointment });
});

// Update appointment
router.put('/:id', (req, res) => {
  const index = appointments.findIndex(a => a.id === parseInt(req.params.id));
  if (index === -1) {
    return res.status(404).json({ success: false, error: 'Appointment not found' });
  }
  appointments[index] = { ...appointments[index], ...req.body };
  res.json({ success: true, data: appointments[index] });
});

// Delete appointment
router.delete('/:id', (req, res) => {
  const index = appointments.findIndex(a => a.id === parseInt(req.params.id));
  if (index === -1) {
    return res.status(404).json({ success: false, error: 'Appointment not found' });
  }
  appointments.splice(index, 1);
  res.json({ success: true, message: 'Appointment deleted' });
});

module.exports = router;
