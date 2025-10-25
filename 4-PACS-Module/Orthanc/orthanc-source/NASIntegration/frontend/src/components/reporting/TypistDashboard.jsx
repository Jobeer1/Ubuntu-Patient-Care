import React, { useState, useEffect } from 'react';
import { 
  Clock, 
  AlertCircle, 
  CheckCircle, 
  User, 
  FileText, 
  Mic,
  TrendingUp,
  Filter,
  RefreshCw,
  Play,
  Pause,
  Volume2
} from 'lucide-react';

const TypistDashboard = () => {
  const [queueItems, setQueueItems] = useState([]);
  const [personalStats, setPersonalStats] = useState(null);
  const [queueStats, setQueueStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchDashboardData();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [priorityFilter]);

  const fetchDashboardData = async () => {
    try {
      setRefreshing(true);
      
      // Fetch queue items
      const queueUrl = priorityFilter === 'all' 
        ? '/api/reporting/typist/queue'
        : `/api/reporting/typist/queue?priority=${priorityFilter}`;
      
      const queueResponse = await fetch(queueUrl, {
        credentials: 'include'
      });
      
      if (!queueResponse.ok) {
        throw new Error(`Queue fetch failed: ${queueResponse.status}`);
      }
      
      const queueData = await queueResponse.json();
      
      // Fetch statistics
      const statsResponse = await fetch('/api/reporting/typist/stats', {
        credentials: 'include'
      });
      
      if (!statsResponse.ok) {
        throw new Error(`Stats fetch failed: ${statsResponse.status}`);
      }
      
      const statsData = await statsResponse.json();
      
      setQueueItems(queueData.queue_items || []);
      setPersonalStats(statsData.personal_statistics);
      setQueueStats(statsData.queue_statistics);
      setError(null);
      
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleClaimReport = async (sessionId) => {
    try {
      const response = await fetch(`/api/reporting/typist/claim/${sessionId}`, {
        method: 'POST',
        credentials: 'include'
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to claim report');
      }
      
      // Refresh dashboard after claiming
      fetchDashboardData();
      
    } catch (err) {
      console.error('Error claiming report:', err);
      alert(`Error claiming report: ${err.message}`);
    }
  };

  const handleReleaseReport = async (sessionId) => {
    try {
      const response = await fetch(`/api/reporting/typist/release/${sessionId}`, {
        method: 'POST',
        credentials: 'include'
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to release report');
      }
      
      // Refresh dashboard after releasing
      fetchDashboardData();
      
    } catch (err) {
      console.error('Error releasing report:', err);
      alert(`Error releasing report: ${err.message}`);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'urgent': return 'text-red-600 bg-red-100';
      case 'routine': return 'text-blue-600 bg-blue-100';
      case 'low': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getPriorityIcon = (priority) => {
    switch (priority) {
      case 'urgent': return <AlertCircle className="h-4 w-4" />;
      case 'routine': return <Clock className="h-4 w-4" />;
      case 'low': return <CheckCircle className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  if (loading && !refreshing) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading typist dashboard...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center">
              <FileText className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <h1 className="text-2xl font-bold text-gray-900">Typist Dashboard</h1>
              <p className="text-gray-600">SA Medical Reporting - Correction Workflow</p>
            </div>
          </div>
          
          <button
            onClick={fetchDashboardData}
            disabled={refreshing}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 text-red-600 mr-2" />
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      {/* Statistics Cards */}
      {personalStats && queueStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <StatCard
            title="Completed Today"
            value={personalStats.reports_completed_today}
            icon={CheckCircle}
            color="green"
          />
          <StatCard
            title="This Week"
            value={personalStats.reports_completed_week}
            icon={TrendingUp}
            color="blue"
          />
          <StatCard
            title="Avg. Time"
            value={`${personalStats.average_completion_time}m`}
            icon={Clock}
            color="purple"
          />
          <StatCard
            title="Accuracy"
            value={`${personalStats.accuracy_rate}%`}
            icon={User}
            color="orange"
          />
        </div>
      )}

      {/* Queue Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-gray-900">Report Queue</h2>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <Filter className="h-4 w-4 text-gray-500 mr-2" />
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm"
              >
                <option value="all">All Priorities</option>
                <option value="urgent">Urgent Only</option>
                <option value="routine">Routine Only</option>
                <option value="low">Low Priority</option>
              </select>
            </div>
            
            {queueStats && (
              <div className="text-sm text-gray-600">
                {queueStats.pending_reports} pending • {queueStats.claimed_reports} claimed
              </div>
            )}
          </div>
        </div>

        {/* Queue Items */}
        <div className="space-y-3">
          {queueItems.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No reports in queue</p>
              <p className="text-sm">Check back later or adjust filters</p>
            </div>
          ) : (
            queueItems.map((item) => (
              <QueueItemCard
                key={item.session_id}
                item={item}
                onClaim={handleClaimReport}
                onRelease={handleReleaseReport}
                getPriorityColor={getPriorityColor}
                getPriorityIcon={getPriorityIcon}
                formatDuration={formatDuration}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ title, value, icon: Icon, color }) => {
  const colorClasses = {
    green: 'bg-green-100 text-green-600',
    blue: 'bg-blue-100 text-blue-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600'
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
};c
onst QueueItemCard = ({ 
  item, 
  onClaim, 
  onRelease, 
  getPriorityColor, 
  getPriorityIcon, 
  formatDuration 
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  
  const handleAction = async (action) => {
    setIsProcessing(true);
    try {
      if (action === 'claim') {
        await onClaim(item.session_id);
      } else if (action === 'release') {
        await onRelease(item.session_id);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const isClaimed = item.status === 'claimed';
  const isMyReport = item.claimed_by && item.claimed_by === 'current_user'; // TODO: Get from session

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {/* Priority Badge */}
          <div className={`flex items-center px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(item.priority)}`}>
            {getPriorityIcon(item.priority)}
            <span className="ml-1 capitalize">{item.priority}</span>
          </div>
          
          {/* Patient Info */}
          <div>
            <div className="font-medium text-gray-900">
              {item.patient_name || `Patient ${item.patient_id}`}
            </div>
            <div className="text-sm text-gray-600">
              {item.study_type} • Dr. {item.doctor_name || item.doctor_id}
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Audio Duration */}
          <div className="flex items-center text-sm text-gray-600">
            <Mic className="h-4 w-4 mr-1" />
            {formatDuration(item.audio_duration)}
          </div>
          
          {/* Estimated Work Time */}
          <div className="flex items-center text-sm text-gray-600">
            <Clock className="h-4 w-4 mr-1" />
            ~{item.estimated_work_time}m
          </div>
          
          {/* Status and Actions */}
          <div className="flex items-center space-x-2">
            {isClaimed ? (
              <div className="flex items-center space-x-2">
                <span className="text-xs text-orange-600 bg-orange-100 px-2 py-1 rounded">
                  Claimed by {item.claimed_by}
                </span>
                {isMyReport && (
                  <button
                    onClick={() => handleAction('release')}
                    disabled={isProcessing}
                    className="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50"
                  >
                    Release
                  </button>
                )}
              </div>
            ) : (
              <button
                onClick={() => handleAction('claim')}
                disabled={isProcessing}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
              >
                {isProcessing ? 'Claiming...' : 'Claim'}
              </button>
            )}
          </div>
        </div>
      </div>
      
      {/* Additional Info */}
      <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
        <div>
          Created: {new Date(item.created_date).toLocaleString()}
        </div>
        <div>
          Language: {item.language}
        </div>
      </div>
    </div>
  );
};

export default TypistDashboard;