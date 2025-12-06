import { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Input, Select, Form, message, Badge, Space, Typography, List, Divider, Statistic, Progress, Tag, Spin, Alert } from 'antd';
import { CheckCircleOutlined, ClockCircleOutlined, DollarOutlined, FileProtectOutlined, SearchOutlined, ReloadOutlined, PlusOutlined, EyeOutlined } from '@ant-design/icons';
import { useAccessibility } from './AccessibilityContext';
import axios from 'axios';
import moment from 'moment';
import '../styles/sa-eye-candy.css';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

// MCP Server connection
const MCP_API_BASE = 'http://localhost:3001/api/mcp';

const MedicalAuthorizationPanel = () => {
  const accessibility = useAccessibility();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [memberInfo, setMemberInfo] = useState(null);
  const [costEstimate, setCostEstimate] = useState(null);
  const [preAuthRequirements, setPreAuthRequirements] = useState(null);
  const [pendingPreAuths, setPendingPreAuths] = useState([]);

  // Medical schemes available in South Africa
  const medicalSchemes = [
    { code: 'DISCOVERY', name: 'Discovery Health' },
    { code: 'MOMENTUM', name: 'Momentum Health' },
    { code: 'BONITAS', name: 'Bonitas Medical Fund' },
    { code: 'GEMS', name: 'Government Employees Medical Scheme' },
    { code: 'MEDSHIELD', name: 'Medshield Medical Scheme' },
    { code: 'BESTMED', name: 'Bestmed Medical Scheme' }
  ];

  // Common NRPL procedure codes
  const procedureCodes = [
    { code: '3011', name: 'CT Head without contrast', category: 'CT' },
    { code: '3012', name: 'CT Head with contrast', category: 'CT' },
    { code: '3021', name: 'CT Chest', category: 'CT' },
    { code: '3031', name: 'CT Abdomen', category: 'CT' },
    { code: '3111', name: 'MRI Brain without contrast', category: 'MRI' },
    { code: '3112', name: 'MRI Brain with contrast', category: 'MRI' },
    { code: '3121', name: 'MRI Spine', category: 'MRI' },
    { code: '2001', name: 'X-Ray Chest PA', category: 'X-Ray' },
    { code: '2011', name: 'X-Ray Skull', category: 'X-Ray' },
    { code: '2021', name: 'X-Ray Abdomen', category: 'X-Ray' }
  ];

  // ICD-10 codes for common indications
  const icd10Codes = [
    { code: 'R51', description: 'Headache' },
    { code: 'R07.4', description: 'Chest pain' },
    { code: 'R10.4', description: 'Abdominal pain' },
    { code: 'M54.5', description: 'Low back pain' },
    { code: 'I63.9', description: 'Cerebral infarction' },
    { code: 'J18.9', description: 'Pneumonia' },
    { code: 'K80.2', description: 'Gallstones' }
  ];

  useEffect(() => {
    loadPendingPreAuths();
  }, []);

  // Call MCP tool via REST API
  const callMCPTool = async (toolName, arguments_) => {
    try {
      let response;
      
      // Map tool names to REST endpoints
      switch (toolName) {
        case 'validate_medical_aid':
          response = await axios.post(`${MCP_API_BASE}/validate-medical-aid`, arguments_);
          break;
        case 'validate_preauth_requirements':
          response = await axios.post(`${MCP_API_BASE}/validate-preauth-requirements`, arguments_);
          break;
        case 'estimate_patient_cost':
          response = await axios.post(`${MCP_API_BASE}/estimate-patient-cost`, arguments_);
          break;
        case 'create_preauth_request':
          response = await axios.post(`${MCP_API_BASE}/create-preauth-request`, arguments_);
          break;
        case 'list_pending_preauths':
          response = await axios.get(`${MCP_API_BASE}/list-pending-preauths`, { params: arguments_ });
          break;
        case 'check_preauth_status':
          response = await axios.get(`${MCP_API_BASE}/check-preauth-status/${arguments_.preauth_id}`);
          break;
        default:
          throw new Error(`Unknown MCP tool: ${toolName}`);
      }
      
      return response.data.data || response.data;
    } catch (error) {
      console.error(`MCP Tool Error (${toolName}):`, error);
      throw error;
    }
  };

  // Validate medical aid member
  const validateMedicalAid = async (memberNumber, schemeCode) => {
    setValidating(true);
    accessibility.announceToScreenReader('Validating medical aid member');

    try {
      const result = await callMCPTool('validate_medical_aid', {
        member_number: memberNumber,
        scheme_code: schemeCode
      });

      if (result.valid) {
        setMemberInfo(result.member);
        message.success(`✅ Valid member: ${result.member.full_name}`);
        accessibility.announceToScreenReader(`Valid member: ${result.member.full_name}`);
        
        // Auto-fill plan code
        form.setFieldsValue({ plan_code: result.member.plan_code });
      } else {
        setMemberInfo(null);
        message.error(`❌ ${result.error}`);
        accessibility.announceToScreenReader(`Error: ${result.error}`);
      }
    } catch (error) {
      message.error('Failed to validate medical aid');
    } finally {
      setValidating(false);
    }
  };

  // Check pre-auth requirements
  const checkPreAuthRequirements = async (schemeCode, planCode, procedureCode) => {
    setLoading(true);
    accessibility.announceToScreenReader('Checking pre-authorization requirements');

    try {
      const result = await callMCPTool('validate_preauth_requirements', {
        scheme_code: schemeCode,
        plan_code: planCode,
        procedure_code: procedureCode
      });

      setPreAuthRequirements(result);

      if (result.requires_preauth) {
        message.warning(`⚠️ Pre-authorization required (${result.typical_turnaround})`);
      } else {
        message.success('✅ No pre-authorization required');
      }

      accessibility.announceToScreenReader(
        result.requires_preauth 
          ? `Pre-authorization required. Typical turnaround: ${result.typical_turnaround}`
          : 'No pre-authorization required'
      );
    } catch (error) {
      message.error('Failed to check pre-auth requirements');
    } finally {
      setLoading(false);
    }
  };

  // Estimate patient cost
  const estimatePatientCost = async (memberNumber, schemeCode, procedureCode) => {
    setLoading(true);
    accessibility.announceToScreenReader('Calculating patient cost');

    try {
      const result = await callMCPTool('estimate_patient_cost', {
        member_number: memberNumber,
        scheme_code: schemeCode,
        procedure_code: procedureCode
      });

      setCostEstimate(result);
      message.success(`💰 Patient portion: R${result.patient_portion.toFixed(2)}`);
      accessibility.announceToScreenReader(`Patient portion: ${result.patient_portion} Rand`);
    } catch (error) {
      message.error('Failed to estimate cost');
    } finally {
      setLoading(false);
    }
  };

  // Create pre-auth request
  const createPreAuthRequest = async (values) => {
    setLoading(true);
    accessibility.announceToScreenReader('Creating pre-authorization request');

    try {
      const result = await callMCPTool('create_preauth_request', {
        patient_id: values.patient_id,
        member_number: values.member_number,
        scheme_code: values.scheme_code,
        procedure_code: values.procedure_code,
        clinical_indication: values.clinical_indication,
        icd10_codes: values.icd10_codes || [],
        urgency: values.urgency || 'routine'
      });

      if (result.success) {
        message.success(`✅ Pre-auth created: ${result.preauth_id}`);
        accessibility.announceToScreenReader(`Pre-authorization request created successfully. ID: ${result.preauth_id}`);
        
        // Reset form and reload pending list
        form.resetFields();
        setMemberInfo(null);
        setCostEstimate(null);
        setPreAuthRequirements(null);
        loadPendingPreAuths();
      } else {
        message.error(`❌ ${result.error}`);
      }
    } catch (error) {
      message.error('Failed to create pre-auth request');
    } finally {
      setLoading(false);
    }
  };

  // Load pending pre-auths
  const loadPendingPreAuths = async () => {
    try {
      const result = await callMCPTool('list_pending_preauths', {
        status: 'queued'
      });

      setPendingPreAuths(result.requests || []);
    } catch (error) {
      console.error('Failed to load pending pre-auths:', error);
    }
  };

  // Handle form value changes
  const handleFormChange = (changedValues, allValues) => {
    // Auto-validate when member number and scheme are entered
    if (changedValues.member_number || changedValues.scheme_code) {
      if (allValues.member_number && allValues.scheme_code) {
        validateMedicalAid(allValues.member_number, allValues.scheme_code);
      }
    }

    // Auto-check pre-auth requirements when procedure is selected
    if (changedValues.procedure_code) {
      if (allValues.scheme_code && allValues.plan_code && allValues.procedure_code) {
        checkPreAuthRequirements(allValues.scheme_code, allValues.plan_code, allValues.procedure_code);
        
        // Also estimate cost if member number is available
        if (allValues.member_number) {
          estimatePatientCost(allValues.member_number, allValues.scheme_code, allValues.procedure_code);
        }
      }
    }
  };

  return (
    <div className="sa-pattern-dots" style={{ padding: '24px' }}>
      {/* Header */}
      <div className="sa-card sa-gradient-primary sa-float" style={{
        padding: '20px',
        marginBottom: '24px',
        color: 'white'
      }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={2} style={{ color: 'white', margin: 0 }}>
              <FileProtectOutlined style={{ marginRight: '12px' }} />
              Medical Scheme Authorization
            </Title>
            <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
              Fast, Accurate, Offline-Capable Pre-Authorization
            </Text>
          </Col>
          <Col>
            <Space>
              <Button
                type="text"
                icon={<ReloadOutlined />}
                onClick={loadPendingPreAuths}
                style={{ color: 'white' }}
                className="sa-btn-outline"
              >
                Refresh
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      <Row gutter={[24, 24]}>
        {/* Left Column - Form */}
        <Col xs={24} lg={14}>
          <Card
            title={
              <Space>
                <PlusOutlined className="sa-text-primary" />
                <span className="sa-text-primary">New Pre-Authorization Request</span>
              </Space>
            }
            className="sa-card sa-card-primary"
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={createPreAuthRequest}
              onValuesChange={handleFormChange}
            >
              {/* Patient Information */}
              <Divider orientation="left">
                <Text className="sa-text-primary">Patient Information</Text>
              </Divider>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="Patient ID"
                    name="patient_id"
                    rules={[{ required: true, message: 'Please enter patient ID' }]}
                  >
                    <Input
                      prefix={<SearchOutlined />}
                      placeholder="Enter patient ID"
                      className="sa-focus"
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="Medical Scheme"
                    name="scheme_code"
                    rules={[{ required: true, message: 'Please select medical scheme' }]}
                  >
                    <Select
                      placeholder="Select scheme"
                      className="sa-focus"
                      showSearch
                      filterOption={(input, option) =>
                        option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
                      }
                    >
                      {medicalSchemes.map(scheme => (
                        <Option key={scheme.code} value={scheme.code}>
                          {scheme.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="Member Number"
                    name="member_number"
                    rules={[{ required: true, message: 'Please enter member number' }]}
                  >
                    <Input
                      placeholder="Enter member number"
                      className="sa-focus"
                      suffix={validating ? <Spin size="small" /> : null}
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="Plan Code"
                    name="plan_code"
                    rules={[{ required: true, message: 'Please enter plan code' }]}
                  >
                    <Input
                      placeholder="Auto-filled after validation"
                      className="sa-focus"
                      disabled={!memberInfo}
                    />
                  </Form.Item>
                </Col>
              </Row>

              {/* Member Validation Status */}
              {memberInfo && (
                <Alert
                  message="✅ Valid Member"
                  description={
                    <div>
                      <Text strong>{memberInfo.full_name}</Text>
                      <br />
                      <Text type="secondary">{memberInfo.plan_name}</Text>
                      <br />
                      <Tag color="green">{memberInfo.status}</Tag>
                    </div>
                  }
                  type="success"
                  showIcon
                  style={{ marginBottom: '16px' }}
                  className="sa-card-success"
                />
              )}

              {/* Procedure Information */}
              <Divider orientation="left">
                <Text className="sa-text-primary">Procedure Information</Text>
              </Divider>

              <Form.Item
                label="Procedure"
                name="procedure_code"
                rules={[{ required: true, message: 'Please select procedure' }]}
              >
                <Select
                  placeholder="Select procedure"
                  className="sa-focus"
                  showSearch
                  filterOption={(input, option) =>
                    option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
                  }
                >
                  {procedureCodes.map(proc => (
                    <Option key={proc.code} value={proc.code}>
                      {proc.code} - {proc.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                label="Clinical Indication"
                name="clinical_indication"
                rules={[{ required: true, message: 'Please enter clinical indication' }]}
              >
                <TextArea
                  rows={3}
                  placeholder="Enter clinical indication for the procedure"
                  className="sa-focus"
                />
              </Form.Item>

              <Form.Item
                label="ICD-10 Diagnosis Codes"
                name="icd10_codes"
              >
                <Select
                  mode="multiple"
                  placeholder="Select ICD-10 codes"
                  className="sa-focus"
                  showSearch
                  filterOption={(input, option) =>
                    option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
                  }
                >
                  {icd10Codes.map(code => (
                    <Option key={code.code} value={code.code}>
                      {code.code} - {code.description}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                label="Urgency"
                name="urgency"
                initialValue="routine"
              >
                <Select className="sa-focus">
                  <Option value="routine">Routine</Option>
                  <Option value="urgent">Urgent</Option>
                  <Option value="emergency">Emergency</Option>
                </Select>
              </Form.Item>

              {/* Pre-Auth Requirements */}
              {preAuthRequirements && (
                <Alert
                  message={preAuthRequirements.requires_preauth ? "⚠️ Pre-Authorization Required" : "✅ No Pre-Authorization Required"}
                  description={
                    <div>
                      <Text>{preAuthRequirements.procedure_name}</Text>
                      <br />
                      {preAuthRequirements.requires_preauth && (
                        <>
                          <Text type="secondary">Typical turnaround: {preAuthRequirements.typical_turnaround}</Text>
                          <br />
                          <Text type="secondary">Approval rate: {(preAuthRequirements.approval_rate * 100).toFixed(0)}%</Text>
                        </>
                      )}
                    </div>
                  }
                  type={preAuthRequirements.requires_preauth ? "warning" : "success"}
                  showIcon
                  style={{ marginBottom: '16px' }}
                  className={preAuthRequirements.requires_preauth ? "sa-card-warning" : "sa-card-success"}
                />
              )}

              {/* Submit Button */}
              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  size="large"
                  className="sa-btn sa-btn-primary sa-focus"
                  style={{ background: 'var(--sa-blue)', borderColor: 'var(--sa-blue)' }}
                  icon={<CheckCircleOutlined />}
                >
                  Create Pre-Authorization Request
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        {/* Right Column - Info & Status */}
        <Col xs={24} lg={10}>
          {/* Cost Estimate */}
          {costEstimate && (
            <Card
              title={
                <Space>
                  <DollarOutlined className="sa-text-accent" />
                  <span className="sa-text-primary">Cost Estimate</span>
                </Space>
              }
              className="sa-card sa-card-warning sa-mb-md"
              style={{ marginBottom: '24px' }}
            >
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Statistic
                    title="Procedure Cost"
                    value={costEstimate.procedure_cost}
                    prefix="R"
                    precision={2}
                    valueStyle={{ color: 'var(--sa-blue)' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="Patient Portion"
                    value={costEstimate.patient_portion}
                    prefix="R"
                    precision={2}
                    valueStyle={{ color: 'var(--sa-red)' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="Medical Aid Portion"
                    value={costEstimate.medical_aid_portion}
                    prefix="R"
                    precision={2}
                    valueStyle={{ color: 'var(--sa-green)' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="Co-Payment"
                    value={costEstimate.co_payment_percentage}
                    suffix="%"
                    precision={0}
                    valueStyle={{ color: 'var(--sa-gold)' }}
                  />
                </Col>
              </Row>

              <Divider />

              <div>
                <Text type="secondary">Annual Limit: R{costEstimate.annual_limit.toFixed(2)}</Text>
                <br />
                <Text type="secondary">Used This Year: R{costEstimate.used_this_year.toFixed(2)}</Text>
                <br />
                <Text strong style={{ color: 'var(--sa-green)' }}>
                  Remaining: R{costEstimate.remaining_benefit.toFixed(2)}
                </Text>
              </div>

              <Progress
                percent={(costEstimate.used_this_year / costEstimate.annual_limit * 100).toFixed(0)}
                strokeColor={{
                  '0%': 'var(--sa-green)',
                  '100%': 'var(--sa-red)'
                }}
                style={{ marginTop: '16px' }}
              />

              {costEstimate.preauth_required && (
                <Tag color="orange" style={{ marginTop: '16px' }}>
                  Pre-Authorization Required
                </Tag>
              )}

              <Tag color="blue" style={{ marginTop: '16px' }}>
                Offline Calculation
              </Tag>
            </Card>
          )}

          {/* Pending Pre-Authorizations */}
          <Card
            title={
              <Space>
                <ClockCircleOutlined className="sa-text-accent" />
                <span className="sa-text-primary">Pending Pre-Authorizations</span>
                <Badge count={pendingPreAuths.length} className="sa-badge sa-badge-warning" />
              </Space>
            }
            className="sa-card sa-card-warning"
          >
            <List
              dataSource={pendingPreAuths}
              locale={{ emptyText: 'No pending pre-authorizations' }}
              renderItem={(item) => (
                <List.Item
                  className="sa-list-item"
                  actions={[
                    <Button
                      type="link"
                      size="small"
                      icon={<EyeOutlined />}
                      className="sa-text-primary"
                    >
                      View
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Badge status="processing" />
                        <span className="sa-text-primary">{item.preauth_id}</span>
                        <Tag color={item.urgency === 'emergency' ? 'red' : item.urgency === 'urgent' ? 'orange' : 'blue'}>
                          {item.urgency}
                        </Tag>
                      </Space>
                    }
                    description={
                      <div>
                        <Text className="sa-text-primary">Patient: {item.patient_id}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          Procedure: {item.procedure_code}
                        </Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          Created: {moment(item.created_at).fromNow()}
                        </Text>
                        <br />
                        {item.approval_probability && (
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            Approval probability: {(item.approval_probability * 100).toFixed(0)}%
                          </Text>
                        )}
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
};

export default MedicalAuthorizationPanel;
