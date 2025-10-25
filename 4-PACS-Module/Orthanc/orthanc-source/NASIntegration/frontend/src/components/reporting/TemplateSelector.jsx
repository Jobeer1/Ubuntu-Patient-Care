import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Search, 
  Filter, 
  Globe, 
  CheckCircle, 
  AlertCircle,
  Stethoscope,
  Heart,
  Bone,
  Eye,
  Brain,
  Zap
} from 'lucide-react';

const TemplateSelector = ({ 
  modality, 
  bodyPart, 
  language = 'en', 
  onTemplateSelect, 
  onLanguageChange 
}) => {
  const [templates, setTemplates] = useState([]);
  const [filteredTemplates, setFilteredTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [languages, setLanguages] = useState([]);
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    loadSystemData();
  }, []);

  useEffect(() => {
    if (modality) {
      loadTemplates();
    }
  }, [modality, bodyPart, language]);

  useEffect(() => {
    filterTemplates();
  }, [templates, selectedCategory, searchTerm]);

  const loadSystemData = async () => {
    try {
      // Load supported languages
      const langResponse = await fetch('/api/reporting/sa-templates/system/languages', {
        credentials: 'include'
      });
      if (langResponse.ok) {
        const langData = await langResponse.json();
        setLanguages(langData.languages || []);
      }

      // Load template categories
      const catResponse = await fetch('/api/reporting/sa-templates/system/categories', {
        credentials: 'include'
      });
      if (catResponse.ok) {
        const catData = await catResponse.json();
        setCategories(catData.categories || []);
      }
    } catch (err) {
      console.error('Error loading system data:', err);
    }
  };

  const loadTemplates = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        modality,
        language,
        ...(bodyPart && { body_part: bodyPart })
      });

      const response = await fetch(`/api/reporting/sa-templates/templates?${params}`, {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`Failed to load templates: ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        setTemplates(data.templates || []);
      } else {
        throw new Error(data.error || 'Failed to load templates');
      }
    } catch (err) {
      console.error('Error loading templates:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filterTemplates = () => {
    let filtered = templates;

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(template => template.category === selectedCategory);
    }

    // Filter by search term
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(template => {
        const name = getTemplateName(template, language).toLowerCase();
        return name.includes(search) || 
               template.modality.toLowerCase().includes(search) ||
               template.body_part.toLowerCase().includes(search);
      });
    }

    setFilteredTemplates(filtered);
  };

  const getTemplateName = (template, lang) => {
    switch (lang) {
      case 'af': return template.name_af || template.name_en;
      case 'zu': return template.name_zu || template.name_en;
      default: return template.name_en;
    }
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'screening': return <Search className="h-5 w-5" />;
      case 'diagnostic': return <Stethoscope className="h-5 w-5" />;
      case 'follow_up': return <CheckCircle className="h-5 w-5" />;
      case 'emergency': return <Zap className="h-5 w-5" />;
      default: return <FileText className="h-5 w-5" />;
    }
  };

  const getCategoryColor = (category) => {
    switch (category) {
      case 'screening': return 'bg-blue-100 text-blue-800';
      case 'diagnostic': return 'bg-green-100 text-green-800';
      case 'follow_up': return 'bg-purple-100 text-purple-800';
      case 'emergency': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getComplianceIcon = (level) => {
    switch (level) {
      case 'hpcsa': return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'medical_aid': return <AlertCircle className="h-4 w-4 text-orange-600" />;
      default: return <FileText className="h-4 w-4 text-gray-600" />;
    }
  };

  const handleTemplateSelect = (template) => {
    if (onTemplateSelect) {
      onTemplateSelect(template);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading SA medical templates...</span>
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
              <h2 className="text-2xl font-bold text-gray-900">🇿🇦 SA Medical Templates</h2>
              <p className="text-gray-600">
                {modality} templates for {bodyPart || 'all body parts'}
              </p>
            </div>
          </div>

          {/* Language Selector */}
          <div className="flex items-center space-x-3">
            <Globe className="h-5 w-5 text-gray-500" />
            <select
              value={language}
              onChange={(e) => onLanguageChange && onLanguageChange(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
            >
              {languages.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.flag} {lang.native_name}
                </option>
              ))}
            </select>
          </div>
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

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Filter Templates</h3>
          <span className="text-sm text-gray-600">
            {filteredTemplates.length} of {templates.length} templates
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search templates..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Category Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Categories</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Template Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredTemplates.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Templates Found</h3>
            <p className="text-gray-600">
              {searchTerm || selectedCategory !== 'all' 
                ? 'Try adjusting your filters or search terms'
                : 'No templates available for this modality'
              }
            </p>
          </div>
        ) : (
          filteredTemplates.map((template) => (
            <TemplateCard
              key={template.template_id}
              template={template}
              language={language}
              onSelect={handleTemplateSelect}
              getCategoryIcon={getCategoryIcon}
              getCategoryColor={getCategoryColor}
              getComplianceIcon={getComplianceIcon}
              getTemplateName={getTemplateName}
            />
          ))
        )}
      </div>
    </div>
  );
};

const TemplateCard = ({ 
  template, 
  language, 
  onSelect, 
  getCategoryIcon, 
  getCategoryColor, 
  getComplianceIcon, 
  getTemplateName 
}) => {
  const [isHovered, setIsHovered] = useState(false);

  const handleSelect = () => {
    onSelect(template);
  };

  const getSectionCount = () => {
    return template.structure?.sections?.length || 0;
  };

  const getRequiredFieldsCount = () => {
    const sections = template.structure?.sections || [];
    return sections.filter(section => section.required).length;
  };

  return (
    <div
      className={`bg-white rounded-lg shadow-md hover:shadow-lg transition-all duration-200 cursor-pointer ${
        isHovered ? 'transform -translate-y-1' : ''
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleSelect}
    >
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {getTemplateName(template, language)}
            </h3>
            <div className="flex items-center space-x-2 mb-3">
              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(template.category)}`}>
                {getCategoryIcon(template.category)}
                <span className="ml-1 capitalize">{template.category}</span>
              </span>
              {template.sa_specific && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  🇿🇦 SA Specific
                </span>
              )}
            </div>
          </div>
          
          <div className="flex items-center">
            {getComplianceIcon(template.compliance_level)}
          </div>
        </div>

        <div className="text-sm text-gray-600">
          <div className="flex items-center justify-between">
            <span>{template.modality} • {template.body_part}</span>
            <span>v{template.version}</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Sections:</span>
            <span className="font-medium">{getSectionCount()}</span>
          </div>
          
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Required Fields:</span>
            <span className="font-medium">{getRequiredFieldsCount()}</span>
          </div>

          {template.common_conditions && template.common_conditions.length > 0 && (
            <div className="text-sm">
              <span className="text-gray-600">Common Conditions:</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {template.common_conditions.slice(0, 3).map((condition, index) => (
                  <span
                    key={index}
                    className="inline-block px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded"
                  >
                    {condition}
                  </span>
                ))}
                {template.common_conditions.length > 3 && (
                  <span className="inline-block px-2 py-1 bg-gray-50 text-gray-600 text-xs rounded">
                    +{template.common_conditions.length - 3} more
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-4 bg-gray-50 rounded-b-lg">
        <button
          onClick={handleSelect}
          className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <FileText className="h-4 w-4 mr-2" />
          Use Template
        </button>
      </div>
    </div>
  );
};

export default TemplateSelector;