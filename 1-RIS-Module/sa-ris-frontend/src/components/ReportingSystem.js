import React, { useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Space, message, Tag, Row, Col, Tabs, Divider } from 'antd';
import { FileTextOutlined, PlusOutlined, EditOutlined, CheckOutlined, EyeOutlined, PrinterOutlined } from '@ant-design/icons';
import moment from 'moment';

const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;

const ReportingSystem = () => {
  const [reports, setReports] = useState([
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
    },
    {
      id: 'R002',
      studyId: 'S002',
      patientName: 'Nomsa Dlamini',
      patientId: 'P002',
      modality: 'MRI',
      bodyPart: 'Spine',
      reportDate: '2025-10-17',
      radiologist: 'Dr. Dlamini',
      status: 'Finalized',
      findings: 'Normal lumbar spine MRI',
      impression: 'No significant abnormality detected'
    }
  ]);
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [form] = Form.useForm();

  const reportTemplates = {
    'CT Brain': {
      findings: 'TECHNIQUE: Non-contrast CT scan of the brain was performed.\n\nFINDINGS:\n- Brain parenchyma: \n- Ventricles: \n- Extra-axial spaces: \n- Skull and scalp: ',
      impression: 'IMPRESSION:\n1. '
    },
    'MRI Spine': {
      findings: 'TECHNIQUE: MRI of the spine was performed.\n\nFINDINGS:\n- Vertebral alignment: \n- Disc spaces: \n- Spinal cord: \n- Paraspinal soft tissues: ',
      impression: 'IMPRESSION:\n1. '
    },
    'Chest X-Ray': {
      findings: 'TECHNIQUE: PA and lateral chest radiographs.\n\nFINDINGS:\n- Lungs: \n- Heart: \n- Mediastinum: \n- Bones: ',
      impression: 'IMPRESSION:\n1. '
    }
  };

  const handleCreateReport = () => {
    form.resetFields();
    setSelectedReport(null);
    setModalVisible(true);
  };

  const handleEditReport = (report) => {
    setSelectedReport(report);
    form.setFieldsValue(report);
    setModalVisible(true);
  };

  const handleTemplateSelect = (template) => {
    if (reportTemplates[template]) {
      form.setFieldsValue({
        findings: reportTemplates[template].findings,
        impression: reportTemplates[template].impression
      });
    }
  };

  const handleSubmit = async (values) => {
    try {
      if (selectedReport) {
        // Update report
        const updated = reports.map(r =>
          r.id === selectedReport.id ? { ...r, ...values } : r
        );
        setReports(updated);
        message.success('Report updated successfully');
      } else {
        // Create new report
        const newReport = {
          id: `R${String(reports.length + 1).padStart(3, '0')}`,
          ...values,
          reportDate: moment().format('YYYY-MM-DD'),
          status: 'Draft'
        };
        setReports([...reports, newReport]);
        message.success('Report created successfully');
      }
      setModalVisible(false);
    } catch (error) {
      message.error('Failed to save report');
    }
  };

  const handleFinalizeReport = (reportId) => {
    const updated = reports.map(r =>
      r.id === reportId ? { ...r, status: 'Finalized' } : r
    );
    setReports(updated);
    message.success('Report finalized');
  };

  const columns = [
    {
      title: 'Report ID',
      dataIndex: 'id',
      key: 'id',
      width: 100
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
      title: 'Study',
      key: 'study',
      width: 150,
      render: (_, record) => (
        <div>
          <Tag color="blue">{record.modality}</Tag>
          <span>{record.bodyPart}</span>
        </div>
      )
    },
    {
      title: 'Report Date',
      dataIndex: 'reportDate',
      key: 'reportDate',
      width: 120
    },
    {
      title: 'Radiologist',
      dataIndex: 'radiologist',
      key: 'radiologist',
      width: 150
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => {
        const colors = {
          'Draft': 'orange',
          'Finalized': 'green',
          'Amended': 'blue'
        };
        return <Tag color={colors[status]}>{status}</Tag>;
      }
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 250,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleEditReport(record)}
          >
            View
          </Button>
          {record.status === 'Draft' && (
            <>
              <Button
                type="link"
                icon={<EditOutlined />}
                onClick={() => handleEditReport(record)}
              >
                Edit
              </Button>
              <Button
                type="link"
                icon={<CheckOutlined />}
                onClick={() => handleFinalizeReport(record.id)}
                style={{ color: 'green' }}
              >
                Finalize
              </Button>
            </>
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

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: '24px' }}>
          <Col>
            <h2 style={{ margin: 0 }}>
              <FileTextOutlined style={{ marginRight: '8px' }} />
              Reporting System
            </h2>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateReport}
              style={{ background: 'var(--sa-blue)' }}
            >
              Create Report
            </Button>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={reports}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={selectedReport ? 'Edit Report' : 'Create New Report'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={900}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="studyId"
                label="Study"
                rules={[{ required: true, message: 'Please select study' }]}
              >
                <Select placeholder="Select study">
                  <Option value="S001">S001 - CT Brain - Thabo Mokoena</Option>
                  <Option value="S002">S002 - MRI Spine - Nomsa Dlamini</Option>
                  <Option value="S003">S003 - Chest X-Ray - Sipho Nkosi</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="radiologist"
                label="Radiologist"
                rules={[{ required: true, message: 'Please select radiologist' }]}
              >
                <Select>
                  <Option value="Dr. Mokoena">Dr. Thabo Mokoena</Option>
                  <Option value="Dr. Dlamini">Dr. Nomsa Dlamini</Option>
                  <Option value="Dr. Nkosi">Dr. Sipho Nkosi</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="Report Template">
            <Select
              placeholder="Select template to auto-fill"
              onChange={handleTemplateSelect}
              allowClear
            >
              <Option value="CT Brain">CT Brain</Option>
              <Option value="MRI Spine">MRI Spine</Option>
              <Option value="Chest X-Ray">Chest X-Ray</Option>
            </Select>
          </Form.Item>

          <Divider />

          <Form.Item
            name="findings"
            label="Findings"
            rules={[{ required: true, message: 'Please enter findings' }]}
          >
            <TextArea rows={10} placeholder="Enter detailed findings..." />
          </Form.Item>

          <Form.Item
            name="impression"
            label="Impression"
            rules={[{ required: true, message: 'Please enter impression' }]}
          >
            <TextArea rows={5} placeholder="Enter clinical impression..." />
          </Form.Item>

          <Form.Item>
            <Space style={{ float: 'right' }}>
              <Button onClick={() => setModalVisible(false)}>Cancel</Button>
              <Button type="default" htmlType="submit">
                Save as Draft
              </Button>
              <Button type="primary" htmlType="submit" style={{ background: 'var(--sa-green)' }}>
                Save & Finalize
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReportingSystem;
