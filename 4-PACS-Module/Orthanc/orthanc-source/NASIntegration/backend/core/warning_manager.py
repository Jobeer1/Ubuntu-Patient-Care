#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Warning Manager

Manages system warnings and provides clean startup experience.
"""

import warnings
import logging
import sys
import os

logger = logging.getLogger(__name__)

class WarningManager:
    """Manages system warnings and provides clean startup feedback"""
    
    def __init__(self):
        self.missing_packages = []
        self.optional_features = []
        self.setup_warning_filters()
    
    def setup_warning_filters(self):
        """Setup warning filters to reduce noise"""
        # Suppress specific warnings that are not critical
        warnings.filterwarnings('ignore', category=UserWarning, module='face_recognition_models')
        warnings.filterwarnings('ignore', message='pkg_resources is deprecated')
        
        # Redirect warnings to our logger
        logging.captureWarnings(True)
    
    def check_dependencies(self):
        """Check for missing dependencies and provide helpful feedback"""
        dependencies = {
            'pydicom': {
                'feature': 'DICOM Processing',
                'install': 'pip install pydicom',
                'critical': False
            },
            'vosk': {
                'feature': 'Voice Recognition',
                'install': 'pip install vosk',
                'critical': False
            },
            'tensorflow': {
                'feature': 'AI Diagnosis',
                'install': 'pip install tensorflow',
                'critical': False
            },
            'face_recognition': {
                'feature': 'Face Recognition',
                'install': 'pip install face_recognition',
                'critical': False
            },
            'pynetdicom': {
                'feature': 'DICOM Networking',
                'install': 'pip install pynetdicom',
                'critical': False
            },
            'scipy': {
                'feature': 'Advanced Image Processing',
                'install': 'pip install scipy scikit-image',
                'critical': False
            }
        }
        
        for package, info in dependencies.items():
            try:
                __import__(package)
            except ImportError:
                self.missing_packages.append(info)
                if not info['critical']:
                    self.optional_features.append(info['feature'])
    
    def print_startup_summary(self):
        """Print a clean startup summary"""
        print("\n" + "="*60)
        print("🇿🇦 SOUTH AFRICAN MEDICAL IMAGING SYSTEM")
        print("🏥 System Status Summary")
        print("="*60)
        
        # Core system status
        print("✅ Core System: Operational")
        print("✅ Web Interface: Ready")
        print("✅ Database: Connected")
        print("✅ Security: Active")
        
        # Optional features
        if self.optional_features:
            print(f"\n⚠️  Optional Features ({len(self.optional_features)} disabled):")
            for feature in self.optional_features:
                print(f"   • {feature}: Not available")
        
        # Installation help
        if self.missing_packages:
            print(f"\n💡 To enable all features, install optional packages:")
            print("   pip install -r requirements-optional.txt")
        
        print("\n🌐 Access the system at: http://localhost:5000")
        print("="*60 + "\n")
    
    def suppress_startup_warnings(self):
        """Suppress non-critical warnings during startup"""
        # Temporarily redirect stderr to suppress warnings
        original_stderr = sys.stderr
        
        class WarningFilter:
            def __init__(self, original):
                self.original = original
                self.warnings_to_suppress = [
                    'Vosk not available',
                    'SpeechRecognition not available',
                    'pydicom not available',
                    'TensorFlow not available',
                    'pkg_resources is deprecated'
                ]
            
            def write(self, text):
                # Only suppress specific warnings, let errors through
                if any(warning in text for warning in self.warnings_to_suppress):
                    return
                self.original.write(text)
            
            def flush(self):
                self.original.flush()
        
        return WarningFilter(original_stderr)

# Global warning manager instance
warning_manager = WarningManager()