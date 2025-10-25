import React from 'react';
import { useQuery } from 'react-query';
import { Image, Upload, Search, Share2, Clock } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import LoadingSpinner from '../common/LoadingSpinner';
import StatsCard from '../dashboard/StatsCard';

const UserDashboard = () => {
  const { user } = useAuth();

  // Fetch user's images
  const { data: images, isLoading } = useQuery(
    ['user-images'],
    async () => {
      const response = await api.get('/images?limit=5');
      return response.data.images;
    }
  );

  return (
    <div className="space-y-6">
      {/* User Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">My Dashboard</h1>
            <p className="text-gray-600 mt-1">Manage your medical images and studies</p>
          </div>
          <div className="flex items-center space-x-2">
            <div className="h-12 w-12 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-lg font-semibold text-primary-700">
                {user?.username?.charAt(0).toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatsCard
          title="My Images"
          value={images?.length || 0}
          icon={Image}
          color="blue"
          subtitle="Total uploaded"
        />
        <StatsCard
          title="Recent Uploads"
          value="0"
          icon={Upload}
          color="green"
          subtitle="This week"
        />
        <StatsCard
          title="Shared Links"
          value="0"
          icon={Share2}
          color="purple"
          subtitle="Active shares"
        />
      </div>

      {/* Recent Images */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Recent Images</h2>
          <a href="/images" className="text-sm text-primary-600 hover:text-primary-700">
            View all →
          </a>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="lg" />
          </div>
        ) : images && images.length > 0 ? (
          <div className="space-y-3">
            {images.map((image) => (
              <div key={image.image_id} className="flex items-center p-3 bg-gray-50 rounded-lg">
                <div className="h-10 w-10 bg-primary-100 rounded-lg flex items-center justify-center">
                  <Image className="h-5 w-5 text-primary-600" />
                </div>
                <div className="ml-3 flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {image.patient_name || 'Unknown Patient'}
                  </p>
                  <p className="text-xs text-gray-500">
                    {image.modality} • {image.study_date} • {image.study_description}
                  </p>
                </div>
                <div className="flex items-center text-xs text-gray-400">
                  <Clock className="h-3 w-3 mr-1" />
                  {new Date(image.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Image className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p>No images uploaded yet</p>
            <p className="text-sm mt-1">Upload your first DICOM image to get started</p>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <ActionButton
            title="Upload Images"
            description="Upload new DICOM files"
            icon={Upload}
            href="/images/upload"
            color="bg-green-500 hover:bg-green-600"
          />
          <ActionButton
            title="Browse Images"
            description="View all your images"
            icon={Image}
            href="/images"
            color="bg-blue-500 hover:bg-blue-600"
          />
          <ActionButton
            title="Search Studies"
            description="Find specific studies"
            icon={Search}
            href="/images?tab=search"
            color="bg-purple-500 hover:bg-purple-600"
          />
        </div>
      </div>
    </div>
  );
};

const ActionButton = ({ title, description, icon: Icon, href, color }) => (
  <a
    href={href}
    className="block p-4 border border-gray-200 rounded-lg hover:shadow-md transition-all duration-200"
  >
    <div className="flex items-center space-x-3">
      <div className={`p-2 rounded-lg text-white ${color} transition-colors`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-sm font-medium text-gray-900">{title}</p>
        <p className="text-xs text-gray-500 mt-1">{description}</p>
      </div>
    </div>
  </a>
);

export default UserDashboard;