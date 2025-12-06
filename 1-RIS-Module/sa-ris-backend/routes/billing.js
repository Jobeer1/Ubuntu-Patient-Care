const express = require('express');
const router = express.Router();

// Mock invoices database
let invoices = [
  {
    id: 'INV001',
    patientName: 'Thabo Mokoena',
    patientId: 'P001',
    studyId: 'S001',
    date: '2025-10-17',
    procedureCode: '71010',
    procedureName: 'CT Brain without contrast',
    amount: 3500.00,
    medicalAid: 'Discovery Health',
    medicalAidNumber: 'DH123456',
    status: 'Paid',
    paymentDate: '2025-10-17'
  }
];

// Get all invoices
router.get('/', (req, res) => {
  const { status, patientId } = req.query;
  let filtered = invoices;
  
  if (status) {
    filtered = filtered.filter(inv => inv.status === status);
  }
  if (patientId) {
    filtered = filtered.filter(inv => inv.patientId === patientId);
  }
  
  res.json({ success: true, data: filtered });
});

// Get invoice by ID
router.get('/:id', (req, res) => {
  const invoice = invoices.find(inv => inv.id === req.params.id);
  if (!invoice) {
    return res.status(404).json({ success: false, error: 'Invoice not found' });
  }
  res.json({ success: true, data: invoice });
});

// Create new invoice
router.post('/', (req, res) => {
  const newInvoice = {
    id: `INV${String(invoices.length + 1).padStart(3, '0')}`,
    ...req.body,
    date: new Date().toISOString().split('T')[0],
    status: 'Pending',
    paymentDate: null
  };
  invoices.push(newInvoice);
  res.json({ success: true, data: newInvoice });
});

// Update invoice
router.put('/:id', (req, res) => {
  const index = invoices.findIndex(inv => inv.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ success: false, error: 'Invoice not found' });
  }
  invoices[index] = { ...invoices[index], ...req.body };
  res.json({ success: true, data: invoices[index] });
});

// Mark invoice as paid
router.post('/:id/pay', (req, res) => {
  const index = invoices.findIndex(inv => inv.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ success: false, error: 'Invoice not found' });
  }
  invoices[index].status = 'Paid';
  invoices[index].paymentDate = new Date().toISOString().split('T')[0];
  res.json({ success: true, data: invoices[index] });
});

// Get billing statistics
router.get('/stats/summary', (req, res) => {
  const totalRevenue = invoices.reduce((sum, inv) => sum + inv.amount, 0);
  const paidRevenue = invoices.filter(inv => inv.status === 'Paid').reduce((sum, inv) => sum + inv.amount, 0);
  const pendingRevenue = invoices.filter(inv => inv.status === 'Pending').reduce((sum, inv) => sum + inv.amount, 0);
  
  res.json({
    success: true,
    data: {
      totalRevenue,
      paidRevenue,
      pendingRevenue,
      totalInvoices: invoices.length,
      paidInvoices: invoices.filter(inv => inv.status === 'Paid').length,
      pendingInvoices: invoices.filter(inv => inv.status === 'Pending').length
    }
  });
});

module.exports = router;
