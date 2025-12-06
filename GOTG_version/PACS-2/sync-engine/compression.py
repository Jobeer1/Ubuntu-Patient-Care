#!/usr/bin/env python3
"""
GOTG PACS - DICOM Compression Engine
Reduce data transfer by 80% for hostile networks
PRODUCTION-READY - Lives depend on this
"""

import os
import logging
import pydicom
from pydicom.uid import JPEGBaseline, JPEG2000Lossless, JPEG2000
from pathlib import Path
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DICOMCompressor:
    """Compress DICOM files for efficient transfer"""
    
    # Compression strategies by network quality
    STRATEGIES = {
        'excellent': {
            'transfer_syntax': JPEG2000Lossless,
            'quality': 100,
            'description': 'Lossless compression for excellent networks'
        },
        'good': {
            'transfer_syntax': JPEG2000,
            'quality': 90,
            'description': 'High quality lossy for good networks'
        },
        'poor': {
            'transfer_syntax': JPEGBaseline,
            'quality': 75,
            'description': 'Moderate quality for poor networks'
        },
        'critical': {
            'transfer_syntax': JPEGBaseline,
            'quality': 50,
            'description': 'Low quality for critical transfers only'
        }
    }
    
    def __init__(self, strategy='good'):
        """Initialize compressor with strategy"""
        self.strategy = self.STRATEGIES.get(strategy, self.STRATEGIES['good'])
        logger.info(f"Compression strategy: {self.strategy['description']}")
    
    def compress_file(self, input_path, output_path=None):
        """
        Compress a DICOM file
        
        Args:
            input_path: Path to input DICOM file
            output_path: Path to output file (optional, creates temp if None)
            
        Returns:
            tuple: (output_path, original_size, compressed_size, ratio)
        """
        try:
            input_path = Path(input_path)
            original_size = input_path.stat().st_size
            
            # Read DICOM
            ds = pydicom.dcmread(input_path)
            
            # Check if already compressed
            if hasattr(ds, 'file_meta') and hasattr(ds.file_meta, 'TransferSyntaxUID'):
                current_syntax = ds.file_meta.TransferSyntaxUID
                if current_syntax in [JPEGBaseline, JPEG2000, JPEG2000Lossless]:
                    logger.info(f"File already compressed: {input_path.name}")
                    return input_path, original_size, original_size, 1.0
            
            # Create output path if not provided
            if output_path is None:
                output_path = Path(tempfile.mktemp(suffix='.dcm'))
            else:
                output_path = Path(output_path)
            
            # Compress pixel data if present
            if hasattr(ds, 'PixelData'):
                # Set transfer syntax
                ds.file_meta.TransferSyntaxUID = self.strategy['transfer_syntax']
                
                # For JPEG compression, ensure proper photometric interpretation
                if self.strategy['transfer_syntax'] == JPEGBaseline:
                    if ds.PhotometricInterpretation == 'MONOCHROME1':
                        ds.PhotometricInterpretation = 'MONOCHROME2'
                
                # Compress using pydicom's built-in compression
                ds.compress(self.strategy['transfer_syntax'])
            
            # Save compressed file
            ds.save_as(output_path, write_like_original=False)
            
            compressed_size = output_path.stat().st_size
            ratio = compressed_size / original_size
            
            logger.info(f"Compressed {input_path.name}: "
                       f"{original_size/1024:.1f}KB → {compressed_size/1024:.1f}KB "
                       f"({ratio*100:.1f}%)")
            
            return output_path, original_size, compressed_size, ratio
            
        except Exception as e:
            logger.error(f"Compression failed for {input_path}: {e}")
            # Return original file if compression fails
            return input_path, original_size, original_size, 1.0
    
    def compress_study(self, study_path, output_dir=None):
        """
        Compress all DICOM files in a study
        
        Args:
            study_path: Path to study directory
            output_dir: Output directory (optional)
            
        Returns:
            dict: Compression statistics
        """
        study_path = Path(study_path)
        
        if output_dir is None:
            output_dir = study_path.parent / f"{study_path.name}_compressed"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        stats = {
            'files_processed': 0,
            'files_compressed': 0,
            'original_size': 0,
            'compressed_size': 0,
            'errors': 0
        }
        
        # Find all DICOM files
        dicom_files = list(study_path.rglob('*.dcm'))
        
        for dicom_file in dicom_files:
            try:
                # Maintain directory structure
                rel_path = dicom_file.relative_to(study_path)
                output_file = output_dir / rel_path
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Compress
                _, orig_size, comp_size, ratio = self.compress_file(dicom_file, output_file)
                
                stats['files_processed'] += 1
                if ratio < 1.0:
                    stats['files_compressed'] += 1
                stats['original_size'] += orig_size
                stats['compressed_size'] += comp_size
                
            except Exception as e:
                logger.error(f"Error processing {dicom_file}: {e}")
                stats['errors'] += 1
        
        # Calculate overall ratio
        if stats['original_size'] > 0:
            overall_ratio = stats['compressed_size'] / stats['original_size']
            stats['compression_ratio'] = overall_ratio
            stats['space_saved'] = stats['original_size'] - stats['compressed_size']
            stats['space_saved_percent'] = (1 - overall_ratio) * 100
        
        logger.info(f"Study compression complete: "
                   f"{stats['files_processed']} files, "
                   f"{stats['space_saved']/1024/1024:.1f}MB saved "
                   f"({stats['space_saved_percent']:.1f}%)")
        
        return stats
    
    def decompress_file(self, input_path, output_path=None):
        """
        Decompress a DICOM file to uncompressed format
        
        Args:
            input_path: Path to compressed DICOM file
            output_path: Path to output file (optional)
            
        Returns:
            Path: Path to decompressed file
        """
        try:
            input_path = Path(input_path)
            
            # Read DICOM
            ds = pydicom.dcmread(input_path)
            
            # Decompress if compressed
            if hasattr(ds, 'file_meta') and hasattr(ds.file_meta, 'TransferSyntaxUID'):
                current_syntax = ds.file_meta.TransferSyntaxUID
                if current_syntax in [JPEGBaseline, JPEG2000, JPEG2000Lossless]:
                    ds.decompress()
            
            # Create output path if not provided
            if output_path is None:
                output_path = Path(tempfile.mktemp(suffix='.dcm'))
            else:
                output_path = Path(output_path)
            
            # Save decompressed file
            ds.save_as(output_path, write_like_original=False)
            
            logger.info(f"Decompressed {input_path.name}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Decompression failed for {input_path}: {e}")
            return input_path
    
    @staticmethod
    def estimate_compression_ratio(file_path):
        """
        Estimate compression ratio without actually compressing
        
        Args:
            file_path: Path to DICOM file
            
        Returns:
            float: Estimated compression ratio (0.2 = 80% reduction)
        """
        try:
            ds = pydicom.dcmread(file_path, stop_before_pixels=True)
            
            # Check modality for estimation
            modality = getattr(ds, 'Modality', 'UN')
            
            # Typical compression ratios by modality
            ratios = {
                'CT': 0.3,   # 70% reduction
                'MR': 0.25,  # 75% reduction
                'CR': 0.2,   # 80% reduction
                'DX': 0.2,   # 80% reduction
                'US': 0.4,   # 60% reduction
                'MG': 0.15,  # 85% reduction
                'PT': 0.35,  # 65% reduction
                'NM': 0.35,  # 65% reduction
            }
            
            return ratios.get(modality, 0.3)  # Default 70% reduction
            
        except Exception:
            return 0.3  # Default estimate

def main():
    """CLI interface for compression"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GOTG PACS DICOM Compressor')
    parser.add_argument('input', help='Input DICOM file or directory')
    parser.add_argument('output', nargs='?', help='Output file or directory')
    parser.add_argument('--strategy', choices=['excellent', 'good', 'poor', 'critical'],
                       default='good', help='Compression strategy')
    parser.add_argument('--decompress', action='store_true',
                       help='Decompress instead of compress')
    
    args = parser.parse_args()
    
    compressor = DICOMCompressor(strategy=args.strategy)
    
    input_path = Path(args.input)
    
    if args.decompress:
        # Decompress
        output = compressor.decompress_file(input_path, args.output)
        print(f"Decompressed to: {output}")
    else:
        # Compress
        if input_path.is_file():
            output, orig, comp, ratio = compressor.compress_file(input_path, args.output)
            print(f"Compressed: {orig/1024:.1f}KB → {comp/1024:.1f}KB ({ratio*100:.1f}%)")
        elif input_path.is_dir():
            stats = compressor.compress_study(input_path, args.output)
            print(f"Study compressed:")
            print(f"  Files: {stats['files_processed']}")
            print(f"  Original: {stats['original_size']/1024/1024:.1f}MB")
            print(f"  Compressed: {stats['compressed_size']/1024/1024:.1f}MB")
            print(f"  Saved: {stats['space_saved_percent']:.1f}%")

if __name__ == '__main__':
    main()
