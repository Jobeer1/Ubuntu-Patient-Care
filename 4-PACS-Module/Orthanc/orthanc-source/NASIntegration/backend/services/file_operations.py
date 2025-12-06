"""
File Operations Service  
Handles file serving, downloads, and image conversion
"""

import logging
import os
import zipfile
import tempfile
from pathlib import Path
from io import BytesIO

logger = logging.getLogger(__name__)

def get_patient_files(patient_folder_path):
    """Get list of files in patient folder"""
    try:
        if not os.path.exists(patient_folder_path):
            return []
        
        files = []
        for root, dirs, filenames in os.walk(patient_folder_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                try:
                    file_size = os.path.getsize(file_path)
                    files.append({
                        'name': filename,
                        'path': os.path.relpath(file_path, patient_folder_path),
                        'full_path': file_path,
                        'size': format_file_size(file_size),
                        'type': get_file_type(filename)
                    })
                except:
                    continue
        
        return sorted(files, key=lambda x: x['name'])
        
    except Exception as e:
        logger.error(f"Error getting patient files: {e}")
        return []

def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"

def get_file_type(filename):
    """Determine file type from extension"""
    ext = os.path.splitext(filename)[1].lower()
    
    if ext in ['.dcm', '.dicom', '.ima']:
        return 'DICOM'
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
        return 'Image'
    elif ext in ['.pdf']:
        return 'PDF'
    elif ext in ['.txt', '.log']:
        return 'Text'
    else:
        return 'Unknown'

def create_download_archive(files, format_type='dicom'):
    """Create ZIP archive of files for download"""
    try:
        memory_file = BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_info in files:
                if os.path.exists(file_info['full_path']):
                    if format_type == 'dicom':
                        # Add DICOM files as-is
                        zf.write(file_info['full_path'], file_info['name'])
                    elif format_type == 'jpeg':
                        # Convert DICOM to JPEG if possible
                        jpeg_data = convert_dicom_to_jpeg(file_info['full_path'])
                        if jpeg_data:
                            jpeg_name = os.path.splitext(file_info['name'])[0] + '.jpg'
                            zf.writestr(jpeg_name, jpeg_data)
        
        memory_file.seek(0)
        return memory_file.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating download archive: {e}")
        return None

def convert_dicom_to_jpeg(dicom_file_path):
    """Convert DICOM file to JPEG"""
    try:
        import pydicom
        from PIL import Image
        import numpy as np
        
        # Read DICOM file
        ds = pydicom.dcmread(dicom_file_path)
        
        # Get pixel array
        pixel_array = ds.pixel_array
        
        # Normalize to 0-255 range
        if pixel_array.max() > 255:
            pixel_array = ((pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
        
        # Convert to PIL Image
        image = Image.fromarray(pixel_array)
        
        # Convert to RGB if grayscale
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save to bytes
        img_bytes = BytesIO()
        image.save(img_bytes, format='JPEG', quality=90)
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
        
    except Exception as e:
        logger.error(f"Error converting DICOM to JPEG: {e}")
        return None

def convert_dicom_to_png(dicom_file_path):
    """Convert DICOM file to PNG for viewing"""
    try:
        import pydicom
        from PIL import Image
        import numpy as np
        
        # Read DICOM file
        ds = pydicom.dcmread(dicom_file_path)
        
        # Get pixel array
        pixel_array = ds.pixel_array
        
        # Apply window/level if available
        if hasattr(ds, 'WindowCenter') and hasattr(ds, 'WindowWidth'):
            center = float(ds.WindowCenter) if not isinstance(ds.WindowCenter, list) else float(ds.WindowCenter[0])
            width = float(ds.WindowWidth) if not isinstance(ds.WindowWidth, list) else float(ds.WindowWidth[0])
            
            min_val = center - width / 2
            max_val = center + width / 2
            
            pixel_array = np.clip(pixel_array, min_val, max_val)
        
        # Normalize to 0-255 range
        if pixel_array.max() > pixel_array.min():
            pixel_array = ((pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
        else:
            pixel_array = pixel_array.astype(np.uint8)
        
        # Convert to PIL Image
        image = Image.fromarray(pixel_array)
        
        # Save to bytes
        img_bytes = BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
        
    except Exception as e:
        logger.error(f"Error converting DICOM to PNG: {e}")
        return None

def serve_file_securely(file_path, share_id):
    """Serve file with security checks"""
    try:
        if not os.path.exists(file_path):
            return None, "File not found"
        
        # Additional security checks could be added here
        # For example, verify the file belongs to the share
        
        with open(file_path, 'rb') as f:
            return f.read(), None
            
    except Exception as e:
        logger.error(f"Error serving file {file_path}: {e}")
        return None, str(e)