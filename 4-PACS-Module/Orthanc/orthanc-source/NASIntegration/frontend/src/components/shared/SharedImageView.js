import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import { Eye, Download, Clock, User } from 'lucide-react';
import api from '../../utils/api';
import LoadingSpinner from '../common/LoadingSpinner';

const SharedImageView = () => {
  const { token } = useParams();

  // Fetch shared image data
  const { data, isLoading, error } = useQuery(
    ['shared-image', token],
    async () => {
      const response = await api.get(`/shared/${token}`);
      return response.data;
    },
    {
      retry: false, // Don't retry on error for shared links
    }
  );

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full text-center">
          <div className="bg-white rounded-lg shadow p-8">
            <div className="h-16 w-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Eye className="h-8 w-8 text-red-600" />
            </div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">Link Not Found</h1>
            <p className="text-gray-600 mb-4">
              This shared link is invalid, expired, or has reached its view limit.
            </p>
            <p className="text-sm text-gray-500">
              Please contact the person who shared this link for assistance.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const { image, shared_link } = data;

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-gray-900">Shared Medical Image</h1>
                <p className="text-sm text-gray-600 mt-1">
                  Securely shared via Orthanc NAS
                </p>
              </div>
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <Eye className="h-4 w-4" />
                <span>Views: {shared_link.current_views}</span>
                {shared_link.max_views > 0 && (
                  <span>/ {shared_link.max_views}</span>
                )}
              </div>
            </div>
          </div>

          {/* Image Details */}
          <div className="px-6 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium text-gray-900 mb-3">Patient Information</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Patient Name:</span>
                    <span className="text-gray-900 font-medium">{image.patient_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Patient ID:</span>
                    <span className="text-gray-900">{image.patient_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Study Date:</span>
                    <span className="text-gray-900">{image.study_date}</span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-medium text-gray-900 mb-3">Study Information</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Modality:</span>
                    <span className="badge badge-secondary">{image.modality}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Study Description:</span>
                    <span className="text-gray-900">{image.study_description || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Institution:</span>
                    <span className="text-gray-900">{image.institution_name || 'N/A'}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Image Viewer Placeholder */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Image Viewer</h2>
          </div>
          <div className="p-6">
            <div className="bg-gray-100 rounded-lg h-96 flex items-center justify-center">
              <div className="text-center">
                <Eye className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 font-medium">DICOM Image Viewer</p>
                <p className="text-sm text-gray-500 mt-1">
                  Image viewer integration would be implemented here
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  File: {image.nas_path}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Share Information */}
        <div className="bg-white rounded-lg shadow mt-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Share Information</h3>
          </div>
          <div className="px-6 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
              <div className="space-y-2">
                <div className="flex items-center">
                  <User className="h-4 w-4 text-gray-400 mr-2" />
                  <span className="text-gray-500">Shared by:</span>
                  <span className="text-gray-900 ml-2">{shared_link.created_by}</span>
                </div>
                <div className="flex items-center">
                  <Clock className="h-4 w-4 text-gray-400 mr-2" />
                  <span className="text-gray-500">Shared on:</span>
                  <span className="text-gray-900 ml-2">
                    {new Date(shared_link.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center">
                  <Clock className="h-4 w-4 text-gray-400 mr-2" />
                  <span className="text-gray-500">Expires:</span>
                  <span className="text-gray-900 ml-2">
                    {new Date(shared_link.expires_at).toLocaleDateString()}
                  </span>
                </div>
                {shared_link.recipient_email && (
                  <div className="flex items-center">
                    <span className="text-gray-500">Recipient:</span>
                    <span className="text-gray-900 ml-2">{shared_link.recipient_email}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Security Notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-6">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <Eye className="h-5 w-5 text-blue-600" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">Security Notice</h3>
              <p className="text-sm text-blue-700 mt-1">
                This medical image has been securely shared with you. Please handle this 
                information in accordance with applicable privacy regulations (HIPAA, GDPR, etc.).
                Do not share this link with unauthorized individuals.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SharedImageView;