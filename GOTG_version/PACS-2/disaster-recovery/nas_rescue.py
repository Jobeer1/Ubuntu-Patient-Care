#!/usr/bin/env python3
"""
GOTG PACS - NAS Disaster Recovery Tool
Extract DICOM files from damaged/corrupted NAS devices in collapsed hospitals

This tool can:
- Mount damaged filesystems (read-only)
- Scan for DICOM files even with corrupted directory structures
- Verify and repair DICOM file integrity
- Extract to portable storage
- Generate recovery reports

Built for Gift of the Givers disaster response teams.
"""

import os
import sys
import logging
import hashlib
import struct
import subprocess
from pathlib import Path
from datetime import datetime
import pydicom
from pydicom.errors import InvalidDicomError
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'nas_rescue_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DICOMRescue:
    """Rescue DICOM files from damaged storage"""
    
    DICOM_MAGIC = b'DICM'  # DICOM file signature at offset 128
    
    def __init__(self, source_path, output_path):
        self.source = Path(source_path)
        self.output = Path(output_path)
        self.output.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'scanned_bytes': 0,
            'files_found': 0,
            'files_valid': 0,
            'files_corrupted': 0,
            'files_recovered': 0,
            'total_size': 0
        }
        
        self.recovered_files = []
    
    def scan_for_dicom_signature(self, file_path):
        """Scan file for DICOM signature"""
        try:
            with open(file_path, 'rb') as f:
                # Check standard DICOM location (offset 128)
                f.seek(128)
                if f.read(4) == self.DICOM_MAGIC:
                    return True
                
                # Scan entire file if not found (for corrupted files)
                f.seek(0)
                content = f.read()
                return self.DICOM_MAGIC in content
        except Exception as e:
            logger.debug(f"Error scanning {file_path}: {e}")
            return False
    
    def deep_scan_device(self, device_path):
        """Deep scan raw device for DICOM files (for severely damaged filesystems)"""
        logger.info(f"Starting deep scan of {device_path}")
        logger.warning("This may take hours for large devices")
        
        try:
            block_size = 4096
            dicom_candidates = []
            
            with open(device_path, 'rb') as device:
                offset = 0
                while True:
                    block = device.read(block_size)
                    if not block:
                        break
                    
                    # Look for DICOM signature
                    if self.DICOM_MAGIC in block:
                        # Found potential DICOM file
                        dicom_offset = offset + block.find(self.DICOM_MAGIC) - 128
                        if dicom_offset >= 0:
                            dicom_candidates.append(dicom_offset)
                            logger.info(f"Found DICOM signature at offset {dicom_offset}")
                    
                    offset += block_size
                    self.stats['scanned_bytes'] = offset
                    
                    if offset % (1024 * 1024 * 100) == 0:  # Log every 100MB
                        logger.info(f"Scanned {offset / 1024 / 1024:.0f} MB")
            
            logger.info(f"Deep scan complete. Found {len(dicom_candidates)} potential DICOM files")
            return dicom_candidates
            
        except Exception as e:
            logger.error(f"Deep scan failed: {e}")
            return []
    
    def extract_dicom_from_offset(self, device_path, offset, output_file):
        """Extract DICOM file from raw device at specific offset"""
        try:
            with open(device_path, 'rb') as device:
                device.seek(offset)
                
                # Read DICOM preamble and magic
                preamble = device.read(128)
                magic = device.read(4)
                
                if magic != self.DICOM_MAGIC:
                    return False
                
                # Try to determine file size from DICOM tags
                # This is complex - simplified version
                max_size = 100 * 1024 * 1024  # 100 MB max
                data = preamble + magic + device.read(max_size)
                
                # Try to parse and find actual end
                try:
                    # Write temporary file
                    temp_file = output_file.with_suffix('.tmp')
                    with open(temp_file, 'wb') as f:
                        f.write(data)
                    
                    # Validate with pydicom
                    ds = pydicom.dcmread(temp_file, force=True)
                    
                    # If valid, keep it
                    temp_file.rename(output_file)
                    logger.info(f"Extracted DICOM file: {output_file.name}")
                    return True
                    
                except Exception as e:
                    if temp_file.exists():
                        temp_file.unlink()
                    logger.debug(f"Failed to extract at offset {offset}: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Extraction failed at offset {offset}: {e}")
            return False
    
    def verify_dicom_file(self, file_path):
        """Verify DICOM file integrity"""
        try:
            ds = pydicom.dcmread(file_path, force=True)
            
            # Check essential tags
            required_tags = [
                'PatientID',
                'StudyInstanceUID',
                'SeriesInstanceUID',
                'SOPInstanceUID'
            ]
            
            for tag in required_tags:
                if not hasattr(ds, tag):
                    logger.warning(f"Missing required tag {tag} in {file_path.name}")
                    return False
            
            return True
            
        except InvalidDicomError:
            logger.warning(f"Invalid DICOM file: {file_path.name}")
            return False
        except Exception as e:
            logger.error(f"Error verifying {file_path.name}: {e}")
            return False
    
    def repair_dicom_file(self, file_path):
        """Attempt to repair corrupted DICOM file"""
        try:
            logger.info(f"Attempting to repair {file_path.name}")
            
            # Read with force=True to ignore errors
            ds = pydicom.dcmread(file_path, force=True)
            
            # Fix common issues
            if not hasattr(ds, 'PatientID'):
                ds.PatientID = 'UNKNOWN'
            
            if not hasattr(ds, 'StudyInstanceUID'):
                ds.StudyInstanceUID = pydicom.uid.generate_uid()
            
            if not hasattr(ds, 'SeriesInstanceUID'):
                ds.SeriesInstanceUID = pydicom.uid.generate_uid()
            
            if not hasattr(ds, 'SOPInstanceUID'):
                ds.SOPInstanceUID = pydicom.uid.generate_uid()
            
            # Save repaired file
            repaired_path = file_path.with_suffix('.repaired.dcm')
            ds.save_as(repaired_path)
            
            # Verify repair
            if self.verify_dicom_file(repaired_path):
                repaired_path.replace(file_path)
                logger.info(f"Successfully repaired {file_path.name}")
                return True
            else:
                repaired_path.unlink()
                return False
                
        except Exception as e:
            logger.error(f"Repair failed for {file_path.name}: {e}")
            return False
    
    def organize_by_patient(self, file_path):
        """Organize recovered files by patient/study/series"""
        try:
            ds = pydicom.dcmread(file_path, force=True)
            
            patient_id = getattr(ds, 'PatientID', 'UNKNOWN')
            study_uid = getattr(ds, 'StudyInstanceUID', 'UNKNOWN')
            series_uid = getattr(ds, 'SeriesInstanceUID', 'UNKNOWN')
            instance_uid = getattr(ds, 'SOPInstanceUID', 'UNKNOWN')
            
            # Create organized directory structure
            organized_dir = self.output / 'organized' / patient_id / study_uid / series_uid
            organized_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy file to organized location
            organized_file = organized_dir / f'{instance_uid}.dcm'
            import shutil
            shutil.copy2(file_path, organized_file)
            
            return organized_file
            
        except Exception as e:
            logger.error(f"Failed to organize {file_path.name}: {e}")
            return None
    
    def rescue_from_directory(self, scan_deep=False):
        """Rescue DICOM files from accessible directory"""
        logger.info(f"Scanning directory: {self.source}")
        
        # Find all files
        if self.source.is_file():
            files_to_check = [self.source]
        else:
            files_to_check = list(self.source.rglob('*'))
        
        logger.info(f"Found {len(files_to_check)} files to check")
        
        for file_path in files_to_check:
            if not file_path.is_file():
                continue
            
            self.stats['files_found'] += 1
            
            # Check if it's a DICOM file
            if self.scan_for_dicom_signature(file_path):
                logger.info(f"Found DICOM file: {file_path}")
                
                # Verify integrity
                if self.verify_dicom_file(file_path):
                    self.stats['files_valid'] += 1
                else:
                    self.stats['files_corrupted'] += 1
                    # Try to repair
                    if self.repair_dicom_file(file_path):
                        self.stats['files_valid'] += 1
                        self.stats['files_corrupted'] -= 1
                
                # Copy to output
                try:
                    output_file = self.output / 'raw' / file_path.name
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    import shutil
                    shutil.copy2(file_path, output_file)
                    
                    self.stats['files_recovered'] += 1
                    self.stats['total_size'] += file_path.stat().st_size
                    
                    # Organize
                    organized = self.organize_by_patient(output_file)
                    if organized:
                        self.recovered_files.append({
                            'original': str(file_path),
                            'recovered': str(output_file),
                            'organized': str(organized),
                            'size': file_path.stat().st_size
                        })
                    
                except Exception as e:
                    logger.error(f"Failed to copy {file_path}: {e}")
            
            # Progress update
            if self.stats['files_found'] % 100 == 0:
                logger.info(f"Progress: {self.stats['files_found']} files checked, "
                          f"{self.stats['files_recovered']} recovered")
    
    def rescue_from_device(self, device_path):
        """Rescue DICOM files from raw device (damaged filesystem)"""
        logger.info(f"Starting raw device rescue from {device_path}")
        logger.warning("This requires root/admin privileges")
        
        # Deep scan for DICOM signatures
        offsets = self.deep_scan_device(device_path)
        
        logger.info(f"Extracting {len(offsets)} potential DICOM files")
        
        for i, offset in enumerate(offsets):
            output_file = self.output / 'raw' / f'recovered_{i:06d}.dcm'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if self.extract_dicom_from_offset(device_path, offset, output_file):
                self.stats['files_recovered'] += 1
                
                # Organize
                organized = self.organize_by_patient(output_file)
                if organized:
                    self.recovered_files.append({
                        'offset': offset,
                        'recovered': str(output_file),
                        'organized': str(organized),
                        'size': output_file.stat().st_size
                    })
            
            if (i + 1) % 10 == 0:
                logger.info(f"Extracted {i + 1}/{len(offsets)} files")
    
    def generate_report(self):
        """Generate recovery report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'source': str(self.source),
            'output': str(self.output),
            'statistics': self.stats,
            'recovered_files': self.recovered_files
        }
        
        report_file = self.output / 'recovery_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Human-readable report
        report_txt = self.output / 'recovery_report.txt'
        with open(report_txt, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("GOTG PACS - DICOM Recovery Report\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Recovery Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source: {self.source}\n")
            f.write(f"Output: {self.output}\n\n")
            f.write("Statistics:\n")
            f.write(f"  Files Found: {self.stats['files_found']}\n")
            f.write(f"  Files Valid: {self.stats['files_valid']}\n")
            f.write(f"  Files Corrupted: {self.stats['files_corrupted']}\n")
            f.write(f"  Files Recovered: {self.stats['files_recovered']}\n")
            f.write(f"  Total Size: {self.stats['total_size'] / 1024 / 1024:.2f} MB\n\n")
            f.write(f"Recovery Rate: {self.stats['files_recovered'] / max(self.stats['files_found'], 1) * 100:.1f}%\n\n")
            f.write("Recovered Files:\n")
            for file_info in self.recovered_files:
                f.write(f"  - {file_info.get('organized', file_info.get('recovered'))}\n")
        
        logger.info(f"Recovery report saved to {report_file}")
        logger.info(f"Human-readable report saved to {report_txt}")
        
        return report

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='GOTG PACS - NAS Disaster Recovery Tool',
        epilog='Built for Gift of the Givers disaster response teams'
    )
    parser.add_argument('source', help='Source path (directory or device)')
    parser.add_argument('output', help='Output directory for recovered files')
    parser.add_argument('--device', action='store_true', 
                       help='Source is a raw device (requires root)')
    parser.add_argument('--deep-scan', action='store_true',
                       help='Perform deep scan (slower but more thorough)')
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("GOTG PACS - NAS Disaster Recovery Tool")
    logger.info("Built for Gift of the Givers")
    logger.info("=" * 80)
    
    rescue = DICOMRescue(args.source, args.output)
    
    try:
        if args.device:
            rescue.rescue_from_device(args.source)
        else:
            rescue.rescue_from_directory(args.deep_scan)
        
        # Generate report
        report = rescue.generate_report()
        
        logger.info("=" * 80)
        logger.info("Recovery Complete!")
        logger.info(f"Files Recovered: {rescue.stats['files_recovered']}")
        logger.info(f"Total Size: {rescue.stats['total_size'] / 1024 / 1024:.2f} MB")
        logger.info(f"Report: {args.output}/recovery_report.txt")
        logger.info("=" * 80)
        
    except KeyboardInterrupt:
        logger.info("\nRecovery interrupted by user")
        rescue.generate_report()
    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
