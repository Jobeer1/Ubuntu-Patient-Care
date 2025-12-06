#!/usr/bin/env python3
"""
🏥 Enterprise NAS Shared Folders API
Ubuntu Patient Care - RESTful API for managing multiple shared folders per NAS device

Provides endpoints for:
- Adding/configuring NAS devices with multiple shared folders
- Testing connections to specific procedure folders
- Managing credentials for different medical procedures
- Integration with existing Orthanc PACS infrastructure
"""

from flask import Blueprint, request, jsonify, render_template
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import our enterprise configuration manager
from .enterprise_nas_shared_folders_config import enterprise_nas_folders

logger = logging.getLogger(__name__)

# Create Flask blueprint
enterprise_nas_bp = Blueprint('enterprise_nas', __name__, url_prefix='/api/enterprise-nas')

# ============================================================================
# NAS DEVICE MANAGEMENT ENDPOINTS
# ============================================================================

@enterprise_nas_bp.route('/devices', methods=['GET'])
def get_nas_devices():
    """Get all NAS devices with their shared folders"""
    try:
        devices = enterprise_nas_folders.get_nas_devices()
        
        return jsonify({
            'success': True,
            'devices': devices,
            'total_devices': len(devices),
            'total_folders': sum(len(device['shared_folders']) for device in devices)
        })
        
    except Exception as e:
        logger.error(f"Error getting NAS devices: {e}")
        return jsonify({'error': f'Failed to get NAS devices: {str(e)}'}), 500

@enterprise_nas_bp.route('/devices', methods=['POST'])
def add_nas_device():
    """Add new NAS device"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['device_name', 'ip_address']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Add device
        device_id = enterprise_nas_folders.add_nas_device(
            device_name=data['device_name'],
            ip_address=data['ip_address'],
            manufacturer=data.get('manufacturer', 'Unknown'),
            model=data.get('model', 'Unknown'),
            default_domain=data.get('default_domain', ''),
            admin_username=data.get('admin_username', ''),
            admin_password=data.get('admin_password', '')
        )
        
        logger.info(f"Added NAS device: {data['device_name']} ({data['ip_address']})")
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'message': f'NAS device "{data["device_name"]}" added successfully'
        })
        
    except Exception as e:
        logger.error(f"Error adding NAS device: {e}")
        return jsonify({'error': f'Failed to add NAS device: {str(e)}'}), 500

@enterprise_nas_bp.route('/devices/<device_id>', methods=['GET'])
def get_nas_device(device_id: str):
    """Get specific NAS device details"""
    try:
        devices = enterprise_nas_folders.get_nas_devices()
        device = next((d for d in devices if d['device_id'] == device_id), None)
        
        if not device:
            return jsonify({'error': 'NAS device not found'}), 404
            
        return jsonify({
            'success': True,
            'device': device
        })
        
    except Exception as e:
        logger.error(f"Error getting NAS device {device_id}: {e}")
        return jsonify({'error': f'Failed to get NAS device: {str(e)}'}), 500

# ============================================================================
# SHARED FOLDER MANAGEMENT ENDPOINTS
# ============================================================================

@enterprise_nas_bp.route('/folders', methods=['GET'])
def get_all_folders():
    """Get all shared folders across all NAS devices"""
    try:
        folders = enterprise_nas_folders.get_all_folders()
        
        # Group by procedure type for summary
        procedure_summary = {}
        for folder in folders:
            proc_type = folder['procedure_type']
            if proc_type not in procedure_summary:
                procedure_summary[proc_type] = {
                    'count': 0,
                    'devices': set(),
                    'last_successful_test': None
                }
            procedure_summary[proc_type]['count'] += 1
            procedure_summary[proc_type]['devices'].add(folder['device_name'])
            
            if folder.get('last_successful'):
                if not procedure_summary[proc_type]['last_successful_test'] or \
                   folder['last_successful'] > procedure_summary[proc_type]['last_successful_test']:
                    procedure_summary[proc_type]['last_successful_test'] = folder['last_successful']
        
        # Convert sets to lists for JSON serialization
        for proc_type in procedure_summary:
            procedure_summary[proc_type]['devices'] = list(procedure_summary[proc_type]['devices'])
        
        return jsonify({
            'success': True,
            'folders': folders,
            'total_folders': len(folders),
            'procedure_summary': procedure_summary
        })
        
    except Exception as e:
        logger.error(f"Error getting folders: {e}")
        return jsonify({'error': f'Failed to get folders: {str(e)}'}), 500

@enterprise_nas_bp.route('/folders', methods=['POST'])
def add_shared_folder():
    """Add shared folder to NAS device for specific procedure"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['nas_device_id', 'procedure_type', 'share_name', 
                          'share_path', 'username', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Add shared folder
        folder_id = enterprise_nas_folders.add_shared_folder(
            nas_device_id=data['nas_device_id'],
            procedure_type=data['procedure_type'],
            share_name=data['share_name'],
            share_path=data['share_path'],
            username=data['username'],
            password=data['password'],
            domain=data.get('domain', ''),
            protocol=data.get('protocol', 'SMB'),
            mount_point=data.get('mount_point', ''),
            auto_mount=data.get('auto_mount', True),
            read_only=data.get('read_only', False),
            compression_type=data.get('compression_type', 'DICOM'),
            database_format=data.get('database_format', 'DICOM'),
            priority=data.get('priority', 5)
        )
        
        logger.info(f"Added shared folder: {data['share_name']} for {data['procedure_type']}")
        
        return jsonify({
            'success': True,
            'folder_id': folder_id,
            'message': f'Shared folder "{data["share_name"]}" added successfully for {data["procedure_type"]}'
        })
        
    except Exception as e:
        logger.error(f"Error adding shared folder: {e}")
        return jsonify({'error': f'Failed to add shared folder: {str(e)}'}), 500

@enterprise_nas_bp.route('/folders/<folder_id>', methods=['GET'])
def get_folder_config(folder_id: str):
    """Get specific folder configuration"""
    try:
        folder = enterprise_nas_folders.get_folder_config(folder_id)
        
        if not folder:
            return jsonify({'error': 'Folder not found'}), 404
            
        # Remove encrypted password from response
        folder_safe = folder.copy()
        folder_safe['password_encrypted'] = '[ENCRYPTED]'
        
        return jsonify({
            'success': True,
            'folder': folder_safe
        })
        
    except Exception as e:
        logger.error(f"Error getting folder {folder_id}: {e}")
        return jsonify({'error': f'Failed to get folder: {str(e)}'}), 500

@enterprise_nas_bp.route('/folders/<folder_id>/test', methods=['POST'])
def test_folder_connection(folder_id: str):
    """Test connection to specific shared folder"""
    try:
        success, message, details = enterprise_nas_folders.test_folder_connection(folder_id)
        
        return jsonify({
            'success': success,
            'message': message,
            'details': details,
            'test_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error testing folder {folder_id}: {e}")
        return jsonify({'error': f'Failed to test folder: {str(e)}'}), 500

@enterprise_nas_bp.route('/folders/test-all', methods=['POST'])
def test_all_folder_connections():
    """Test all shared folder connections"""
    try:
        results = enterprise_nas_folders.test_all_folders()
        
        return jsonify({
            'success': True,
            'test_results': results,
            'test_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error testing all folders: {e}")
        return jsonify({'error': f'Failed to test all folders: {str(e)}'}), 500

# ============================================================================
# PROCEDURE-SPECIFIC ENDPOINTS
# ============================================================================

@enterprise_nas_bp.route('/procedures', methods=['GET'])
def get_procedure_types():
    """Get all available procedure types"""
    try:
        procedures = enterprise_nas_folders.get_procedure_types()
        
        return jsonify({
            'success': True,
            'procedures': procedures
        })
        
    except Exception as e:
        logger.error(f"Error getting procedure types: {e}")
        return jsonify({'error': f'Failed to get procedure types: {str(e)}'}), 500

@enterprise_nas_bp.route('/procedures/<procedure_type>/folders', methods=['GET'])
def get_folders_by_procedure(procedure_type: str):
    """Get all shared folders for specific procedure type"""
    try:
        folders = enterprise_nas_folders.get_folders_by_procedure(procedure_type.upper())
        
        return jsonify({
            'success': True,
            'procedure_type': procedure_type.upper(),
            'folders': folders,
            'total_folders': len(folders)
        })
        
    except Exception as e:
        logger.error(f"Error getting folders for procedure {procedure_type}: {e}")
        return jsonify({'error': f'Failed to get folders for procedure: {str(e)}'}), 500

# ============================================================================
# INTEGRATION WITH EXISTING PACS SYSTEM
# ============================================================================

@enterprise_nas_bp.route('/integration/pacs-folders', methods=['GET'])
def get_pacs_integration_folders():
    """Get folders configured for PACS integration with credentials"""
    try:
        all_folders = enterprise_nas_folders.get_all_folders()
        
        # Format for PACS integration - include decrypted credentials
        pacs_folders = []
        for folder in all_folders:
            if folder['is_active']:
                credentials = enterprise_nas_folders.get_folder_credentials(folder['folder_id'])
                if credentials:
                    pacs_folder = {
                        'folder_id': folder['folder_id'],
                        'procedure_type': folder['procedure_type'],
                        'nas_device': {
                            'device_name': folder['device_name'],
                            'ip_address': folder['ip_address']
                        },
                        'connection': {
                            'protocol': credentials['protocol'],
                            'share_path': credentials['share_path'],
                            'username': credentials['username'],
                            'password': credentials['password'],
                            'domain': credentials['domain']
                        },
                        'indexing_config': {
                            'compression_type': folder['compression_type'],
                            'database_format': folder['database_format'],
                            'priority': folder['priority'],
                            'auto_mount': folder['auto_mount'],
                            'read_only': folder['read_only']
                        }
                    }
                    pacs_folders.append(pacs_folder)
        
        return jsonify({
            'success': True,
            'pacs_folders': pacs_folders,
            'total_active_folders': len(pacs_folders)
        })
        
    except Exception as e:
        logger.error(f"Error getting PACS integration folders: {e}")
        return jsonify({'error': f'Failed to get PACS integration folders: {str(e)}'}), 500

@enterprise_nas_bp.route('/integration/indexing-config/<procedure_type>', methods=['GET'])
def get_indexing_config_for_procedure(procedure_type: str):
    """Get indexing configuration for specific procedure type"""
    try:
        folders = enterprise_nas_folders.get_folders_by_procedure(procedure_type.upper())
        
        # Create indexing configuration
        indexing_config = {
            'procedure_type': procedure_type.upper(),
            'nas_sources': []
        }
        
        for folder in folders:
            if folder['is_active']:
                credentials = enterprise_nas_folders.get_folder_credentials(folder['folder_id'])
                if credentials:
                    nas_source = {
                        'source_id': folder['folder_id'],
                        'nas_device_ip': folder['ip_address'],
                        'share_path': credentials['share_path'],
                        'connection_string': f"{credentials['protocol']}://{credentials['username']}:{credentials['password']}@{credentials['share_path']}",
                        'compression_type': folder['compression_type'],
                        'database_format': folder['database_format'],
                        'priority': folder['priority']
                    }
                    indexing_config['nas_sources'].append(nas_source)
        
        return jsonify({
            'success': True,
            'indexing_config': indexing_config
        })
        
    except Exception as e:
        logger.error(f"Error getting indexing config for {procedure_type}: {e}")
        return jsonify({'error': f'Failed to get indexing config: {str(e)}'}), 500

# ============================================================================
# WEB INTERFACE ENDPOINTS
# ============================================================================

@enterprise_nas_bp.route('/config-ui', methods=['GET'])
def show_config_ui():
    """Show the enterprise NAS configuration web interface"""
    return render_template('enterprise_nas_folders_config.html')

# ============================================================================
# STATISTICS AND MONITORING
# ============================================================================

@enterprise_nas_bp.route('/stats', methods=['GET'])
def get_statistics():
    """Get statistics about NAS devices and shared folders"""
    try:
        devices = enterprise_nas_folders.get_nas_devices()
        all_folders = enterprise_nas_folders.get_all_folders()
        
        # Calculate statistics
        total_devices = len(devices)
        total_folders = len(all_folders)
        
        # Active procedures
        active_procedures = len(set(folder['procedure_type'] for folder in all_folders))
        
        # Connection success rate
        tested_folders = [f for f in all_folders if f.get('last_successful')]
        success_rate = (len(tested_folders) / total_folders * 100) if total_folders > 0 else 0
        
        # Procedure distribution
        procedure_distribution = {}
        for folder in all_folders:
            proc_type = folder['procedure_type']
            procedure_distribution[proc_type] = procedure_distribution.get(proc_type, 0) + 1
        
        # Manufacturer distribution
        manufacturer_distribution = {}
        for device in devices:
            manufacturer = device['manufacturer']
            manufacturer_distribution[manufacturer] = manufacturer_distribution.get(manufacturer, 0) + 1
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_devices': total_devices,
                'total_folders': total_folders,
                'active_procedures': active_procedures,
                'success_rate': round(success_rate, 2),
                'procedure_distribution': procedure_distribution,
                'manufacturer_distribution': manufacturer_distribution,
                'last_updated': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'error': f'Failed to get statistics: {str(e)}'}), 500

# ============================================================================
# EXPORT/IMPORT CONFIGURATION
# ============================================================================

@enterprise_nas_bp.route('/export', methods=['GET'])
def export_configuration():
    """Export all NAS and folder configurations"""
    try:
        devices = enterprise_nas_folders.get_nas_devices()
        procedures = enterprise_nas_folders.get_procedure_types()
        
        # Remove sensitive data for export
        export_data = {
            'export_info': {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'source': 'Ubuntu Patient Care Enterprise NAS'
            },
            'nas_devices': [],
            'procedure_types': procedures
        }
        
        for device in devices:
            device_export = device.copy()
            device_export['admin_password_encrypted'] = '[ENCRYPTED - NOT EXPORTED]'
            
            # Remove sensitive folder data
            for folder in device_export['shared_folders']:
                folder['password_encrypted'] = '[ENCRYPTED - NOT EXPORTED]'
                
            export_data['nas_devices'].append(device_export)
        
        return jsonify({
            'success': True,
            'configuration': export_data
        })
        
    except Exception as e:
        logger.error(f"Error exporting configuration: {e}")
        return jsonify({'error': f'Failed to export configuration: {str(e)}'}), 500

# Register error handlers
@enterprise_nas_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@enterprise_nas_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Export blueprint for registration in main app
__all__ = ['enterprise_nas_bp']