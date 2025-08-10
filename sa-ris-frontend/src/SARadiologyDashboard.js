import React, { useState, useEffect } from 'react';
import {
  Layout,
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Progress,
  Timeline,
  Alert,
  Button,
  Select,
  DatePicker,
  Modal,
  Form,
  Input,
  Upload,
  message,
  Badge,
  Tooltip,
  Space,
  Divider
} from 'antd';
import {
  DashboardOutlined,
  CalendarOutlined,
  UserOutlined,
  FileImageOutlined,
  DollarOutlined,
  ClockCircleOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  UploadOutlined,
  PrinterOutlined,
  DownloadOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import axios from 'axios';
import moment from 'moment';
import io from 'socket.io-client';

const { Header, Content, Sider } = Layout;
const { Option } = Select;
const { RangePicker } = DatePicker;

// Real-time socket connection
const socket = io('ws://localhost:3001');

const SARadiologyDashboard = () => {
  const [loading, setLoading] = useState(false);
  const [dashboardData, setDashboardData] = useState({
    currentStatus: [],
    urgentCases: [],
    criticalFindings: [],
    pendingReports: [],
    radiologistWorkload: [],
    equipmentStatus: [],
    performanceMetrics: {}
  });
  const [selectedTimeRange, setSelectedTimeRange] = useState('today');
  const [workflowModalVisible, setWorkflowModalVisible] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [billingData, setBillingData] = useState([]);

  useEffect(() => {
    loadDashboardData();
    
    // Setup real-time updates
    socket.on('workflow_update', (data) => {
      updateWorkflowStatus(data);
    });
    
    socket.on('critical_finding', (data) => {
      showCriticalFindingAlert(data);
    });
    
    socket.on('equipment_status', (data) => {
      updateEquipmentStatus(data);
    });
    
    // Refresh data every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    
    return () => {
      clearInterval(interval);
      socket.disconnect();
    };
  }, [selectedTimeRange]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/dashboard?range=${selectedTimeRange}`);
      setDashboardData(response.data);
      
      const billingResponse = await axios.get(`/api/billing/summary?range=${selectedTimeRange}`);
      setBillingData(billingResponse.data);
    } catch (error) {
      message.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const updateWorkflowStatus = (data) => {
    setDashboardData(prev => ({
      ...prev,
      currentStatus: prev.currentStatus.map(item => 
        item.workflow_id === data.workflow_id ? { ...item, ...data } : item
      )
    }));
  };

  const showCriticalFindingAlert = (data) => {
    Modal.error({
      title: 'Critical Finding Alert',
      content: (
        <div>
          <p><strong>Patient:</strong> {data.patient_name}</p>
          <p><strong>Examination:</strong> {data.examination_type}</p>
          <p><strong>Finding:</strong> {data.finding}</p>
          <p><strong>Urgency:</strong> IMMEDIATE ATTENTION REQUIRED</p>
        </div>
      ),
      onOk: () => handleCriticalFinding(data)
    });
  };

  const handleCriticalFinding = async (data) => {
    try {
      await axios.post('/api/critical-findings/acknowledge', {
        workflow_id: data.workflow_id,
        acknowledged_by: 'current_user'
      });
      message.success('Critical finding acknowledged');
    } catch (error) {
      message.error('Failed to acknowledge critical finding');
    }
  };

  const updateEquipmentStatus = (data) => {
    setDashboardData(prev => ({
      ...prev,
      equipmentStatus: prev.equipmentStatus.map(equipment => 
        equipment.id === data.equipment_id ? { ...equipment, ...data } : equipment
      )
    }));
  };

  // Workflow status columns
  const workflowColumns = [
    {
      title: 'Patient',
      dataIndex: 'patient_name',
      key: 'patient_name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            ID: {record.patient_id}
          </div>
        </div>
      )
    },
    {
      title: 'Examination',
      dataIndex: 'examination_type',
      key: 'examination_type',
      render: (text) => (
        <Tag color="blue">{text.toUpperCase()}</Tag>
      )
    },
    {
      title: 'Status',
      dataIndex: 'current_state',
      key: 'current_state',
      render: (status) => {
        const statusConfig = {
          'BOOKED': { color: 'orange', icon: <CalendarOutlined /> },
          'REGISTERED': { color: 'blue', icon: <UserOutlined /> },
          'IN_PROGRESS': { color: 'purple', icon: <ClockCircleOutlined /> },
          'COMPLETED': { color: 'green', icon: <CheckCircleOutlined /> },
          'PRELIMINARY_READ': { color: 'gold', icon: <FileImageOutlined /> },
          'FINAL_REPORT': { color: 'success', icon: <CheckCircleOutlined /> }
        };
        
        const config = statusConfig[status] || { color: 'default', icon: null };
        
        return (
          <Tag color={config.color} icon={config.icon}>
            {status.replace('_', ' ')}
          </Tag>
        );
      }
    },
    {
      title: 'Urgency',
      dataIndex: 'urgency',
      key: 'urgency',
      render: (urgency) => {
        const urgencyColors = {
          'stat': 'red',
          'urgent': 'orange',
          'routine': 'green'
        };
        return (
          <Tag color={urgencyColors[urgency]}>
            {urgency.toUpperCase()}
          </Tag>
        );
      }
    },
    {
      title: 'Medical Aid',
      dataIndex: 'medical_aid',
      key: 'medical_aid',
      render: (aid) => aid ? aid.toUpperCase() : 'CASH'
    },
    {
      title: 'Progress',
      dataIndex: 'progress_percentage',
      key: 'progress',
      render: (progress) => (
        <Progress 
          percent={progress} 
          size="small" 
          status={progress === 100 ? 'success' : 'active'}
        />
      )
    },
    {
      title: 'Est. Completion',
      dataIndex: 'estimated_completion',
      key: 'estimated_completion',
      render: (time) => moment(time).format('HH:mm')
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            type="primary" 
            size="small"
            onClick={() => openWorkflowModal(record)}
          >
            View Details
          </Button>
          <Button 
            size="small"
            onClick={() => advanceWorkflow(record.workflow_id)}
          >
            Advance
          </Button>
        </Space>
      )
    }
  ];

  // Performance metrics chart data
  const performanceData = [
    { name: 'Mon', examinations: 24, reports: 22, revenue: 45000 },
    { name: 'Tue', examinations: 28, reports: 26, revenue: 52000 },
    { name: 'Wed', examinations: 32, reports: 30, revenue: 58000 },
    { name: 'Thu', examinations: 25, reports: 24, revenue: 48000 },
    { name: 'Fri', examinations: 30, reports: 28, revenue: 55000 },
    { name: 'Sat', examinations: 18, reports: 18, revenue: 35000 },
    { name: 'Sun', examinations: 12, reports: 12, revenue: 22000 }
  ];

  // Medical aid distribution data
  const medicalAidData = [
    { name: 'Discovery', value: 35, color: '#0088FE' },
    { name: 'Momentum', value: 25, color: '#00C49F' },
    { name: 'Bonitas', value: 20, color: '#FFBB28' },
    { name: 'GEMS', value: 15, color: '#FF8042' },
    { name: 'Cash', value: 5, color: '#8884d8' }
  ];

  const openWorkflowModal = (patient) => {
    setSelectedPatient(patient);
    setWorkflowModalVisible(true);
  };

  const advanceWorkflow = async (workflowId) => {
    try {
      const response = await axios.post(`/api/workflow/${workflowId}/advance`);
      if (response.data.success) {
        message.success('Workflow advanced successfully');
        loadDashboardData();
      }
    } catch (error) {
      message.error('Failed to advance workflow');
    }
  };

  const generateReport = async (workflowId) => {
    try {
      const response = await axios.post(`/api/workflow/${workflowId}/generate-report`);
      if (response.data.success) {
        message.success('AI report generated successfully');
        loadDashboardData();
      }
    } catch (error) {
      message.error('Failed to generate report');
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ 
        background: '#1890ff', 
        color: 'white', 
        display: 'flex', 
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <FileImageOutlined style={{ fontSize: '24px', marginRight: '16px' }} />
          <h2 style={{ color: 'white', margin: 0 }}>
            Ubuntu Patient Sorg - SA Radiology Information System
          </h2>
        </div>
        <div>
          <Select
            value={selectedTimeRange}
            onChange={setSelectedTimeRange}
            style={{ width: 120, marginRight: 16 }}
          >
            <Option value="today">Today</Option>
            <Option value="week">This Week</Option>
            <Option value="month">This Month</Option>
          </Select>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={loadDashboardData}
            loading={loading}
            style={{ color: 'white', borderColor: 'white' }}
          >
            Refresh
          </Button>
        </div>
      </Header>

      <Content style={{ padding: '24px' }}>
        {/* Key Performance Indicators */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Today's Examinations"
                value={dashboardData.performanceMetrics.total_examinations || 0}
                prefix={<FileImageOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Pending Reports"
                value={dashboardData.pendingReports?.length || 0}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Revenue Today"
                value={dashboardData.performanceMetrics.total_revenue || 0}
                prefix={<DollarOutlined />}
                precision={2}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Critical Findings"
                value={dashboardData.criticalFindings?.length || 0}
                prefix={<AlertOutlined />}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Critical Alerts */}
        {dashboardData.criticalFindings?.length > 0 && (
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col span={24}>
              <Alert
                message="Critical Findings Require Immediate Attention"
                description={`${dashboardData.criticalFindings.length} critical findings pending review`}
                type="error"
                showIcon
                closable
                action={
                  <Button size="small" danger>
                    Review Now
                  </Button>
                }
              />
            </Col>
          </Row>
        )}

        {/* Main Dashboard Content */}
        <Row gutter={[16, 16]}>
          {/* Current Workflow Status */}
          <Col span={16}>
            <Card 
              title="Current Workflow Status" 
              extra={
                <Space>
                  <Badge count={dashboardData.urgentCases?.length || 0} showZero>
                    <Button icon={<AlertOutlined />}>Urgent Cases</Button>
                  </Badge>
                </Space>
              }
            >
              <Table
                columns={workflowColumns}
                dataSource={dashboardData.currentStatus}
                rowKey="workflow_id"
                pagination={{ pageSize: 10 }}
                loading={loading}
                scroll={{ x: 1200 }}
              />
            </Card>
          </Col>

          {/* Radiologist Workload */}
          <Col span={8}>
            <Card title="Radiologist Workload">
              <Timeline>
                {dashboardData.radiologistWorkload?.map((radiologist, index) => (
                  <Timeline.Item
                    key={index}
                    color={radiologist.workload > 10 ? 'red' : 'green'}
                    dot={radiologist.workload > 10 ? <ExclamationCircleOutlined /> : <CheckCircleOutlined />}
                  >
                    <div>
                      <strong>{radiologist.name}</strong>
                      <br />
                      <span>Cases: {radiologist.pending_cases}</span>
                      <br />
                      <Progress 
                        percent={Math.min(radiologist.workload * 10, 100)} 
                        size="small"
                        status={radiologist.workload > 10 ? 'exception' : 'normal'}
                      />
                    </div>
                  </Timeline.Item>
                ))}
              </Timeline>
            </Card>
          </Col>
        </Row>

        {/* Performance Charts */}
        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          <Col span={12}>
            <Card title="Weekly Performance Trends">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <RechartsTooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="examinations" 
                    stroke="#8884d8" 
                    name="Examinations"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="reports" 
                    stroke="#82ca9d" 
                    name="Reports"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </Col>

          <Col span={12}>
            <Card title="Medical Aid Distribution">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={medicalAidData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {medicalAidData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>

        {/* Equipment Status */}
        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          <Col span={24}>
            <Card title="Equipment Status">
              <Row gutter={[16, 16]}>
                {dashboardData.equipmentStatus?.map((equipment, index) => (
                  <Col span={6} key={index}>
                    <Card 
                      size="small"
                      title={equipment.name}
                      extra={
                        <Tag color={equipment.status === 'operational' ? 'green' : 'red'}>
                          {equipment.status.toUpperCase()}
                        </Tag>
                      }
                    >
                      <div>
                        <p>Utilization: {equipment.utilization}%</p>
                        <Progress percent={equipment.utilization} size="small" />
                        <p style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                          Last Service: {moment(equipment.last_service).format('DD/MM/YYYY')}
                        </p>
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          </Col>
        </Row>
      </Content>

      {/* Workflow Detail Modal */}
      <Modal
        title="Workflow Details"
        visible={workflowModalVisible}
        onCancel={() => setWorkflowModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setWorkflowModalVisible(false)}>
            Close
          </Button>,
          <Button 
            key="report" 
            type="primary" 
            onClick={() => generateReport(selectedPatient?.workflow_id)}
          >
            Generate AI Report
          </Button>
        ]}
      >
        {selectedPatient && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <h4>Patient Information</h4>
                <p><strong>Name:</strong> {selectedPatient.patient_name}</p>
                <p><strong>ID:</strong> {selectedPatient.patient_id}</p>
                <p><strong>Medical Aid:</strong> {selectedPatient.medical_aid}</p>
              </Col>
              <Col span={12}>
                <h4>Examination Details</h4>
                <p><strong>Type:</strong> {selectedPatient.examination_type}</p>
                <p><strong>Urgency:</strong> {selectedPatient.urgency}</p>
                <p><strong>Status:</strong> {selectedPatient.current_state}</p>
              </Col>
            </Row>
            
            <Divider />
            
            <h4>Workflow Progress</h4>
            <Timeline>
              <Timeline.Item color="green">Booking Confirmed</Timeline.Item>
              <Timeline.Item color="blue">Patient Registered</Timeline.Item>
              <Timeline.Item color="orange">Examination In Progress</Timeline.Item>
              <Timeline.Item color="red">Pending Report</Timeline.Item>
            </Timeline>
          </div>
        )}
      </Modal>
    </Layout>
  );
};

export default SARadiologyDashboard;
