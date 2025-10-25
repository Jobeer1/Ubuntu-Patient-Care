import React, { useState, useEffect } from 'react';
import { Shield, Users, Key, Share, Eye, Download, QrCode, Clock, AlertTriangle } from 'lucide-react';

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [shares, setShares] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUserModal, setShowUserModal] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // SA Healthcare specific data
  const saProvinces = [
    'Eastern Cape', 'Free State', 'Gauteng', 'KwaZulu-Natal', 'Limpopo',
    'Mpumalanga', 'Northern Cape', 'North West', 'Western Cape'
  ];

  const saHealthcareRoles = [
    'radiologist', 'general_practitioner', 'specialist_physician', 'surgeon',
    'nursing_sister', 'healthcare_admin', 'medical_technologist', 'facility_manager'
  ];

  const saFacilityTypes = [
    'public_hospital', 'private_hospital', 'community_health_centre', 'clinic',
    'specialist_practice', 'radiology_practice', 'pathology_lab', 'pharmacy'
  ];

  useEffect(() => {
    fetchUsers();
    fetchGroups();
    fetchShares();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/admin/users');
      const data = await response.json();
      setUsers(data);
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  const fetchGroups = async () => {
    try {
      const response = await fetch('/api/admin/groups');
      const data = await response.json();
      setGroups(data);
    } catch (error) {
      console.error('Error fetching groups:', error);
    }
  };

  const fetchShares = async () => {
    try {
      const response = await fetch('/api/admin/shares');
      const data = await response.json();
      setShares(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching shares:', error);
      setLoading(false);
    }
  };

  const UserManagementTab = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">User Management</h2>
        <button
          onClick={() => setShowUserModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <Users size={20} />
          Add User
        </button>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Facility</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Province</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">HPCSA</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users.map((user) => (
              <tr key={user.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <span className="text-blue-600 font-medium">{user.name.charAt(0)}</span>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">{user.name}</div>
                      <div className="text-sm text-gray-500">{user.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.role}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.facility_name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.province}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.hpcsa_number || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => setSelectedUser(user)}
                    className="text-blue-600 hover:text-blue-900 mr-4"
                  >
                    Edit
                  </button>
                  <button className="text-red-600 hover:text-red-900">
                    Deactivate
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const ShareManagementTab = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Secure Shares</h2>
        <button
          onClick={() => setShowShareModal(true)}
          className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center gap-2"
        >
          <Share size={20} />
          Create Share
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Share className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Active Shares</p>
              <p className="text-2xl font-semibold text-gray-900">{shares.filter(s => s.is_active).length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <Eye className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Views</p>
              <p className="text-2xl font-semibold text-gray-900">{shares.reduce((sum, s) => sum + s.access_count, 0)}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 rounded-lg">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Expiring Soon</p>
              <p className="text-2xl font-semibold text-gray-900">
                {shares.filter(s => {
                  const expiry = new Date(s.expires_at);
                  const now = new Date();
                  const daysDiff = (expiry - now) / (1000 * 60 * 60 * 24);
                  return daysDiff <= 7 && daysDiff > 0;
                }).length}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patient</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Recipient</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Content</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expires</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Access</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {shares.map((share) => (
              <tr key={share.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{share.patient_name}</div>
                  <div className="text-sm text-gray-500">{share.study_description}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{share.recipient_name}</div>
                  <div className="text-sm text-gray-500">{share.recipient_type}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{share.content_type}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{new Date(share.expires_at).toLocaleDateString()}</div>
                  <div className={`text-sm ${
                    new Date(share.expires_at) < new Date() ? 'text-red-600' : 'text-gray-500'
                  }`}>
                    {new Date(share.expires_at) < new Date() ? 'Expired' : 'Active'}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {share.access_count} / {share.max_access_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button className="text-blue-600 hover:text-blue-900 mr-4">
                    <QrCode size={16} />
                  </button>
                  <button className="text-green-600 hover:text-green-900 mr-4">
                    <Download size={16} />
                  </button>
                  <button className="text-red-600 hover:text-red-900">
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const UserModal = () => (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            {selectedUser ? 'Edit User' : 'Add New User'}
          </h3>
          <form className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <input
                type="text"
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                placeholder="Dr. Jane Smith"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                placeholder="jane.smith@hospital.co.za"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Role</label>
              <select className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
                {saHealthcareRoles.map(role => (
                  <option key={role} value={role}>{role.replace('_', ' ').toUpperCase()}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Province</label>
              <select className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
                {saProvinces.map(province => (
                  <option key={province} value={province}>{province}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Facility Type</label>
              <select className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
                {saFacilityTypes.map(type => (
                  <option key={type} value={type}>{type.replace('_', ' ').toUpperCase()}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">HPCSA Practice Number</label>
              <input
                type="text"
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                placeholder="PR0123456"
              />
            </div>
            
            <div className="flex justify-end gap-2 mt-6">
              <button
                type="button"
                onClick={() => {
                  setShowUserModal(false);
                  setSelectedUser(null);
                }}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                {selectedUser ? 'Update' : 'Create'} User
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );

  const ShareModal = () => (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Create Secure Share</h3>
          <form className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Patient Name</label>
              <input
                type="text"
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                placeholder="John Doe"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Recipient Name</label>
              <input
                type="text"
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                placeholder="Dr. Sarah Wilson"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Recipient Email</label>
              <input
                type="email"
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                placeholder="sarah.wilson@specialist.co.za"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Content Type</label>
              <select className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
                <option value="single_image">Single Image</option>
                <option value="study">Complete Study</option>
                <option value="report">Report Only</option>
                <option value="report_with_images">Report with Images</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Access Level</label>
              <select className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
                <option value="view_only">View Only</option>
                <option value="view_download">View & Download</option>
                <option value="view_annotate">View & Annotate</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Expires In</label>
              <select className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
                <option value="1">1 Day</option>
                <option value="7">1 Week</option>
                <option value="30">1 Month</option>
                <option value="90">3 Months</option>
              </select>
            </div>
            
            <div className="flex items-center">
              <input
                type="checkbox"
                className="h-4 w-4 text-blue-600 border-gray-300 rounded"
              />
              <label className="ml-2 block text-sm text-gray-700">
                Require OTP verification
              </label>
            </div>
            
            <div className="flex justify-end gap-2 mt-6">
              <button
                type="button"
                onClick={() => setShowShareModal(false)}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                Create Share
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-blue-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-900">SA Healthcare Admin</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">South African Healthcare System</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('users')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'users'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Users className="inline-block w-5 h-5 mr-2" />
              Users & Groups
            </button>
            <button
              onClick={() => setActiveTab('shares')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'shares'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Share className="inline-block w-5 h-5 mr-2" />
              Secure Shares
            </button>
            <button
              onClick={() => setActiveTab('permissions')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'permissions'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Key className="inline-block w-5 h-5 mr-2" />
              Permissions
            </button>
          </nav>
        </div>

        {activeTab === 'users' && <UserManagementTab />}
        {activeTab === 'shares' && <ShareManagementTab />}
        {activeTab === 'permissions' && (
          <div className="text-center py-12">
            <h3 className="text-lg font-medium text-gray-900">Permissions Management</h3>
            <p className="text-gray-500">Advanced permission configuration coming soon...</p>
          </div>
        )}
      </div>

      {showUserModal && <UserModal />}
      {showShareModal && <ShareModal />}
    </div>
  );
};

export default AdminDashboard;
