"""
NAS File Operations Service  
Handles file serving, DICOM conversion, and download archive creation
"""

import os
import logging
import zipfile
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import subprocess

logger = logging.getLogger(__name__)

def get_patient_files(patient_folder_path):
    """Get list of files in a patient folder"""
    try:
        if not os.path.exists(patient_folder_path):
            logger.error(f"Patient folder not found: {patient_folder_path}")
            return []
        
        files = []
        for root, dirs, filenames in os.walk(patient_folder_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, patient_folder_path)
                
                # Get file info
                try:
                    stat = os.stat(file_path)
                    file_size = stat.st_size
                    modified_time = stat.st_mtime
                    
                    # Determine file type
                    file_type = get_file_type(filename, file_path)
                    
                    files.append({
                        'filename': filename,
                        'relative_path': relative_path,
                        'full_path': file_path,
                        'size': file_size,
                        'modified_time': modified_time,
                        'type': file_type,
                        'is_dicom': is_dicom_file(filename, file_path)
                    })
                except Exception as e:
                    logger.warning(f"Error getting file info for {file_path}: {e}")
        
        # Sort by filename
        files.sort(key=lambda x: x['filename'])
        
        logger.info(f"📁 Found {len(files)} files in patient folder")
        return files
        
    except Exception as e:
        logger.error(f"Error getting patient files: {e}")
        return []

def get_file_type(filename, file_path=None):
    """Determine file type from filename and optionally file content"""
    try:
        filename_lower = filename.lower()
        
        # DICOM files
        if filename_lower.endswith(('.dcm', '.dicom')):
            return 'dicom'
        
        # Image files
        if filename_lower.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')):
            return 'image'
        
        # Check if it might be a DICOM file without extension
        if '.' not in filename and file_path and os.path.exists(file_path):
            try:
                # Check file size - DICOM files are usually larger than 1KB
                if os.path.getsize(file_path) > 1024:
                    return 'dicom'
            except:
                pass
        
        # Other file types
        if filename_lower.endswith(('.pdf', '.doc', '.docx')):
            return 'document'
        if filename_lower.endswith(('.txt', '.log')):
            return 'text'
        if filename_lower.endswith(('.zip', '.rar', '.7z')):
            return 'archive'
        
        return 'unknown'
        
    except Exception as e:
        logger.error(f"Error determining file type: {e}")
        return 'unknown'

def is_dicom_file(filename, file_path=None):
    """Check if a file is likely a DICOM file"""
    try:
        # Check extension first
        if filename.lower().endswith(('.dcm', '.dicom')):
            return True
        
        # Check files without extensions that might be DICOM
        if '.' not in filename and file_path and os.path.exists(file_path):
            try:
                # Simple heuristic: DICOM files usually start with specific bytes
                with open(file_path, 'rb') as f:
                    # Skip to byte 128 where DICOM prefix should be
                    f.seek(128)
                    prefix = f.read(4)
                    if prefix == b'DICM':
                        return True
                    
                    # Some DICOM files don't have the prefix, check file size
                    f.seek(0, 2)  # Go to end
                    size = f.tell()
                    if size > 1024:  # Assume files > 1KB might be DICOM
                        return True
            except:
                pass
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking if DICOM file: {e}")
        return False

def serve_file_securely(file_path, as_attachment=False):
    """Securely serve a file (placeholder implementation)"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        # In a real implementation, this would use Flask's send_file
        # with proper security checks and headers
        
        return {
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'size': os.path.getsize(file_path),
            'as_attachment': as_attachment
        }
        
    except Exception as e:
        logger.error(f"Error serving file: {e}")
        return None

def convert_dicom_to_png(dicom_file_path, output_path=None):
    """Convert DICOM file to PNG image"""
    try:
        if not os.path.exists(dicom_file_path):
            logger.error(f"DICOM file not found: {dicom_file_path}")
            return None
        
        # Create output path if not provided
        if not output_path:
            base_name = os.path.splitext(os.path.basename(dicom_file_path))[0]
            output_path = os.path.join(tempfile.gettempdir(), f"{base_name}.png")
        
        try:
            # Try using pydicom if available
            import pydicom
            from pydicom.pixel_data_handlers.util import apply_windowing
            
            # Read DICOM file
            ds = pydicom.dcmread(dicom_file_path)
            
            if hasattr(ds, 'pixel_array'):
                # Get pixel data
                pixel_array = ds.pixel_array
                
                # Apply windowing if available
                if hasattr(ds, 'WindowCenter') and hasattr(ds, 'WindowWidth'):
                    pixel_array = apply_windowing(pixel_array, ds)
                
                # Convert to PIL Image
                if len(pixel_array.shape) == 2:  # Grayscale
                    # Normalize to 0-255 range
                    pixel_array = ((pixel_array - pixel_array.min()) * 255.0 / 
                                 (pixel_array.max() - pixel_array.min())).astype('uint8')
                    image = Image.fromarray(pixel_array, mode='L')
                else:  # RGB
                    image = Image.fromarray(pixel_array)
                
                # Save as PNG
                image.save(output_path, 'PNG')
                logger.info(f"🖼️ DICOM converted to PNG: {output_path}")
                return output_path
        
        except ImportError:
            logger.warning("pydicom not available, trying alternative method")
            # Fallback method using ImageMagick or other tools
            return convert_dicom_fallback(dicom_file_path, output_path)
        
        except Exception as e:
            logger.error(f"Error with pydicom conversion: {e}")
            return convert_dicom_fallback(dicom_file_path, output_path)
        
        return None
        
    except Exception as e:
        logger.error(f"Error converting DICOM to PNG: {e}")
        return None

def convert_dicom_fallback(dicom_file_path, output_path):
    """Fallback DICOM conversion method"""
    try:
        # Try using ImageMagick convert command
        cmd = ['convert', dicom_file_path, output_path]
        
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info(f"🖼️ DICOM converted using ImageMagick: {output_path}")
            return output_path
        else:
            logger.error(f"ImageMagick conversion failed: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Fallback conversion error: {e}")
        return None

def create_download_archive(files_list, format_type='dicom', output_path=None):
    """Create downloadable archive of patient files"""
    try:
        if not files_list:
            logger.error("No files provided for archive")
            return None
        
        # Create output path if not provided
        if not output_path:
            timestamp = int(datetime.now().timestamp())
            output_path = os.path.join(tempfile.gettempdir(), f"patient_files_{timestamp}.zip")
        
        # Create ZIP archive
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            files_added = 0
            
            for file_info in files_list:
                file_path = file_info.get('full_path') or file_info.get('file_path')
                
                if not file_path or not os.path.exists(file_path):
                    logger.warning(f"File not found for archive: {file_path}")
                    continue
                
                # Determine archive filename
                archive_filename = file_info.get('filename') or os.path.basename(file_path)
                
                if format_type == 'png' and is_dicom_file(archive_filename, file_path):
                    # Convert DICOM to PNG
                    png_path = convert_dicom_to_png(file_path)
                    if png_path:
                        # Add PNG to archive
                        png_filename = os.path.splitext(archive_filename)[0] + '.png'
                        zipf.write(png_path, png_filename)
                        files_added += 1
                        
                        # Clean up temporary PNG
                        try:
                            os.remove(png_path)
                        except:
                            pass
                elif format_type == 'dicom' or not is_dicom_file(archive_filename, file_path):
                    # Add original file to archive
                    zipf.write(file_path, archive_filename)
                    files_added += 1
        
        if files_added > 0:
            logger.info(f"📦 Created archive with {files_added} files: {output_path}")
            return output_path
        else:
            # Remove empty archive
            try:
                os.remove(output_path)
            except:
                pass
            logger.error("No files were added to archive")
            return None
            
    except Exception as e:
        logger.error(f"Error creating download archive: {e}")
        return None

def cleanup_temp_files(file_paths):
    """Clean up temporary files"""
    try:
        cleaned_count = 0
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"Could not remove temp file {file_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"🧹 Cleaned up {cleaned_count} temporary files")
        
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {e}")

# Add missing import
from datetime import datetime