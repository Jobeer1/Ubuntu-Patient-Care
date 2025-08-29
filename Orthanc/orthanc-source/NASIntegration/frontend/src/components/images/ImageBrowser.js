import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { Search, Filter, Grid, List, Upload, Eye } from 'lucide-react';
import api from '../../utils/api';
import LoadingSpinner from '../common/LoadingSpinner';

const ImageBrowser = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState('grid');
  const [filters, setFilters] = useState({
    modality: '',
    dateFrom: '',
    dateTo: '',
  });

  // Fetch images
  const { data: imagesData, isLoading, error } = useQuery(
    ['images', searchTerm, filters],
    async () => {
      const params = new URLSearchParams();
      if (searchTerm) params.append('patient_name', searchTerm);
      if (filters.modality) params.append('modality', filters.modality);
      if (filters.dateFrom) params.append('study_date_from', filters.dateFrom);
      if (filters.dateTo) params.append('study_date_to', filters.dateTo);
      
      const response = await api.get(`/images?${params.toString()}`);
      return response.data;
    }
  );

  const images = imagesData?.images || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Image Browser</h1>
            <p className="text-gray-600 mt-1">Browse and manage your DICOM images</p>
          </div>
          <button className="btn-primary">
            <Upload className="h-4 w-4 mr-2" />
            Upload Images
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
          {/* Search */}
          <div className="flex-1 max-w-lg">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by patient name..."
                className="input pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-md ${
                viewMode === 'grid' 
                  ? 'bg-primary-100 text-primary-600' 
                  : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              <Grid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-md ${
                viewMode === 'list' 
                  ? 'bg-primary-100 text-primary-600' 
                  : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              <List className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">Modality</label>
            <select
              className="input"
              value={filters.modality}
              onChange={(e) => setFilters({ ...filters, modality: e.target.value })}
            >
              <option value="">All Modalities</option>
              <option value="CT">CT</option>
              <option value="MRI">MRI</option>
              <option value="X-RAY">X-Ray</option>
              <option value="US">Ultrasound</option>
            </select>
          </div>
          <div>
            <label className="label">Date From</label>
            <input
              type="date"
              className="input"
              value={filters.dateFrom}
              onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Date To</label>
            <input
              type="date"
              className="input"
              value={filters.dateTo}
              onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
            />
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : error ? (
          <div className="p-6 text-center text-red-600">
            Failed to load images. Please try again.
          </div>
        ) : images.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            <Eye className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium">No images found</p>
            <p className="text-sm mt-1">Try adjusting your search criteria or upload some images.</p>
          </div>
        ) : (
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-600">
                Found {images.length} image{images.length !== 1 ? 's' : ''}
              </p>
            </div>

            {viewMode === 'grid' ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {images.map((image) => (
                  <ImageCard key={image.image_id} image={image} />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {images.map((image) => (
                  <ImageListItem key={image.image_id} image={image} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const ImageCard = ({ image }) => (
  <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
    <div className="flex items-center mb-3">
      <div className="h-10 w-10 bg-primary-100 rounded-lg flex items-center justify-center">
        <Eye className="h-5 w-5 text-primary-600" />
      </div>
      <div className="ml-3">
        <p className="text-sm font-medium text-gray-900">{image.patient_name}</p>
        <p className="text-xs text-gray-500">{image.patient_id}</p>
      </div>
    </div>
    <div className="space-y-2 text-sm">
      <div className="flex justify-between">
        <span className="text-gray-500">Study:</span>
        <span className="text-gray-900">{image.study_description || 'N/A'}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-500">Modality:</span>
        <span className="badge badge-secondary">{image.modality}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-500">Date:</span>
        <span className="text-gray-900">{image.study_date}</span>
      </div>
    </div>
    <div className="mt-4 flex space-x-2">
      <button className="btn-outline btn-sm flex-1">
        <Eye className="h-3 w-3 mr-1" />
        View
      </button>
      <button className="btn-outline btn-sm">
        Share
      </button>
    </div>
  </div>
);

const ImageListItem = ({ image }) => (
  <div className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
    <div className="h-10 w-10 bg-primary-100 rounded-lg flex items-center justify-center">
      <Eye className="h-5 w-5 text-primary-600" />
    </div>
    <div className="ml-4 flex-1">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-900">{image.patient_name}</p>
          <p className="text-xs text-gray-500">{image.study_description}</p>
        </div>
        <div className="flex items-center space-x-4 text-sm text-gray-500">
          <span className="badge badge-secondary">{image.modality}</span>
          <span>{image.study_date}</span>
          <div className="flex space-x-2">
            <button className="btn-outline btn-sm">View</button>
            <button className="btn-outline btn-sm">Share</button>
          </div>
        </div>
      </div>
    </div>
  </div>
);

export default ImageBrowser;