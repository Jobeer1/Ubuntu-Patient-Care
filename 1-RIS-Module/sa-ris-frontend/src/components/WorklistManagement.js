import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Select, Input, Row, Col, Badge } from 'antd';
import { UnorderedListOutlined, SearchOutlined, FilterOutlined, UserOutlined, ClockCircleOutlined } from '@ant-design/icons';
import moment from 'moment';

const { Option } = Select;

const WorklistManagement = () => {
  const [worklist, setWorklist] = useState([
    {
      id: 'W001',
      patientName: 'Thabo Mokoena',
      patientId: 'P001',
      accessionNumber: 'ACC20251017001',
      scheduledTime: '2025-10-17 09:00',
      modality: 'CT',
      bodyPart: 'Brain',
      priority: 'Urgent',
      status: 'Scheduled',
      radiologist: 'Unassigned',
      referringPhysician: 'Dr. Smith'
    },
    {
      id: 'W002',
      patientName: 'Nomsa Dlamini',
      patientId: 'P002',
      accessionNumber: 'ACC20251017002',
      scheduledTime: '2025-10-17 10:30',
      modality: 'MRI',
      bodyPart: 'Spine',
      priority: 'Routine',
      status: 'In Progress',
      radiologist: 'Dr. Dlamini',
      referringPhysician: 'Dr. Jones'
    },
    {
      id: 'W003',
      patientName: 'Sipho Nkosi',
      patientId: 'P003',
      accessionNumber: 'ACC20251017003',
      scheduledTime: '2025-10-17 14:00',
      modality: 'XR',
      bodyPart: 'Chest',
      priority: 'Routine',
      status: 'Completed',
      radiologist: 'Dr. Mokoena',
      referringPhysician: 'Dr. Brown'
    }
  ]);

  const [filters, setFilters] = useState({
    status: 'all',
    modality: 'all',
    priority: 'all'
  });

  const columns = [
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority) => {
        const colors = {
          'Urgent': 'red',
          'High': 'orange',
          'Routine': 'blue'
        };
        return <Badge status="processing" color={colors[priority]} text={priority} />;
      }
    },
    {
      title: 'Accession #',
      dataIndex: 'accessionNumber',
      key: 'accessionNumber',
      width: 180
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
      title: 'Scheduled Time',
      dataIndex: 'scheduledTime',
      key: 'scheduledTime',
      width: 150,
      render: (time) => moment(time).format('HH:mm')
    },
    {
      title: 'Exam',
      key: 'exam',
      width: 200,
      render: (_, record) => (
        <div>
          <Tag color="blue">{record.modality}</Tag>
          <span>{record.bodyPart}</span>
        </div>
      )
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => {
        const colors = {
          'Scheduled': 'default',
          'In Progress': 'processing',
          'Completed': 'success',
          'Cancelled': 'error'
        };
        return <Tag color={colors[status]}>{status}</Tag>;
      }
    },
    {
      title: 'Radiologist',
      dataIndex: 'radiologist',
      key: 'radiologist',
      width: 150,
      render: (radiologist) => (
        <span style={{ color: radiologist === 'Unassigned' ? '#999' : 'inherit' }}>
          {radiologist}
        </span>
      )
    },
    {
      title: 'Referring MD',
      dataIndex: 'referringPhysician',
      key: 'referringPhysician',
      width: 150
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small">View</Button>
          <Button type="link" size="small">Assign</Button>
        </Space>
      )
    }
  ];

  const filteredWorklist = worklist.filter(item => {
    if (filters.status !== 'all' && item.status !== filters.status) return false;
    if (filters.modality !== 'all' && item.modality !== filters.modality) return false;
    if (filters.priority !== 'all' && item.priority !== filters.priority) return false;
    return true;
  });

  const stats = {
    total: worklist.length,
    scheduled: worklist.filter(w => w.status === 'Scheduled').length,
    inProgress: worklist.filter(w => w.status === 'In Progress').length,
    completed: worklist.filter(w => w.status === 'Completed').length,
    urgent: worklist.filter(w => w.priority === 'Urgent').length
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={4}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--sa-blue)' }}>
                {stats.total}
              </div>
              <div style={{ fontSize: '12px', color: '#999' }}>Total</div>
            </div>
          </Card>
        </Col>
        <Col span={5}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'orange' }}>
                {stats.scheduled}
              </div>
              <div style={{ fontSize: '12px', color: '#999' }}>Scheduled</div>
            </div>
          </Card>
        </Col>
        <Col span={5}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'blue' }}>
                {stats.inProgress}
              </div>
              <div style={{ fontSize: '12px', color: '#999' }}>In Progress</div>
            </div>
          </Card>
        </Col>
        <Col span={5}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--sa-green)' }}>
                {stats.completed}
              </div>
              <div style={{ fontSize: '12px', color: '#999' }}>Completed</div>
            </div>
          </Card>
        </Col>
        <Col span={5}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'red' }}>
                {stats.urgent}
              </div>
              <div style={{ fontSize: '12px', color: '#999' }}>Urgent</div>
            </div>
          </Card>
        </Col>
      </Row>

      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: '24px' }}>
          <Col>
            <h2 style={{ margin: 0 }}>
              <UnorderedListOutlined style={{ marginRight: '8px' }} />
              Radiology Worklist
            </h2>
          </Col>
          <Col>
            <Space>
              <Input
                placeholder="Search..."
                prefix={<SearchOutlined />}
                style={{ width: 200 }}
              />
              <Select
                value={filters.status}
                onChange={(value) => setFilters({ ...filters, status: value })}
                style={{ width: 150 }}
              >
                <Option value="all">All Status</Option>
                <Option value="Scheduled">Scheduled</Option>
                <Option value="In Progress">In Progress</Option>
                <Option value="Completed">Completed</Option>
              </Select>
              <Select
                value={filters.modality}
                onChange={(value) => setFilters({ ...filters, modality: value })}
                style={{ width: 120 }}
              >
                <Option value="all">All Modalities</Option>
                <Option value="CT">CT</Option>
                <Option value="MRI">MRI</Option>
                <Option value="XR">X-Ray</Option>
              </Select>
              <Select
                value={filters.priority}
                onChange={(value) => setFilters({ ...filters, priority: value })}
                style={{ width: 120 }}
              >
                <Option value="all">All Priority</Option>
                <Option value="Urgent">Urgent</Option>
                <Option value="High">High</Option>
                <Option value="Routine">Routine</Option>
              </Select>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={filteredWorklist}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1400 }}
        />
      </Card>
    </div>
  );
};

export default WorklistManagement;
