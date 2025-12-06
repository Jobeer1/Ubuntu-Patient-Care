import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Select, DatePicker, Space, message, Tag, Drawer, Descriptions, Tabs, Card, Row, Col, Upload, Avatar } from 'antd';
import { UserOutlined, PlusOutlined, EditOutlined, EyeOutlined, PhoneOutlined, MailOutlined, HomeOutlined, IdcardOutlined, MedicineBoxOutlined, HistoryOutlined, FileImageOutlined, UploadOutlined } from '@ant-design/icons';
import moment from 'moment';
import axios from 'axios';

const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;

const PatientManagement = () => {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [form] = Form.useForm();
  const [searchText, setSearchText] = useState('');

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    setLoading(true);
    try {
      // Mock data - replace with actual API call
      const mockPatients = [
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
        },
        {
          id: 'P002',
          firstName: 'Nomsa',
          lastName: 'Dlamini',
          idNumber: '9203125900082',
          dateOfBirth: '1992-03-12',
          gender: 'Female',
          phone: '+27 83 234 5678',
          email: 'nomsa.dlamini@email.com',
          address: '456 Oak Ave, Pretoria, 0001',
          medicalAid: 'Bonitas',
          medicalAidNumber: 'BON789012',
          status: 'Active',
          lastVisit: '2025-10-16',
          totalStudies: 8
        }
      ];
      setPatients(mockPatients);
    } catch (error) {
      message.error('Failed to load patients');
    }
    setLoading(false);
  };

  const handleAddPatient = () => {
    form.resetFields();
    setSelectedPatient(null);
    setModalVisible(true);
  };

  const handleEditPatient = (patient) => {
    setSelectedPatient(patient);
    form.setFieldsValue({
      ...patient,
      dateOfBirth: moment(patient.dateOfBirth)
    });
    setModalVisible(true);
  };

  const handleViewPatient = (patient) => {
    setSelectedPatient(patient);
    setDrawerVisible(true);
  };

  const handleSubmit = async (values) => {
    try {
      const patientData = {
        ...values,
        dateOfBirth: values.dateOfBirth.format('YYYY-MM-DD')
      };
      
      if (selectedPatient) {
        // Update patient
        message.success('Patient updated successfully');
      } else {
        // Create new patient
        message.success('Patient created successfully');
      }
      
      setModalVisible(false);
      loadPatients();
    } catch (error) {
      message.error('Failed to save patient');
    }
  };

  const columns = [
    {
      title: 'Patient ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      fixed: 'left'
    },
    {
      title: 'Name',
      key: 'name',
      width: 200,
      render: (_, record) => (
        <Space>
          <Avatar style={{ background: 'var(--sa-blue)' }}>
            {record.firstName[0]}{record.lastName[0]}
          </Avatar>
          <span>{record.firstName} {record.lastName}</span>
        </Space>
      )
    },
    {
      title: 'ID Number',
      dataIndex: 'idNumber',
      key: 'idNumber',
      width: 150
    },
    {
      title: 'Gender',
      dataIndex: 'gender',
      key: 'gender',
      width: 100
    },
    {
      title: 'Phone',
      dataIndex: 'phone',
      key: 'phone',
      width: 150
    },
    {
      title: 'Medical Aid',
      dataIndex: 'medicalAid',
      key: 'medicalAid',
      width: 150
    },
    {
      title: 'Last Visit',
      dataIndex: 'lastVisit',
      key: 'lastVisit',
      width: 120,
      render: (date) => moment(date).format('YYYY-MM-DD')
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => (
        <Tag color={status === 'Active' ? 'green' : 'red'}>{status}</Tag>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewPatient(record)}
          >
            View
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditPatient(record)}
          >
            Edit
          </Button>
        </Space>
      )
    }
  ];

  const filteredPatients = patients.filter(p =>
    `${p.firstName} ${p.lastName} ${p.idNumber} ${p.phone}`.toLowerCase().includes(searchText.toLowerCase())
  );

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: '24px' }}>
          <Col>
            <h2 style={{ margin: 0 }}>
              <UserOutlined style={{ marginRight: '8px' }} />
              Patient Management
            </h2>
          </Col>
          <Col>
            <Space>
              <Input.Search
                placeholder="Search patients..."
                style={{ width: 300 }}
                onChange={(e) => setSearchText(e.target.value)}
                allowClear
              />
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAddPatient}
                style={{ background: 'var(--sa-blue)' }}
              >
                Add Patient
              </Button>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={filteredPatients}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1200 }}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Add/Edit Patient Modal */}
      <Modal
        title={selectedPatient ? 'Edit Patient' : 'Add New Patient'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="firstName"
                label="First Name"
                rules={[{ required: true, message: 'Please enter first name' }]}
              >
                <Input prefix={<UserOutlined />} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="lastName"
                label="Last Name"
                rules={[{ required: true, message: 'Please enter last name' }]}
              >
                <Input prefix={<UserOutlined />} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="idNumber"
                label="ID Number"
                rules={[{ required: true, message: 'Please enter ID number' }]}
              >
                <Input prefix={<IdcardOutlined />} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="dateOfBirth"
                label="Date of Birth"
                rules={[{ required: true, message: 'Please select date of birth' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="gender"
                label="Gender"
                rules={[{ required: true, message: 'Please select gender' }]}
              >
                <Select>
                  <Option value="Male">Male</Option>
                  <Option value="Female">Female</Option>
                  <Option value="Other">Other</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="phone"
                label="Phone Number"
                rules={[{ required: true, message: 'Please enter phone number' }]}
              >
                <Input prefix={<PhoneOutlined />} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="email"
            label="Email"
            rules={[{ type: 'email', message: 'Please enter valid email' }]}
          >
            <Input prefix={<MailOutlined />} />
          </Form.Item>

          <Form.Item
            name="address"
            label="Address"
          >
            <TextArea rows={2} prefix={<HomeOutlined />} />
          </Form.Item>

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
                  <Option value="None">None</Option>
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
                {selectedPatient ? 'Update' : 'Create'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Patient Details Drawer */}
      <Drawer
        title="Patient Details"
        placement="right"
        width={720}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedPatient && (
          <Tabs defaultActiveKey="1">
            <TabPane tab="Demographics" key="1">
              <Descriptions bordered column={1}>
                <Descriptions.Item label="Patient ID">{selectedPatient.id}</Descriptions.Item>
                <Descriptions.Item label="Full Name">
                  {selectedPatient.firstName} {selectedPatient.lastName}
                </Descriptions.Item>
                <Descriptions.Item label="ID Number">{selectedPatient.idNumber}</Descriptions.Item>
                <Descriptions.Item label="Date of Birth">{selectedPatient.dateOfBirth}</Descriptions.Item>
                <Descriptions.Item label="Gender">{selectedPatient.gender}</Descriptions.Item>
                <Descriptions.Item label="Phone">{selectedPatient.phone}</Descriptions.Item>
                <Descriptions.Item label="Email">{selectedPatient.email}</Descriptions.Item>
                <Descriptions.Item label="Address">{selectedPatient.address}</Descriptions.Item>
                <Descriptions.Item label="Medical Aid">{selectedPatient.medicalAid}</Descriptions.Item>
                <Descriptions.Item label="Medical Aid Number">{selectedPatient.medicalAidNumber}</Descriptions.Item>
              </Descriptions>
            </TabPane>
            <TabPane tab="Medical History" key="2">
              <p>Medical history will be displayed here</p>
            </TabPane>
            <TabPane tab="Studies" key="3">
              <p>Imaging studies will be displayed here</p>
            </TabPane>
            <TabPane tab="Reports" key="4">
              <p>Radiology reports will be displayed here</p>
            </TabPane>
          </Tabs>
        )}
      </Drawer>
    </div>
  );
};

export default PatientManagement;
