import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Select, Space, message, Tag, Card, Row, Col, Descriptions, Tabs, Upload, Progress } from 'antd';
import { FileImageOutlined, EyeOutlined, DownloadOutlined, UploadOutlined, SearchOutlined, FilterOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import moment from 'moment';
import axios from 'axios';

const { Option } = Select;
const { TabPane } = Tabs;

const StudyManagement = () => {
  const [studies, setStudies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewerVisible, setViewerVisible] = useState(false);
  const [selectedStudy, setSelectedStudy] = useState(null);
  const [filters, setFilters] = useState({
    modality: 'all',
    status: 'all',
    dateRange: 'today'
  });

  useEffect(() => {
    loadStudies();
  }, [filters]);

  const loadStudies = async () => {
    setLoading(true);
    try {
      // Mock data - replace with actual API call to /api/dicom/studies
      const mockStudies = [
        {
          id: 'S001',
          studyInstanceUID: '1.2.840.113619.2.55.3.2831868576.123',
          patientId: 'P001',
          patientName: 'Thabo Mokoena',
          studyDate: '2025-10-17',
          studyTime: '09:15:00',
          modality: 'CT',
          bodyPart: 'Brain',
          description: 'CT Brain without contrast',
          status: 'Completed',
          reportStatus: 'Pending',
          seriesCount: 3,
          instanceCount: 150,
          radiologist: 'Dr. Mokoena',
          referringPhysician: 'Dr. Smith'
        },
        {
          id: 'S002',
          studyInstanceUID: '1.2.840.113619.2.55.3.2831868576.124',
          patientId: 'P002',
          patientName: 'Nomsa Dlamini',
          studyDate: '2025-10-17',
          studyTime: '10:30:00',
          modality: 'MRI',
          bodyPart: 'Spine',
          description: 'MRI Lumbar Spine',
          status: 'Completed',
          reportStatus: 'Reported',
          seriesCount: 5,
          instanceCount: 280,
          radiologist: 'Dr. Dlamini',
          referringPhysician: 'Dr. Jones'
        },
        {
          id: 'S003',
          studyInstanceUID: '1.2.840.113619.2.55.3.2831868576.125',
          patientId: 'P003',
          patientName: 'Sipho Nkosi',
          studyDate: '2025-10-17',
          studyTime: '14:00:00',
          modality: 'XR',
          bodyPart: 'Chest',
          description: 'Chest X-Ray PA and Lateral',
          status: 'In Progress',
          reportStatus: 'Not Started',
          seriesCount: 2,
          instanceCount: 2,
          radiologist: 'Unassigned',
          referringPhysician: 'Dr. Brown'
        }
      ];
      setStudies(mockStudies);
    } catch (error) {
      message.error('Failed to load studies');
    }
    setLoading(false);
  };

  const handleViewStudy = (study) => {
    setSelectedStudy(study);
    setViewerVisible(true);
  };

  const handleDownloadStudy = async (study) => {
    message.info(`Downloading study ${study.id}...`);
    // Implement DICOM download
  };

  const columns = [
    {
      title: 'Study ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      fixed: 'left'
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
      title: 'Study Date/Time',
      key: 'datetime',
      width: 150,
      render: (_, record) => (
        <div>
          <div>{moment(record.studyDate).format('YYYY-MM-DD')}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>{record.studyTime}</div>
        </div>
      )
    },
    {
      title: 'Modality',
      dataIndex: 'modality',
      key: 'modality',
      width: 100,
      render: (modality) => (
        <Tag color="blue">{modality}</Tag>
      )
    },
    {
      title: 'Body Part',
      dataIndex: 'bodyPart',
      key: 'bodyPart',
      width: 120
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      ellipsis: true
    },
    {
      title: 'Images',
      key: 'images',
      width: 100,
      render: (_, record) => (
        <div>
          <div>{record.seriesCount} series</div>
          <div style={{ fontSize: '12px', color: '#999' }}>{record.instanceCount} images</div>
        </div>
      )
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => (
        <Tag color={status === 'Completed' ? 'green' : 'orange'}>
          {status === 'Completed' ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
          {' '}{status}
        </Tag>
      )
    },
    {
      title: 'Report',
      dataIndex: 'reportStatus',
      key: 'reportStatus',
      width: 120,
      render: (status) => {
        const colors = {
          'Reported': 'green',
          'Pending': 'orange',
          'Not Started': 'default'
        };
        return <Tag color={colors[status]}>{status}</Tag>;
      }
    },
    {
      title: 'Radiologist',
      dataIndex: 'radiologist',
      key: 'radiologist',
      width: 150
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewStudy(record)}
          >
            View
          </Button>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => handleDownloadStudy(record)}
          >
            Download
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
              <FileImageOutlined style={{ marginRight: '8px' }} />
              Study Management
            </h2>
          </Col>
          <Col>
            <Space>
              <Select
                value={filters.modality}
                onChange={(value) => setFilters({ ...filters, modality: value })}
                style={{ width: 120 }}
              >
                <Option value="all">All Modalities</Option>
                <Option value="CT">CT</Option>
                <Option value="MRI">MRI</Option>
                <Option value="XR">X-Ray</Option>
                <Option value="US">Ultrasound</Option>
              </Select>
              <Select
                value={filters.status}
                onChange={(value) => setFilters({ ...filters, status: value })}
                style={{ width: 150 }}
              >
                <Option value="all">All Status</Option>
                <Option value="completed">Completed</Option>
                <Option value="in-progress">In Progress</Option>
              </Select>
              <Select
                value={filters.dateRange}
                onChange={(value) => setFilters({ ...filters, dateRange: value })}
                style={{ width: 120 }}
              >
                <Option value="today">Today</Option>
                <Option value="week">This Week</Option>
                <Option value="month">This Month</Option>
              </Select>
              <Button
                type="primary"
                icon={<UploadOutlined />}
                style={{ background: 'var(--sa-blue)' }}
              >
                Upload DICOM
              </Button>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={studies}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1600 }}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* DICOM Viewer Modal */}
      <Modal
        title={`Study Viewer - ${selectedStudy?.id}`}
        open={viewerVisible}
        onCancel={() => setViewerVisible(false)}
        width={1200}
        footer={null}
      >
        {selectedStudy && (
          <Tabs defaultActiveKey="1">
            <TabPane tab="Study Info" key="1">
              <Descriptions bordered column={2}>
                <Descriptions.Item label="Study ID">{selectedStudy.id}</Descriptions.Item>
                <Descriptions.Item label="Study UID">{selectedStudy.studyInstanceUID}</Descriptions.Item>
                <Descriptions.Item label="Patient">{selectedStudy.patientName}</Descriptions.Item>
                <Descriptions.Item label="Patient ID">{selectedStudy.patientId}</Descriptions.Item>
                <Descriptions.Item label="Study Date">{selectedStudy.studyDate}</Descriptions.Item>
                <Descriptions.Item label="Study Time">{selectedStudy.studyTime}</Descriptions.Item>
                <Descriptions.Item label="Modality">{selectedStudy.modality}</Descriptions.Item>
                <Descriptions.Item label="Body Part">{selectedStudy.bodyPart}</Descriptions.Item>
                <Descriptions.Item label="Description" span={2}>{selectedStudy.description}</Descriptions.Item>
                <Descriptions.Item label="Series Count">{selectedStudy.seriesCount}</Descriptions.Item>
                <Descriptions.Item label="Instance Count">{selectedStudy.instanceCount}</Descriptions.Item>
                <Descriptions.Item label="Radiologist">{selectedStudy.radiologist}</Descriptions.Item>
                <Descriptions.Item label="Referring Physician">{selectedStudy.referringPhysician}</Descriptions.Item>
              </Descriptions>
            </TabPane>
            <TabPane tab="DICOM Viewer" key="2">
              <div style={{
                height: '500px',
                background: '#000',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff'
              }}>
                <div style={{ textAlign: 'center' }}>
                  <FileImageOutlined style={{ fontSize: '64px', marginBottom: '16px' }} />
                  <p>DICOM Viewer Integration</p>
                  <p style={{ fontSize: '12px', color: '#999' }}>
                    Connect to Orthanc PACS or integrate OHIF Viewer
                  </p>
                </div>
              </div>
            </TabPane>
            <TabPane tab="Report" key="3">
              <p>Radiology report will be displayed here</p>
            </TabPane>
          </Tabs>
        )}
      </Modal>
    </div>
  );
};

export default StudyManagement;
