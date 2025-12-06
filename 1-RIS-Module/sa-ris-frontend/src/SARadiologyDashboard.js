import { useState, useEffect } from 'react';
import { Layout, Card, Row, Col, Button, Select, message, Badge, Space, Avatar, Typography, List, Drawer, Modal, Form, Input, DatePicker, Radio } from 'antd';
import { DashboardOutlined, UserOutlined, FileImageOutlined, AlertOutlined, CheckCircleOutlined, HeartOutlined, GlobalOutlined, TeamOutlined, BellOutlined, ReloadOutlined, SettingOutlined, FileProtectOutlined, HddOutlined, SafetyOutlined, RiseOutlined, CalendarOutlined, UnorderedListOutlined, FileTextOutlined, DollarOutlined, PlusOutlined, SearchOutlined, SafetyCertificateOutlined, CreditCardOutlined, NotificationOutlined, UserAddOutlined } from '@ant-design/icons';
import moment from 'moment';
import io from 'socket.io-client';
import { useAccessibility, LanguageSwitcher, AccessibilitySettings } from './components/AccessibilityContext';
import MedicalAuthorizationPanel from './components/MedicalAuthorizationPanel';
import PatientManagement from './components/PatientManagement';
import AppointmentScheduling from './components/AppointmentScheduling';
import StudyManagement from './components/StudyManagement';
import ReportingSystem from './components/ReportingSystem';
import WorklistManagement from './components/WorklistManagement';
import BillingSystem from './components/BillingSystem';
import './styles/sa-eye-candy.css';

const { Header, Content, Sider, Footer } = Layout;
const { Title, Text } = Typography;
const { Option } = Select;

const socket = io('ws://localhost:3001');

const SARadiologyDashboard = () => {
  const accessibility = useAccessibility();
  const [loading, setLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [notificationDrawerVisible, setNotificationDrawerVisible] = useState(false);
  const [settingsDrawerVisible, setSettingsDrawerVisible] = useState(false);
  const [currentView, setCurrentView] = useState('dashboard'); // dashboard, authorization, patients, appointments, studies, worklist, reports, billing
  const [patientRegistrationVisible, setPatientRegistrationVisible] = useState(false);
  const [advancedSearchVisible, setAdvancedSearchVisible] = useState(false);
  const [benefitsCheckVisible, setBenefitsCheckVisible] = useState(false);
  const [authRequestVisible, setAuthRequestVisible] = useState(false);
  const [form] = Form.useForm();
  const [dashboardData, setDashboardData] = useState({
    todayStudies: 45,
    completedReports: 32,
    pendingCases: 13,
    criticalFindings: 3,
    urgentCases: [],
    radiologistWorkload: [],
    equipmentStatus: [],
    notifications: []
  });
  const [selectedTimeRange, setSelectedTimeRange] = useState('today');

  useEffect(() => {
    loadDashboardData();
    socket.on('critical_finding', (data) => {
      message.warning(`${accessibility.translate('criticalFindings')}: ${data.description}`);
      accessibility.announceToScreenReader(`${accessibility.translate('criticalFindings')}: ${data.description}`);
    });
    return () => socket.off('critical_finding');
  }, [accessibility]);

  const loadDashboardData = async () => {
    setLoading(true);
    accessibility.announceToScreenReader(accessibility.translate('loading'));
    setDashboardData({
      todayStudies: 45,
      completedReports: 32,
      pendingCases: 13,
      criticalFindings: 3,
      urgentCases: [
        { id: 1, patientName: 'John Nkosi', modality: 'CT Brain', urgency: 'High', scheduledTime: moment().add(30, 'minutes') },
        { id: 2, patientName: 'Sarah Zulu', modality: 'MRI Spine', urgency: 'Critical', scheduledTime: moment().add(15, 'minutes') }
      ],
      radiologistWorkload: [
        { name: 'Dr. Thabo Mokoena', workload: 85, pending: 12 },
        { name: 'Dr. Nomsa Dlamini', workload: 65, pending: 8 },
        { name: 'Dr. Sipho Nkosi', workload: 90, pending: 15 }
      ],
      equipmentStatus: [
        { id: 1, name: 'Siemens CT Scanner', status: 'online', location: 'Room 101', lastCheck: moment() },
        { id: 2, name: 'GE MRI Machine', status: 'maintenance', location: 'Room 203', lastCheck: moment().subtract(2, 'hours') }
      ],
      notifications: [
        { id: 1, title: 'System Update', message: 'New features available', timestamp: moment() }
      ]
    });
    setLoading(false);
    accessibility.announceToScreenReader(accessibility.translate('dashboard') + ' ' + accessibility.translate('loaded'));
  };

  const handlePatientRegistration = async (values) => {
    try {
      const response = await fetch('http://localhost:3001/api/patients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      });
      const data = await response.json();
      if (data.success) {
        message.success('Patient registered successfully!');
        setPatientRegistrationVisible(false);
        form.resetFields();
      }
    } catch (error) {
      message.error('Failed to register patient');
    }
  };

  const handleAdvancedSearch = async (values) => {
    try {
      // Search using same database as NAS integration
      const queryParams = new URLSearchParams(values).toString();
      const response = await fetch(`http://localhost:3001/api/patients?${queryParams}`);
      const data = await response.json();
      if (data.success) {
        message.success(`Found ${data.data.length} patients`);
        // Navigate to patients view with results
        setCurrentView('patients');
        setAdvancedSearchVisible(false);
      }
    } catch (error) {
      message.error('Search failed');
    }
  };

  const handleBenefitsCheck = async (values) => {
    try {
      const response = await fetch('http://localhost:3001/api/medical-auth/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      });
      const data = await response.json();
      if (data.success) {
        message.success('Benefits verified successfully!');
        Modal.info({
          title: 'Benefits Check Result',
          content: (
            <div>
              <p><strong>Member:</strong> {data.data.memberName}</p>
              <p><strong>Scheme:</strong> {data.data.schemeName}</p>
              <p><strong>Status:</strong> {data.data.status}</p>
              <p><strong>Benefits Available:</strong> {data.data.benefitsAvailable ? 'Yes' : 'No'}</p>
            </div>
          )
        });
        setBenefitsCheckVisible(false);
      }
    } catch (error) {
      message.error('Benefits check failed');
    }
  };

  const handleAuthRequest = async (values) => {
    try {
      const response = await fetch('http://localhost:3001/api/medical-auth/preauth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      });
      const data = await response.json();
      if (data.success) {
        message.success('Authorization request submitted successfully!');
        Modal.success({
          title: 'Authorization Request Submitted',
          content: (
            <div>
              <p><strong>Request ID:</strong> {data.data.requestId}</p>
              <p><strong>Status:</strong> {data.data.status}</p>
              <p>You will be notified when the authorization is processed.</p>
            </div>
          )
        });
        setAuthRequestVisible(false);
        form.resetFields();
      }
    } catch (error) {
      message.error('Authorization request failed');
    }
  };

  const renderDashboard = () => (
    <div style={{ padding: '24px', minHeight: '100vh', background: 'var(--sa-gray-50)' }}>
      {/* Welcome Header */}
      <div className="sa-card" style={{ padding: '24px', marginBottom: '24px' }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={2} className="sa-text-primary" style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
              <HeartOutlined style={{ marginRight: '12px', color: 'var(--sa-red)' }} />
              Welcome back, Admin!
            </Title>
            <Text style={{ color: 'var(--sa-gray-600)', marginTop: '4px', display: 'block' }}>
              South African Radiology Information System Dashboard
            </Text>
          </Col>
          <Col>
            <div style={{
              width: '48px',
              height: '48px',
              background: 'linear-gradient(135deg, var(--sa-blue), var(--sa-red))',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <GlobalOutlined style={{ fontSize: '24px', color: 'white' }} />
            </div>
          </Col>
        </Row>
      </div>

      {/* Quick Actions */}
      <div className="sa-card" style={{ padding: '24px', marginBottom: '24px' }}>
        <Title level={4} className="sa-text-primary" style={{ marginBottom: '16px' }}>Quick Actions</Title>
        <Row gutter={[12, 12]}>
          <Col xs={24} sm={12} md={6}>
            <Button
              type="primary"
              icon={<UserAddOutlined />}
              block
              size="large"
              onClick={() => setPatientRegistrationVisible(true)}
              style={{
                height: '56px',
                background: 'linear-gradient(135deg, var(--sa-blue), #0056b3)',
                borderColor: 'var(--sa-blue)',
                fontWeight: 600,
                fontSize: '15px'
              }}
            >
              Register Patient
            </Button>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Button
              icon={<SearchOutlined />}
              block
              size="large"
              onClick={() => setAdvancedSearchVisible(true)}
              style={{
                height: '56px',
                borderColor: 'var(--sa-blue)',
                color: 'var(--sa-blue)',
                fontWeight: 600,
                fontSize: '15px'
              }}
            >
              Advanced Search
            </Button>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Button
              icon={<CreditCardOutlined />}
              block
              size="large"
              onClick={() => setBenefitsCheckVisible(true)}
              style={{
                height: '56px',
                borderColor: 'var(--sa-green)',
                color: 'var(--sa-green)',
                fontWeight: 600,
                fontSize: '15px'
              }}
            >
              Benefits Check
            </Button>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Button
              icon={<SafetyCertificateOutlined />}
              block
              size="large"
              onClick={() => setAuthRequestVisible(true)}
              style={{
                height: '56px',
                borderColor: '#800080',
                color: '#800080',
                fontWeight: 600,
                fontSize: '15px'
              }}
            >
              Authorization Request
            </Button>
          </Col>
        </Row>
      </div>

      {/* System Status */}
      <div className="sa-card" style={{ padding: '24px', marginBottom: '24px' }}>
        <Title level={4} className="sa-text-primary" style={{ marginBottom: '16px' }}>System Status</Title>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              padding: '12px',
              background: 'rgba(0, 122, 51, 0.1)',
              borderRadius: 'var(--sa-radius-md)',
              border: '1px solid rgba(0, 122, 51, 0.2)'
            }}>
              <CheckCircleOutlined style={{ fontSize: '20px', color: 'var(--sa-green)', marginRight: '12px' }} />
              <div>
                <Text strong style={{ color: 'var(--sa-green)', display: 'block', fontSize: '14px' }}>API Server</Text>
                <Text style={{ color: 'var(--sa-green)', fontSize: '12px' }}>Online</Text>
              </div>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              padding: '12px',
              background: 'rgba(0, 38, 84, 0.1)',
              borderRadius: 'var(--sa-radius-md)',
              border: '1px solid rgba(0, 38, 84, 0.2)'
            }}>
              <HddOutlined style={{ fontSize: '20px', color: 'var(--sa-blue)', marginRight: '12px' }} />
              <div>
                <Text strong style={{ color: 'var(--sa-blue)', display: 'block', fontSize: '14px' }}>NAS Storage</Text>
                <Text style={{ color: 'var(--sa-blue)', fontSize: '12px' }}>Connected</Text>
              </div>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              padding: '12px',
              background: 'rgba(128, 0, 128, 0.1)',
              borderRadius: 'var(--sa-radius-md)',
              border: '1px solid rgba(128, 0, 128, 0.2)'
            }}>
              <SafetyOutlined style={{ fontSize: '20px', color: '#800080', marginRight: '12px' }} />
              <div>
                <Text strong style={{ color: '#800080', display: 'block', fontSize: '14px' }}>Security</Text>
                <Text style={{ color: '#800080', fontSize: '12px' }}>2FA Enabled</Text>
              </div>
            </div>
          </Col>
        </Row>
      </div>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} md={6}>
          <div className="sa-card sa-will-change" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{
                padding: '12px',
                borderRadius: 'var(--sa-radius-md)',
                background: 'rgba(0, 38, 84, 0.1)',
                marginRight: '16px'
              }}>
                <FileImageOutlined style={{ fontSize: '24px', color: 'var(--sa-blue)' }} />
              </div>
              <div>
                <Text style={{ fontSize: '14px', color: 'var(--sa-gray-600)', display: 'block' }}>Today's Studies</Text>
                <Title level={2} className="sa-text-primary" style={{ margin: 0 }}>{dashboardData.todayStudies}</Title>
                <Text style={{ fontSize: '12px', color: 'var(--sa-gray-500)' }}>DICOM files stored</Text>
              </div>
            </div>
          </div>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <div className="sa-card sa-will-change" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{
                padding: '12px',
                borderRadius: 'var(--sa-radius-md)',
                background: 'rgba(0, 122, 51, 0.1)',
                marginRight: '16px'
              }}>
                <CheckCircleOutlined style={{ fontSize: '24px', color: 'var(--sa-green)' }} />
              </div>
              <div>
                <Text style={{ fontSize: '14px', color: 'var(--sa-gray-600)', display: 'block' }}>Completed Reports</Text>
                <Title level={2} style={{ margin: 0, color: 'var(--sa-green)' }}>{dashboardData.completedReports}</Title>
                <Text style={{ fontSize: '12px', color: 'var(--sa-gray-500)' }}>Active accounts</Text>
              </div>
            </div>
          </div>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <div className="sa-card sa-will-change" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{
                padding: '12px',
                borderRadius: 'var(--sa-radius-md)',
                background: 'rgba(128, 0, 128, 0.1)',
                marginRight: '16px'
              }}>
                <RiseOutlined style={{ fontSize: '24px', color: '#800080' }} />
              </div>
              <div>
                <Text style={{ fontSize: '14px', color: 'var(--sa-gray-600)', display: 'block' }}>Recent Uploads</Text>
                <Title level={2} style={{ margin: 0, color: '#800080' }}>{dashboardData.pendingCases}</Title>
                <Text style={{ fontSize: '12px', color: 'var(--sa-gray-500)' }}>Last 7 days</Text>
              </div>
            </div>
          </div>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <div className="sa-card sa-will-change" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{
                padding: '12px',
                borderRadius: 'var(--sa-radius-md)',
                background: 'rgba(255, 140, 0, 0.1)',
                marginRight: '16px'
              }}>
                <HddOutlined style={{ fontSize: '24px', color: '#FF8C00' }} />
              </div>
              <div>
                <Text style={{ fontSize: '14px', color: 'var(--sa-gray-600)', display: 'block' }}>Storage Used</Text>
                <Title level={2} style={{ margin: 0, color: '#FF8C00' }}>125 GB</Title>
                <Text style={{ fontSize: '12px', color: 'var(--sa-gray-500)' }}>Total file size</Text>
              </div>
            </div>
          </div>
        </Col>
      </Row>

      {/* Content Grid */}
      <Row gutter={[24, 24]}>
        {/* Urgent Cases */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <AlertOutlined style={{ color: 'var(--sa-red)' }} />
                <span className="sa-text-primary">Urgent Cases</span>
              </Space>
            }
            className="sa-card"
            style={{ height: '100%' }}
          >
            {dashboardData.urgentCases.length > 0 ? (
              <List
                dataSource={dashboardData.urgentCases}
                renderItem={(item) => (
                  <List.Item
                    className="sa-list-item"
                    actions={[
                      <Button
                        type="primary"
                        size="small"
                        className="sa-btn sa-btn-primary sa-focus"
                        style={{ background: 'var(--sa-blue)', borderColor: 'var(--sa-blue)' }}
                      >
                        View
                      </Button>
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Badge status="error" />
                          <span className="sa-text-primary">{item.patientName}</span>
                          <Badge
                            count={item.urgency}
                            style={{ background: 'var(--sa-red)' }}
                          />
                        </Space>
                      }
                      description={
                        <div>
                          <Text className="sa-text-primary">{item.modality}</Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            Scheduled: {moment(item.scheduledTime).fromNow()}
                          </Text>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '32px', color: 'var(--sa-gray-500)' }}>
                <FileImageOutlined style={{ fontSize: '48px', color: 'var(--sa-gray-300)', marginBottom: '12px' }} />
                <p>No urgent cases</p>
              </div>
            )}
          </Card>
        </Col>

        {/* Radiologist Workload */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <TeamOutlined style={{ color: 'var(--sa-blue)' }} />
                <span className="sa-text-primary">Radiologist Workload</span>
              </Space>
            }
            className="sa-card"
            style={{ height: '100%' }}
          >
            <List
              dataSource={dashboardData.radiologistWorkload}
              renderItem={(item) => (
                <List.Item className="sa-list-item">
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        className="sa-avatar"
                        style={{ background: 'linear-gradient(135deg, var(--sa-blue), var(--sa-red))' }}
                      >
                        {item.name.split(' ').map(n => n[0]).join('')}
                      </Avatar>
                    }
                    title={<span className="sa-text-primary">{item.name}</span>}
                    description={
                      <div>
                        <div style={{
                          width: '100%',
                          height: '8px',
                          background: 'var(--sa-gray-200)',
                          borderRadius: '4px',
                          overflow: 'hidden',
                          marginBottom: '8px'
                        }}>
                          <div style={{
                            width: `${item.workload}%`,
                            height: '100%',
                            background: item.workload > 80
                              ? 'linear-gradient(90deg, var(--sa-red), var(--sa-red-light))'
                              : 'linear-gradient(90deg, var(--sa-green), var(--sa-green-light))',
                            transition: 'width 0.3s ease'
                          }}></div>
                        </div>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {item.pending} pending cases
                        </Text>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );

  return (
    <Layout className="sa-gpu-accelerated" style={{ minHeight: '100vh', background: 'var(--sa-gray-50)' }}>
      <Sider
        collapsible
        collapsed={sidebarCollapsed}
        onCollapse={setSidebarCollapsed}
        style={{ 
          background: 'var(--sa-white)', 
          borderRight: '1px solid var(--sa-gray-200)',
          boxShadow: '2px 0 8px rgba(0,0,0,0.05)'
        }}
        width={260}
      >
        <div style={{ 
          padding: '24px', 
          textAlign: 'center', 
          borderBottom: '1px solid var(--sa-gray-200)',
          background: 'linear-gradient(135deg, rgba(0, 38, 84, 0.05), rgba(224, 60, 49, 0.05))'
        }}>
          <Avatar
            size={sidebarCollapsed ? 40 : 64}
            style={{
              background: 'linear-gradient(135deg, var(--sa-blue), var(--sa-red), var(--sa-gold), var(--sa-green))',
              marginBottom: sidebarCollapsed ? 0 : '12px',
              transition: 'all 0.3s'
            }}
          >
            <GlobalOutlined style={{ fontSize: sidebarCollapsed ? '20px' : '32px', color: 'white' }} />
          </Avatar>
          {!sidebarCollapsed && (
            <div>
              <Title level={4} className="sa-text-primary" style={{ marginBottom: '4px', marginTop: '8px' }}>SA-RIS</Title>
              <Text style={{ fontSize: '12px', color: 'var(--sa-gray-600)' }}>Healthcare Excellence</Text>
            </div>
          )}
        </div>
        <div style={{ padding: '16px' }}>
          <Button
            type="text"
            icon={<DashboardOutlined />}
            block
            style={{ 
              textAlign: 'left',
              marginBottom: '8px',
              height: '40px',
              color: currentView === 'dashboard' ? 'var(--sa-blue)' : 'var(--sa-gray-700)',
              background: currentView === 'dashboard' ? 'rgba(0, 38, 84, 0.1)' : 'transparent',
              fontWeight: currentView === 'dashboard' ? 600 : 400,
              borderRadius: 'var(--sa-radius-md)'
            }}
            onClick={() => setCurrentView('dashboard')}
          >
            {!sidebarCollapsed && 'Dashboard'}
          </Button>
          <Button
            type="text"
            icon={<FileProtectOutlined />}
            block
            style={{ 
              textAlign: 'left',
              marginBottom: '8px',
              height: '40px',
              color: currentView === 'authorization' ? 'var(--sa-blue)' : 'var(--sa-gray-700)',
              background: currentView === 'authorization' ? 'rgba(0, 38, 84, 0.1)' : 'transparent',
              fontWeight: currentView === 'authorization' ? 600 : 400,
              borderRadius: 'var(--sa-radius-md)'
            }}
            onClick={() => setCurrentView('authorization')}
          >
            {!sidebarCollapsed && 'Medical Authorization'}
          </Button>
          <Button
            type="text"
            icon={<UserOutlined />}
            block
            style={{ 
              textAlign: 'left',
              marginBottom: '8px',
              height: '40px',
              color: currentView === 'patients' ? 'var(--sa-blue)' : 'var(--sa-gray-700)',
              background: currentView === 'patients' ? 'rgba(0, 38, 84, 0.1)' : 'transparent',
              fontWeight: currentView === 'patients' ? 600 : 400,
              borderRadius: 'var(--sa-radius-md)'
            }}
            onClick={() => setCurrentView('patients')}
          >
            {!sidebarCollapsed && 'Patients'}
          </Button>
          <Button
            type="text"
            icon={<CalendarOutlined />}
            block
            style={{ 
              textAlign: 'left',
              marginBottom: '8px',
              height: '40px',
              color: currentView === 'appointments' ? 'var(--sa-blue)' : 'var(--sa-gray-700)',
              background: currentView === 'appointments' ? 'rgba(0, 38, 84, 0.1)' : 'transparent',
              fontWeight: currentView === 'appointments' ? 600 : 400,
              borderRadius: 'var(--sa-radius-md)'
            }}
            onClick={() => setCurrentView('appointments')}
          >
            {!sidebarCollapsed && 'Appointments'}
          </Button>
          <Button
            type="text"
            icon={<UnorderedListOutlined />}
            block
            style={{ 
              textAlign: 'left',
              marginBottom: '8px',
              height: '40px',
              color: currentView === 'worklist' ? 'var(--sa-blue)' : 'var(--sa-gray-700)',
              background: currentView === 'worklist' ? 'rgba(0, 38, 84, 0.1)' : 'transparent',
              fontWeight: currentView === 'worklist' ? 600 : 400,
              borderRadius: 'var(--sa-radius-md)'
            }}
            onClick={() => setCurrentView('worklist')}
          >
            {!sidebarCollapsed && 'Worklist'}
          </Button>
          <Button
            type="text"
            icon={<FileImageOutlined />}
            block
            style={{ 
              textAlign: 'left',
              marginBottom: '8px',
              height: '40px',
              color: currentView === 'studies' ? 'var(--sa-blue)' : 'var(--sa-gray-700)',
              background: currentView === 'studies' ? 'rgba(0, 38, 84, 0.1)' : 'transparent',
              fontWeight: currentView === 'studies' ? 600 : 400,
              borderRadius: 'var(--sa-radius-md)'
            }}
            onClick={() => setCurrentView('studies')}
          >
            {!sidebarCollapsed && 'Studies'}
          </Button>
          <Button
            type="text"
            icon={<FileTextOutlined />}
            block
            style={{ 
              textAlign: 'left',
              marginBottom: '8px',
              height: '40px',
              color: currentView === 'reports' ? 'var(--sa-blue)' : 'var(--sa-gray-700)',
              background: currentView === 'reports' ? 'rgba(0, 38, 84, 0.1)' : 'transparent',
              fontWeight: currentView === 'reports' ? 600 : 400,
              borderRadius: 'var(--sa-radius-md)'
            }}
            onClick={() => setCurrentView('reports')}
          >
            {!sidebarCollapsed && 'Reports'}
          </Button>
          <Button
            type="text"
            icon={<DollarOutlined />}
            block
            style={{ 
              textAlign: 'left',
              marginBottom: '8px',
              height: '40px',
              color: currentView === 'billing' ? 'var(--sa-blue)' : 'var(--sa-gray-700)',
              background: currentView === 'billing' ? 'rgba(0, 38, 84, 0.1)' : 'transparent',
              fontWeight: currentView === 'billing' ? 600 : 400,
              borderRadius: 'var(--sa-radius-md)'
            }}
            onClick={() => setCurrentView('billing')}
          >
            {!sidebarCollapsed && 'Billing'}
          </Button>
        </div>
      </Sider>
      <Layout style={{ background: 'var(--sa-gray-50)' }}>
        <Header
          style={{
            background: 'var(--sa-white)',
            padding: '0 24px',
            borderBottom: '1px solid var(--sa-gray-200)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
            height: '64px',
            lineHeight: '64px'
          }}
        >
          <Space>
            <Title level={4} className="sa-text-primary" style={{ margin: 0 }}>
              {currentView === 'dashboard' && 'Radiology Dashboard'}
              {currentView === 'authorization' && 'Medical Authorization'}
              {currentView === 'patients' && 'Patient Management'}
              {currentView === 'appointments' && 'Appointment Scheduling'}
              {currentView === 'worklist' && 'Radiology Worklist'}
              {currentView === 'studies' && 'Study Management'}
              {currentView === 'reports' && 'Reporting System'}
              {currentView === 'billing' && 'Billing & Invoices'}
            </Title>
          </Space>
          <Space size="middle">
            <Select
              value={selectedTimeRange}
              onChange={setSelectedTimeRange}
              style={{ width: 120 }}
              variant="borderless"
            >
              <Option value="today">Today</Option>
              <Option value="week">This Week</Option>
              <Option value="month">This Month</Option>
            </Select>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={loadDashboardData}
              loading={loading}
              style={{ 
                background: 'var(--sa-blue)', 
                borderColor: 'var(--sa-blue)',
                borderRadius: 'var(--sa-radius-md)'
              }}
            >
              Refresh
            </Button>
            <LanguageSwitcher />
            <Button
              type="text"
              icon={<BellOutlined />}
              onClick={() => setNotificationDrawerVisible(true)}
              style={{ 
                fontSize: '18px',
                color: 'var(--sa-gray-700)'
              }}
            />
            <Button
              type="text"
              icon={<SettingOutlined />}
              onClick={() => setSettingsDrawerVisible(true)}
              style={{ 
                fontSize: '18px',
                color: 'var(--sa-gray-700)'
              }}
            />
            <Avatar
              style={{ 
                background: 'linear-gradient(135deg, var(--sa-blue), var(--sa-red))',
                cursor: 'pointer'
              }}
            >
              <UserOutlined />
            </Avatar>
          </Space>
        </Header>
        <Content style={{ overflow: 'auto', background: 'var(--sa-gray-50)' }}>
          {currentView === 'dashboard' && renderDashboard()}
          {currentView === 'authorization' && (
            <div style={{ padding: '24px' }}>
              <MedicalAuthorizationPanel />
            </div>
          )}
          {currentView === 'patients' && <PatientManagement />}
          {currentView === 'appointments' && <AppointmentScheduling />}
          {currentView === 'worklist' && <WorklistManagement />}
          {currentView === 'studies' && <StudyManagement />}
          {currentView === 'reports' && <ReportingSystem />}
          {currentView === 'billing' && <BillingSystem />}
        </Content>
        <Footer
          style={{
            textAlign: 'center',
            background: 'var(--sa-white)',
            borderTop: '1px solid var(--sa-gray-200)',
            color: 'var(--sa-gray-600)',
            padding: '16px 24px',
            fontSize: '14px'
          }}
        >
          © 2025 South African Radiology Information System - Powered by Modern Healthcare Technology
        </Footer>
      </Layout>

      <Drawer
        title={
          <Space>
            <BellOutlined style={{ color: 'var(--sa-blue)' }} />
            <span className="sa-text-primary">Notifications</span>
          </Space>
        }
        placement="right"
        onClose={() => setNotificationDrawerVisible(false)}
        open={notificationDrawerVisible}
        width={400}
      >
        {dashboardData.notifications.length > 0 ? (
          <List
            dataSource={dashboardData.notifications}
            renderItem={(item) => (
              <List.Item style={{ 
                padding: '16px',
                borderRadius: 'var(--sa-radius-md)',
                marginBottom: '8px',
                background: 'var(--sa-gray-50)',
                border: '1px solid var(--sa-gray-200)'
              }}>
                <List.Item.Meta
                  title={<span className="sa-text-primary" style={{ fontWeight: 600 }}>{item.title}</span>}
                  description={
                    <div>
                      <Text style={{ color: 'var(--sa-gray-700)' }}>{item.message}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {moment(item.timestamp).fromNow()}
                      </Text>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: '48px', color: 'var(--sa-gray-500)' }}>
            <BellOutlined style={{ fontSize: '48px', color: 'var(--sa-gray-300)', marginBottom: '12px' }} />
            <p>No notifications</p>
          </div>
        )}
      </Drawer>

      <Drawer
        title={
          <Space>
            <SettingOutlined style={{ color: 'var(--sa-blue)' }} />
            <span className="sa-text-primary">Accessibility Settings</span>
          </Space>
        }
        placement="right"
        onClose={() => setSettingsDrawerVisible(false)}
        open={settingsDrawerVisible}
        width={400}
      >
        <AccessibilitySettings />
      </Drawer>

      {/* Patient Registration Modal */}
      <Modal
        title={
          <Space>
            <UserAddOutlined style={{ color: 'var(--sa-blue)' }} />
            <span>Patient Registration</span>
          </Space>
        }
        open={patientRegistrationVisible}
        onCancel={() => setPatientRegistrationVisible(false)}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handlePatientRegistration}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="firstName" label="First Name" rules={[{ required: true }]}>
                <Input placeholder="Enter first name" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="lastName" label="Last Name" rules={[{ required: true }]}>
                <Input placeholder="Enter last name" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="idNumber" label="ID Number" rules={[{ required: true }]}>
                <Input placeholder="Enter SA ID number" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="dateOfBirth" label="Date of Birth" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="gender" label="Gender" rules={[{ required: true }]}>
                <Radio.Group>
                  <Radio value="Male">Male</Radio>
                  <Radio value="Female">Female</Radio>
                  <Radio value="Other">Other</Radio>
                </Radio.Group>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="phone" label="Phone Number" rules={[{ required: true }]}>
                <Input placeholder="+27 XX XXX XXXX" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="email" label="Email">
            <Input placeholder="patient@email.com" />
          </Form.Item>
          <Form.Item name="address" label="Address">
            <Input.TextArea rows={2} placeholder="Enter full address" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="medicalAid" label="Medical Aid">
                <Select placeholder="Select medical aid">
                  <Select.Option value="Discovery Health">Discovery Health</Select.Option>
                  <Select.Option value="Momentum Health">Momentum Health</Select.Option>
                  <Select.Option value="Bonitas">Bonitas</Select.Option>
                  <Select.Option value="Medshield">Medshield</Select.Option>
                  <Select.Option value="None">None</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="medicalAidNumber" label="Medical Aid Number">
                <Input placeholder="Enter member number" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" style={{ background: 'var(--sa-blue)' }}>
                Register Patient
              </Button>
              <Button onClick={() => setPatientRegistrationVisible(false)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Advanced Search Modal */}
      <Modal
        title={
          <Space>
            <SearchOutlined style={{ color: 'var(--sa-blue)' }} />
            <span>Advanced Patient Search</span>
          </Space>
        }
        open={advancedSearchVisible}
        onCancel={() => setAdvancedSearchVisible(false)}
        footer={null}
        width={600}
      >
        <Form layout="vertical" onFinish={handleAdvancedSearch}>
          <Form.Item name="firstName" label="First Name">
            <Input placeholder="Search by first name" />
          </Form.Item>
          <Form.Item name="lastName" label="Last Name">
            <Input placeholder="Search by last name" />
          </Form.Item>
          <Form.Item name="idNumber" label="ID Number">
            <Input placeholder="Search by SA ID number" />
          </Form.Item>
          <Form.Item name="medicalAidNumber" label="Medical Aid Number">
            <Input placeholder="Search by medical aid number" />
          </Form.Item>
          <Form.Item name="phone" label="Phone Number">
            <Input placeholder="Search by phone number" />
          </Form.Item>
          <Form.Item name="dateOfBirth" label="Date of Birth">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<SearchOutlined />} style={{ background: 'var(--sa-blue)' }}>
                Search Patients
              </Button>
              <Button onClick={() => setAdvancedSearchVisible(false)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Benefits Check Modal */}
      <Modal
        title={
          <Space>
            <CreditCardOutlined style={{ color: 'var(--sa-green)' }} />
            <span>Medical Aid Benefits Check</span>
          </Space>
        }
        open={benefitsCheckVisible}
        onCancel={() => setBenefitsCheckVisible(false)}
        footer={null}
        width={500}
      >
        <Form layout="vertical" onFinish={handleBenefitsCheck}>
          <Form.Item name="memberNumber" label="Member Number" rules={[{ required: true }]}>
            <Input placeholder="Enter medical aid member number" />
          </Form.Item>
          <Form.Item name="schemeCode" label="Medical Scheme" rules={[{ required: true }]}>
            <Select placeholder="Select medical scheme">
              <Select.Option value="DISCOVERY">Discovery Health</Select.Option>
              <Select.Option value="MOMENTUM">Momentum Health</Select.Option>
              <Select.Option value="BONITAS">Bonitas</Select.Option>
              <Select.Option value="MEDSHIELD">Medshield</Select.Option>
              <Select.Option value="BESTMED">Bestmed</Select.Option>
              <Select.Option value="FEDHEALTH">Fedhealth</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="idNumber" label="ID Number">
            <Input placeholder="Enter patient ID number (optional)" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" style={{ background: 'var(--sa-green)' }}>
                Check Benefits
              </Button>
              <Button onClick={() => setBenefitsCheckVisible(false)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Authorization Request Modal */}
      <Modal
        title={
          <Space>
            <SafetyCertificateOutlined style={{ color: '#800080' }} />
            <span>Pre-Authorization Request</span>
          </Space>
        }
        open={authRequestVisible}
        onCancel={() => setAuthRequestVisible(false)}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleAuthRequest}>
          <Form.Item name="patientId" label="Patient ID" rules={[{ required: true }]}>
            <Input placeholder="Enter patient ID" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="memberNumber" label="Member Number" rules={[{ required: true }]}>
                <Input placeholder="Medical aid member number" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="schemeCode" label="Medical Scheme" rules={[{ required: true }]}>
                <Select placeholder="Select scheme">
                  <Select.Option value="DISCOVERY">Discovery Health</Select.Option>
                  <Select.Option value="MOMENTUM">Momentum Health</Select.Option>
                  <Select.Option value="BONITAS">Bonitas</Select.Option>
                  <Select.Option value="MEDSHIELD">Medshield</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="procedureCode" label="Procedure Code (NRPL)" rules={[{ required: true }]}>
            <Input placeholder="Enter NRPL procedure code" />
          </Form.Item>
          <Form.Item name="clinicalIndication" label="Clinical Indication" rules={[{ required: true }]}>
            <Input.TextArea rows={3} placeholder="Describe the clinical reason for the procedure" />
          </Form.Item>
          <Form.Item name="icd10Codes" label="ICD-10 Diagnosis Codes">
            <Input placeholder="Enter ICD-10 codes (comma separated)" />
          </Form.Item>
          <Form.Item name="urgency" label="Urgency" rules={[{ required: true }]}>
            <Radio.Group>
              <Radio value="routine">Routine</Radio>
              <Radio value="urgent">Urgent</Radio>
              <Radio value="emergency">Emergency</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" style={{ background: '#800080', borderColor: '#800080' }}>
                Submit Authorization Request
              </Button>
              <Button onClick={() => setAuthRequestVisible(false)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
};

export default SARadiologyDashboard;