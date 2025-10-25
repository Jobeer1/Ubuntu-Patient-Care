import React, { useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Space, message, Tag, Row, Col, Descriptions, InputNumber, Divider } from 'antd';
import { DollarOutlined, PlusOutlined, EyeOutlined, PrinterOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import moment from 'moment';

const { Option } = Select;

const BillingSystem = () => {
  const [invoices, setInvoices] = useState([
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
    },
    {
      id: 'INV002',
      patientName: 'Nomsa Dlamini',
      patientId: 'P002',
      studyId: 'S002',
      date: '2025-10-17',
      procedureCode: '72148',
      procedureName: 'MRI Lumbar Spine',
      amount: 5200.00,
      medicalAid: 'Bonitas',
      medicalAidNumber: 'BON789012',
      status: 'Pending',
      paymentDate: null
    }
  ]);
  const [modalVisible, setModalVisible] = useState(false);
  const [detailsVisible, setDetailsVisible] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [form] = Form.useForm();

  const procedureCodes = [
    { code: '71010', name: 'CT Brain without contrast', price: 3500.00 },
    { code: '71020', name: 'CT Brain with contrast', price: 4200.00 },
    { code: '72148', name: 'MRI Lumbar Spine', price: 5200.00 },
    { code: '72146', name: 'MRI Thoracic Spine', price: 5200.00 },
    { code: '71045', name: 'Chest X-Ray PA and Lateral', price: 450.00 },
    { code: '76700', name: 'Ultrasound Abdomen', price: 1200.00 }
  ];

  const handleCreateInvoice = () => {
    form.resetFields();
    setModalVisible(true);
  };

  const handleViewInvoice = (invoice) => {
    setSelectedInvoice(invoice);
    setDetailsVisible(true);
  };

  const handleProcedureChange = (code) => {
    const procedure = procedureCodes.find(p => p.code === code);
    if (procedure) {
      form.setFieldsValue({
        procedureName: procedure.name,
        amount: procedure.price
      });
    }
  };

  const handleSubmit = async (values) => {
    try {
      const newInvoice = {
        id: `INV${String(invoices.length + 1).padStart(3, '0')}`,
        ...values,
        date: moment().format('YYYY-MM-DD'),
        status: 'Pending',
        paymentDate: null
      };
      setInvoices([...invoices, newInvoice]);
      message.success('Invoice created successfully');
      setModalVisible(false);
    } catch (error) {
      message.error('Failed to create invoice');
    }
  };

  const handleMarkAsPaid = (invoiceId) => {
    const updated = invoices.map(inv =>
      inv.id === invoiceId
        ? { ...inv, status: 'Paid', paymentDate: moment().format('YYYY-MM-DD') }
        : inv
    );
    setInvoices(updated);
    message.success('Invoice marked as paid');
  };

  const columns = [
    {
      title: 'Invoice #',
      dataIndex: 'id',
      key: 'id',
      width: 100
    },
    {
      title: 'Date',
      dataIndex: 'date',
      key: 'date',
      width: 120
    },
    {
      title: 'Patient',
      key: 'patient',
      width: 180,
      render: (_, record) => (
        <div>
          <div>{record.patientName}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>{record.patientId}</div>
        </div>
      )
    },
    {
      title: 'Procedure',
      key: 'procedure',
      width: 250,
      render: (_, record) => (
        <div>
          <div>{record.procedureName}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>Code: {record.procedureCode}</div>
        </div>
      )
    },
    {
      title: 'Medical Aid',
      key: 'medicalAid',
      width: 180,
      render: (_, record) => (
        <div>
          <div>{record.medicalAid}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>{record.medicalAidNumber}</div>
        </div>
      )
    },
    {
      title: 'Amount',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      render: (amount) => `R ${amount.toFixed(2)}`
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => {
        const config = {
          'Paid': { color: 'green', icon: <CheckCircleOutlined /> },
          'Pending': { color: 'orange', icon: <ClockCircleOutlined /> },
          'Rejected': { color: 'red', icon: null }
        };
        return (
          <Tag color={config[status].color}>
            {config[status].icon} {status}
          </Tag>
        );
      }
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewInvoice(record)}
          >
            View
          </Button>
          {record.status === 'Pending' && (
            <Button
              type="link"
              icon={<CheckCircleOutlined />}
              onClick={() => handleMarkAsPaid(record.id)}
              style={{ color: 'green' }}
            >
              Mark Paid
            </Button>
          )}
          <Button
            type="link"
            icon={<PrinterOutlined />}
          >
            Print
          </Button>
        </Space>
      )
    }
  ];

  const totalRevenue = invoices.reduce((sum, inv) => sum + inv.amount, 0);
  const paidRevenue = invoices.filter(inv => inv.status === 'Paid').reduce((sum, inv) => sum + inv.amount, 0);
  const pendingRevenue = invoices.filter(inv => inv.status === 'Pending').reduce((sum, inv) => sum + inv.amount, 0);

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={8}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', color: '#999', marginBottom: '8px' }}>Total Revenue</div>
              <div style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--sa-blue)' }}>
                R {totalRevenue.toFixed(2)}
              </div>
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', color: '#999', marginBottom: '8px' }}>Paid</div>
              <div style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--sa-green)' }}>
                R {paidRevenue.toFixed(2)}
              </div>
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', color: '#999', marginBottom: '8px' }}>Pending</div>
              <div style={{ fontSize: '28px', fontWeight: 'bold', color: 'orange' }}>
                R {pendingRevenue.toFixed(2)}
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: '24px' }}>
          <Col>
            <h2 style={{ margin: 0 }}>
              <DollarOutlined style={{ marginRight: '8px' }} />
              Billing & Invoices
            </h2>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateInvoice}
              style={{ background: 'var(--sa-blue)' }}
            >
              Create Invoice
            </Button>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={invoices}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create Invoice Modal */}
      <Modal
        title="Create New Invoice"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="patientId"
                label="Patient"
                rules={[{ required: true, message: 'Please select patient' }]}
              >
                <Select placeholder="Select patient">
                  <Option value="P001">P001 - Thabo Mokoena</Option>
                  <Option value="P002">P002 - Nomsa Dlamini</Option>
                  <Option value="P003">P003 - Sipho Nkosi</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="studyId"
                label="Study"
                rules={[{ required: true, message: 'Please select study' }]}
              >
                <Select placeholder="Select study">
                  <Option value="S001">S001 - CT Brain</Option>
                  <Option value="S002">S002 - MRI Spine</Option>
                  <Option value="S003">S003 - Chest X-Ray</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="procedureCode"
            label="Procedure Code"
            rules={[{ required: true, message: 'Please select procedure' }]}
          >
            <Select
              placeholder="Select procedure"
              onChange={handleProcedureChange}
              showSearch
            >
              {procedureCodes.map(proc => (
                <Option key={proc.code} value={proc.code}>
                  {proc.code} - {proc.name} (R {proc.price.toFixed(2)})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="procedureName"
            label="Procedure Name"
          >
            <Input disabled />
          </Form.Item>

          <Form.Item
            name="amount"
            label="Amount (ZAR)"
            rules={[{ required: true, message: 'Please enter amount' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={2}
              formatter={value => `R ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value.replace(/R\s?|(,*)/g, '')}
            />
          </Form.Item>

          <Divider />

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="medicalAid"
                label="Medical Aid"
              >
                <Select>
                  <Option value="Discovery Health">Discovery Health</Option>
                  <Option value="Bonitas">Bonitas</Option>
                  <Option value="Momentum">Momentum</Option>
                  <Option value="Medshield">Medshield</Option>
                  <Option value="None">None (Self-Pay)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="medicalAidNumber"
                label="Medical Aid Number"
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space style={{ float: 'right' }}>
              <Button onClick={() => setModalVisible(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit" style={{ background: 'var(--sa-blue)' }}>
                Create Invoice
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Invoice Details Modal */}
      <Modal
        title={`Invoice Details - ${selectedInvoice?.id}`}
        open={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        footer={[
          <Button key="print" icon={<PrinterOutlined />}>
            Print Invoice
          </Button>,
          <Button key="close" onClick={() => setDetailsVisible(false)}>
            Close
          </Button>
        ]}
        width={700}
      >
        {selectedInvoice && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="Invoice Number">{selectedInvoice.id}</Descriptions.Item>
            <Descriptions.Item label="Date">{selectedInvoice.date}</Descriptions.Item>
            <Descriptions.Item label="Patient">{selectedInvoice.patientName} ({selectedInvoice.patientId})</Descriptions.Item>
            <Descriptions.Item label="Study ID">{selectedInvoice.studyId}</Descriptions.Item>
            <Descriptions.Item label="Procedure Code">{selectedInvoice.procedureCode}</Descriptions.Item>
            <Descriptions.Item label="Procedure Name">{selectedInvoice.procedureName}</Descriptions.Item>
            <Descriptions.Item label="Amount">R {selectedInvoice.amount.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="Medical Aid">{selectedInvoice.medicalAid}</Descriptions.Item>
            <Descriptions.Item label="Medical Aid Number">{selectedInvoice.medicalAidNumber}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={selectedInvoice.status === 'Paid' ? 'green' : 'orange'}>
                {selectedInvoice.status}
              </Tag>
            </Descriptions.Item>
            {selectedInvoice.paymentDate && (
              <Descriptions.Item label="Payment Date">{selectedInvoice.paymentDate}</Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default BillingSystem;
