import React, { useState } from 'react';
import { Calendar, Badge, Modal, Form, Input, Select, DatePicker, TimePicker, Button, Space, message, Card, Row, Col, List, Tag, Switch, Checkbox } from 'antd';
import { CalendarOutlined, ClockCircleOutlined, UserOutlined, MedicineBoxOutlined, PlusOutlined, NotificationOutlined, BellOutlined } from '@ant-design/icons';
import moment from 'moment';

const { Option } = Select;
const { TextArea } = Input;

const AppointmentScheduling = () => {
  const [selectedDate, setSelectedDate] = useState(moment());
  const [modalVisible, setModalVisible] = useState(false);
  const [notificationSettingsVisible, setNotificationSettingsVisible] = useState(false);
  const [form] = Form.useForm();
  const [notificationForm] = Form.useForm();
  const [notificationSettings, setNotificationSettings] = useState({
    smsEnabled: true,
    emailEnabled: true,
    whatsappEnabled: false,
    reminderTimes: ['24h', '2h'],
    autoConfirm: false
  });
  const [appointments, setAppointments] = useState([
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
    },
    {
      id: 2,
      patientName: 'Nomsa Dlamini',
      patientId: 'P002',
      date: '2025-10-17',
      time: '10:30',
      modality: 'MRI',
      bodyPart: 'Spine',
      status: 'Confirmed',
      notes: ''
    },
    {
      id: 3,
      patientName: 'Sipho Nkosi',
      patientId: 'P003',
      date: '2025-10-17',
      time: '14:00',
      modality: 'X-Ray',
      bodyPart: 'Chest',
      status: 'Scheduled',
      notes: ''
    }
  ]);

  const getListData = (value) => {
    const dateStr = value.format('YYYY-MM-DD');
    return appointments.filter(apt => apt.date === dateStr);
  };

  const dateCellRender = (value) => {
    const listData = getListData(value);
    return (
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {listData.map(item => (
          <li key={item.id}>
            <Badge
              status={item.status === 'Confirmed' ? 'success' : 'processing'}
              text={`${item.time} - ${item.patientName}`}
              style={{ fontSize: '11px' }}
            />
          </li>
        ))}
      </ul>
    );
  };

  const handleDateSelect = (date) => {
    setSelectedDate(date);
  };

  const handleAddAppointment = () => {
    form.resetFields();
    form.setFieldsValue({
      date: selectedDate,
      time: moment('09:00', 'HH:mm')
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values) => {
    try {
      const newAppointment = {
        id: appointments.length + 1,
        patientName: values.patientName,
        patientId: values.patientId,
        date: values.date.format('YYYY-MM-DD'),
        time: values.time.format('HH:mm'),
        modality: values.modality,
        bodyPart: values.bodyPart,
        status: 'Scheduled',
        notes: values.notes || '',
        notifications: notificationSettings
      };
      
      setAppointments([...appointments, newAppointment]);
      
      // Send notifications based on settings
      if (notificationSettings.smsEnabled) {
        message.info('SMS notification will be sent to patient');
      }
      if (notificationSettings.emailEnabled) {
        message.info('Email notification will be sent to patient');
      }
      
      message.success('Appointment scheduled successfully with notifications enabled');
      setModalVisible(false);
    } catch (error) {
      message.error('Failed to schedule appointment');
    }
  };

  const todayAppointments = appointments.filter(apt => apt.date === moment().format('YYYY-MM-DD'));
  const selectedDateAppointments = appointments.filter(apt => apt.date === selectedDate.format('YYYY-MM-DD'));

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={24}>
        <Col span={16}>
          <Card
            title={
              <Space>
                <CalendarOutlined />
                <span>Appointment Calendar</span>
              </Space>
            }
            extra={
              <Space>
                <Button
                  icon={<BellOutlined />}
                  onClick={() => setNotificationSettingsVisible(true)}
                >
                  Notification Settings
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleAddAppointment}
                  style={{ background: 'var(--sa-blue)' }}
                >
                  New Appointment
                </Button>
              </Space>
            }
          >
            <Calendar
              dateCellRender={dateCellRender}
              onSelect={handleDateSelect}
            />
          </Card>
        </Col>

        <Col span={8}>
          <Card
            title={
              <Space>
                <ClockCircleOutlined />
                <span>Today's Schedule</span>
              </Space>
            }
            style={{ marginBottom: '24px' }}
          >
            <List
              dataSource={todayAppointments}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <Space>
                        <Tag color="blue">{item.time}</Tag>
                        <span>{item.patientName}</span>
                      </Space>
                    }
                    description={`${item.modality} - ${item.bodyPart}`}
                  />
                  <Tag color={item.status === 'Confirmed' ? 'green' : 'orange'}>
                    {item.status}
                  </Tag>
                </List.Item>
              )}
            />
          </Card>

          <Card
            title={
              <Space>
                <CalendarOutlined />
                <span>{selectedDate.format('MMMM D, YYYY')}</span>
              </Space>
            }
          >
            {selectedDateAppointments.length > 0 ? (
              <List
                dataSource={selectedDateAppointments}
                renderItem={item => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <Space>
                          <Tag color="blue">{item.time}</Tag>
                          <span>{item.patientName}</span>
                        </Space>
                      }
                      description={`${item.modality} - ${item.bodyPart}`}
                    />
                  </List.Item>
                )}
              />
            ) : (
              <p style={{ textAlign: 'center', color: '#999' }}>No appointments</p>
            )}
          </Card>
        </Col>
      </Row>

      <Modal
        title="Schedule New Appointment"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="patientId"
            label="Patient"
            rules={[{ required: true, message: 'Please select patient' }]}
          >
            <Select
              showSearch
              placeholder="Search patient by name or ID"
              optionFilterProp="children"
            >
              <Option value="P001">P001 - Thabo Mokoena</Option>
              <Option value="P002">P002 - Nomsa Dlamini</Option>
              <Option value="P003">P003 - Sipho Nkosi</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="date"
                label="Date"
                rules={[{ required: true, message: 'Please select date' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="time"
                label="Time"
                rules={[{ required: true, message: 'Please select time' }]}
              >
                <TimePicker format="HH:mm" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="modality"
                label="Modality"
                rules={[{ required: true, message: 'Please select modality' }]}
              >
                <Select>
                  <Option value="CT Scan">CT Scan</Option>
                  <Option value="MRI">MRI</Option>
                  <Option value="X-Ray">X-Ray</Option>
                  <Option value="Ultrasound">Ultrasound</Option>
                  <Option value="Mammography">Mammography</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="bodyPart"
                label="Body Part"
                rules={[{ required: true, message: 'Please enter body part' }]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="notes"
            label="Notes"
          >
            <TextArea rows={3} />
          </Form.Item>

          <Form.Item>
            <Space style={{ float: 'right' }}>
              <Button onClick={() => setModalVisible(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit" style={{ background: 'var(--sa-blue)' }}>
                Schedule
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Notification Settings Modal */}
      <Modal
        title={
          <Space>
            <NotificationOutlined style={{ color: 'var(--sa-blue)' }} />
            <span>Automatic Notification Settings</span>
          </Space>
        }
        open={notificationSettingsVisible}
        onCancel={() => setNotificationSettingsVisible(false)}
        onOk={() => {
          message.success('Notification settings saved');
          setNotificationSettingsVisible(false);
        }}
        width={600}
      >
        <Form
          form={notificationForm}
          layout="vertical"
          initialValues={notificationSettings}
          onValuesChange={(_, allValues) => setNotificationSettings(allValues)}
        >
          <Card title="Notification Channels" style={{ marginBottom: 16 }}>
            <Form.Item name="smsEnabled" valuePropName="checked">
              <Checkbox>
                <Space>
                  <span>SMS Notifications</span>
                  <Tag color="blue">Recommended</Tag>
                </Space>
              </Checkbox>
            </Form.Item>
            <Form.Item name="emailEnabled" valuePropName="checked">
              <Checkbox>Email Notifications</Checkbox>
            </Form.Item>
            <Form.Item name="whatsappEnabled" valuePropName="checked">
              <Checkbox>
                <Space>
                  <span>WhatsApp Notifications</span>
                  <Tag color="green">New</Tag>
                </Space>
              </Checkbox>
            </Form.Item>
          </Card>

          <Card title="Reminder Schedule" style={{ marginBottom: 16 }}>
            <Form.Item name="reminderTimes" label="Send reminders before appointment">
              <Checkbox.Group>
                <Space direction="vertical">
                  <Checkbox value="7d">7 days before</Checkbox>
                  <Checkbox value="3d">3 days before</Checkbox>
                  <Checkbox value="24h">24 hours before</Checkbox>
                  <Checkbox value="2h">2 hours before</Checkbox>
                  <Checkbox value="30m">30 minutes before</Checkbox>
                </Space>
              </Checkbox.Group>
            </Form.Item>
          </Card>

          <Card title="Automation Settings">
            <Form.Item name="autoConfirm" valuePropName="checked">
              <Checkbox>
                Automatically send confirmation after booking
              </Checkbox>
            </Form.Item>
            <Form.Item name="autoReminder" valuePropName="checked">
              <Checkbox>
                Send automatic reminders based on schedule
              </Checkbox>
            </Form.Item>
            <Form.Item name="autoReschedule" valuePropName="checked">
              <Checkbox>
                Allow patients to reschedule via notification link
              </Checkbox>
            </Form.Item>
          </Card>

          <div style={{ 
            background: '#e6f7ff', 
            border: '1px solid #91d5ff', 
            borderRadius: '4px', 
            padding: '12px',
            marginTop: '16px'
          }}>
            <Space>
              <BellOutlined style={{ color: '#1890ff' }} />
              <div>
                <strong>Current Settings:</strong>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  {notificationSettings.smsEnabled && 'SMS '}
                  {notificationSettings.emailEnabled && 'Email '}
                  {notificationSettings.whatsappEnabled && 'WhatsApp '}
                  notifications enabled
                  {notificationSettings.reminderTimes && notificationSettings.reminderTimes.length > 0 && 
                    ` • ${notificationSettings.reminderTimes.length} reminder(s) scheduled`
                  }
                </div>
              </div>
            </Space>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default AppointmentScheduling;
