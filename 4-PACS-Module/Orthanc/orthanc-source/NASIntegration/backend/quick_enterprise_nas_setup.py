#!/usr/bin/env python3
"""
🏥 Quick Setup - Enterprise NAS Shared Folders System
Ubuntu Patient Care - Demonstration and Testing Script

This script demonstrates the complete enterprise shared folders system:
1. Multiple NAS devices with different procedures
2. Shared folders with unique credentials per procedure
3. Integration with your existing Orthanc PACS infrastructure
"""

import sys
import os
import logging

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("🏥 " + "="*80)
    print("🇿🇦 UBUNTU PATIENT CARE - ENTERPRISE NAS SHARED FOLDERS SYSTEM")
    print("="*84)
    print()
    
    try:
        # Import the enterprise configuration manager
        from enterprise_nas_shared_folders_config import EnterpriseNASFoldersManager
        
        print("✅ Initializing Enterprise NAS Shared Folders Manager...")
        manager = EnterpriseNASFoldersManager()
        
        print("\n🏗️ SETTING UP DEMO CONFIGURATION")
        print("="*50)
        
        # Add NAS Device #1 - Primary Medical NAS (Your current Z: drive equivalent)
        print("📡 Adding NAS Device #1: Primary Medical NAS...")
        nas1_id = manager.add_nas_device(
            device_name="Primary Medical NAS (Z: equivalent)",
            ip_address="192.168.1.100", 
            manufacturer="Synology",
            model="DS920+",
            default_domain="HOSPITAL",
            admin_username="admin",
            admin_password="secure_admin_password"
        )
        
        # Add NAS Device #2 - Secondary with Firebird
        print("📡 Adding NAS Device #2: Secondary Medical NAS...")
        nas2_id = manager.add_nas_device(
            device_name="Secondary Medical NAS (Y: equivalent)",
            ip_address="192.168.1.101",
            manufacturer="QNAP", 
            model="TS-464",
            default_domain="HOSPITAL",
            admin_username="admin",
            admin_password="secure_admin_password"
        )
        
        # Add NAS Device #3 - Tertiary with Firebird
        print("📡 Adding NAS Device #3: Tertiary Medical NAS...")
        nas3_id = manager.add_nas_device(
            device_name="Tertiary Medical NAS (X: equivalent)",
            ip_address="192.168.1.102",
            manufacturer="Buffalo",
            model="TeraStation",
            default_domain="HOSPITAL",
            admin_username="admin", 
            admin_password="secure_admin_password"
        )
        
        print("\n📁 CONFIGURING SHARED FOLDERS FOR DIFFERENT PROCEDURES")
        print("="*60)
        
        # CT Scans on NAS #1 (DICOM - like your current setup)
        print("🔬 CT Scans (DICOM) on Primary NAS...")
        manager.add_shared_folder(
            nas_device_id=nas1_id,
            procedure_type="CT",
            share_name="ct_scans", 
            share_path="//192.168.1.100/ct_scans",
            username="ct_operator",
            password="ct_secure_2025",
            domain="HOSPITAL",
            protocol="SMB",
            mount_point="/mnt/nas1/ct_scans",
            compression_type="DICOM",
            database_format="DICOM",
            priority=9
        )
        
        # MRI Studies on NAS #1 (DICOM + Firebird)
        print("🧠 MRI Studies (DICOM + Firebird) on Primary NAS...")
        manager.add_shared_folder(
            nas_device_id=nas1_id,
            procedure_type="MRI",
            share_name="mri_studies",
            share_path="//192.168.1.100/mri_studies", 
            username="mri_operator",
            password="mri_secure_2025",
            domain="HOSPITAL",
            protocol="SMB",
            mount_point="/mnt/nas1/mri_studies",
            compression_type="DICOM",
            database_format="FIREBIRD",
            priority=8
        )
        
        # X-Ray Imaging on NAS #2 (JPEG2000 + Firebird - like your other NAS devices)
        print("📷 X-Ray Imaging (JPEG2000 + Firebird) on Secondary NAS...")
        manager.add_shared_folder(
            nas_device_id=nas2_id,
            procedure_type="XRAY",
            share_name="xray_images",
            share_path="//192.168.1.101/xray_images",
            username="xray_operator", 
            password="xray_secure_2025",
            domain="HOSPITAL",
            protocol="SMB",
            mount_point="/mnt/nas2/xray_images",
            compression_type="JPEG2000",
            database_format="FIREBIRD",
            priority=7
        )
        
        # Ultrasound on NAS #2 (Mixed formats)
        print("🔊 Ultrasound (Mixed formats) on Secondary NAS...")
        manager.add_shared_folder(
            nas_device_id=nas2_id,
            procedure_type="ULTRASOUND",
            share_name="ultrasound_studies",
            share_path="//192.168.1.101/ultrasound_studies",
            username="ultrasound_operator",
            password="ultrasound_secure_2025",
            domain="HOSPITAL",
            protocol="SMB", 
            mount_point="/mnt/nas2/ultrasound_studies",
            compression_type="JPEG",
            database_format="SQLITE",
            priority=6
        )
        
        # Digital Pathology on NAS #3 (High-resolution TIFF + Firebird)
        print("🔬 Digital Pathology (TIFF + Firebird) on Tertiary NAS...")
        manager.add_shared_folder(
            nas_device_id=nas3_id,
            procedure_type="PATHOLOGY",
            share_name="pathology_slides",
            share_path="//192.168.1.102/pathology_slides",
            username="pathology_operator",
            password="pathology_secure_2025", 
            domain="HOSPITAL",
            protocol="SMB",
            mount_point="/mnt/nas3/pathology_slides",
            compression_type="TIFF",
            database_format="FIREBIRD",
            priority=8
        )
        
        # Nuclear Medicine on NAS #3 (DICOM)
        print("☢️ Nuclear Medicine (DICOM) on Tertiary NAS...")
        manager.add_shared_folder(
            nas_device_id=nas3_id,
            procedure_type="NUCLEAR",
            share_name="nuclear_medicine",
            share_path="//192.168.1.102/nuclear_medicine",
            username="nuclear_operator",
            password="nuclear_secure_2025",
            domain="HOSPITAL",
            protocol="SMB",
            mount_point="/mnt/nas3/nuclear_medicine", 
            compression_type="DICOM",
            database_format="DICOM",
            priority=7
        )
        
        print("\n📊 SYSTEM OVERVIEW")
        print("="*30)
        
        # Display configuration summary
        devices = manager.get_nas_devices()
        all_folders = manager.get_all_folders()
        procedure_types = manager.get_procedure_types()
        
        print(f"✅ Total NAS Devices: {len(devices)}")
        print(f"✅ Total Shared Folders: {len(all_folders)}")
        print(f"✅ Procedure Types Available: {len(procedure_types)}")
        
        print("\n📋 PROCEDURE DISTRIBUTION:")
        procedure_summary = {}
        for folder in all_folders:
            proc_type = folder['procedure_type']
            if proc_type not in procedure_summary:
                procedure_summary[proc_type] = []
            procedure_summary[proc_type].append(f"{folder['device_name']}")
        
        for proc_type, devices_list in procedure_summary.items():
            print(f"  🔸 {proc_type}: {len(devices_list)} folders across {len(set(devices_list))} devices")
        
        print("\n🔧 TESTING CONNECTION CAPABILITIES")
        print("="*40)
        
        # Test one folder to demonstrate connection testing
        test_folder = all_folders[0] if all_folders else None
        if test_folder:
            print(f"🧪 Testing connection to: {test_folder['share_name']} ({test_folder['procedure_type']})...")
            success, message, details = manager.test_folder_connection(test_folder['folder_id'])
            
            if success:
                print(f"✅ Connection test successful: {message}")
                if 'response_time_ms' in details:
                    print(f"   Response time: {details['response_time_ms']}ms")
            else:
                print(f"⚠️ Connection test failed: {message}")
                print("   Note: This is expected in demo mode without actual NAS devices")
        
        print("\n🌐 WEB INTERFACE ACCESS")
        print("="*30)
        print("📱 Enterprise NAS Configuration UI:")
        print("   http://localhost:5000/api/enterprise-nas/config-ui")
        print()
        print("🔧 API Endpoints Available:")
        print("   GET  /api/enterprise-nas/devices - List all NAS devices")
        print("   POST /api/enterprise-nas/devices - Add new NAS device")
        print("   GET  /api/enterprise-nas/folders - List all shared folders")
        print("   POST /api/enterprise-nas/folders - Add new shared folder")
        print("   POST /api/enterprise-nas/folders/{id}/test - Test folder connection")
        print("   GET  /api/enterprise-nas/stats - Get system statistics")
        
        print("\n🏥 INTEGRATION WITH YOUR EXISTING PACS")
        print("="*45)
        print("✅ Enterprise NAS system integrates with your existing:")
        print("   🔸 Orthanc PACS server")
        print("   🔸 Multi-NAS indexing system") 
        print("   🔸 Patient search capabilities")
        print("   🔸 DICOM file processing")
        print()
        print("🔗 Your 3 NAS devices are now configured for:")
        print("   📁 Different medical procedures")
        print("   🔐 Unique credentials per shared folder")
        print("   🗄️ Multiple database formats (DICOM, Firebird, SQLite)")
        print("   📦 Various compression types (DICOM, JPEG2000, TIFF)")
        print("   🔄 Automatic connection testing and monitoring")
        
        print("\n🚀 NEXT STEPS")
        print("="*20)
        print("1. 🌐 Access the web interface to manage configurations")
        print("2. 🔧 Update connection credentials for your actual NAS devices")
        print("3. 🧪 Test connections to verify network access")
        print("4. 📊 Start indexing medical images across all procedures")
        print("5. 🔍 Use unified patient search across all NAS devices")
        
        print("\n🏆 " + "="*80)
        print("🇿🇦 UBUNTU PATIENT CARE ENTERPRISE NAS SYSTEM READY!")
        print("="*84)
        print()
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importing required modules: {e}")
        print("💡 Make sure you're running from the correct directory")
        return False
    except Exception as e:
        print(f"❌ Error setting up enterprise NAS system: {e}")
        logger.exception("Setup failed")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Enterprise NAS Shared Folders system setup complete!")
        print("🌐 Start the Flask app to access the web interface:")
        print("   python app.py")
    else:
        print("❌ Setup failed. Please check the error messages above.")
        sys.exit(1)