#!/usr/bin/env python3
"""
Simple NAS DICOM Scanner
"""

import os
import sys
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

try:
    import pydicom
    from smbprotocol.connection import Connection
    from smbprotocol.session import Session
    from smbprotocol.tree import TreeConnect
    from smbprotocol.open import Open, CreateDisposition, FileAttributes
    from smbprotocol.file_info import FileStandardInformation
    import uuid
    print("SMB libraries loaded successfully")
except ImportError as e:
    print(f"Missing SMB libraries: {e}")
    print("Install with: pip install pydicom smbprotocol")
    sys.exit(1)

def scan_nas_directory():
    """Scan NAS directory for DICOM files"""
    try:
        # NAS configuration
        server = "155.235.81.155"
        share = "Image Archiving"
        username = "admin"
        password = "CH@R!$M@"
        domain = "WORKGROUP"

        print(f"🔗 Connecting to NAS: {server}\\{share}")
        print(f"Username: {username}")

        # Create connection
        connection = Connection(uuid.uuid4(), server, 445)
        connection.connect()
        print("✅ Connected to server")

        # Create session
        session = Session(connection, username, password, domain)
        session.connect()
        print("✅ Session established")

        # Connect to share
        tree = TreeConnect(session, f"\\\\{server}\\{share}")
        tree.connect()
        print("✅ Connected to share")

        # Scan directory
        print("\n🔍 Scanning for DICOM files...")
        dicom_files = []
        total_files = 0
        total_dirs = 0

        def scan_recursive(path="", depth=0):
            nonlocal total_files, total_dirs, dicom_files

            if depth > 3:  # Limit depth to avoid going too deep
                return

            try:
                indent = "  " * depth
                query_info = tree.query_directory(path, "*")

                for file_info in query_info:
                    if file_info.file_name in ['.', '..']:
                        continue

                    total_files += 1
                    file_path = os.path.join(path, file_info.file_name).replace('\\', '/')

                    # Check if it's a directory
                    if file_info.file_attributes & FileAttributes.FILE_ATTRIBUTE_DIRECTORY:
                        total_dirs += 1
                        print(f"{indent}📁 {file_info.file_name}/")
                        scan_recursive(file_path, depth + 1)
                    else:
                        # Check if it's a potential DICOM file
                        if file_info.file_name.lower().endswith(('.dcm', '.dicom', '.ima')) or '.' not in file_info.file_name:
                            dicom_files.append(file_path)
                            print(f"{indent}📄 {file_info.file_name} (potential DICOM)")

                        if total_files % 100 == 0:
                            print(f"Scanned {total_files} files, found {len(dicom_files)} potential DICOM files")

            except Exception as e:
                print(f"Error scanning {path}: {e}")

        # Start scanning from root
        scan_recursive()

        print("\n📊 SCAN RESULTS:")
        print(f"Total files scanned: {total_files}")
        print(f"Total directories: {total_dirs}")
        print(f"Potential DICOM files: {len(dicom_files)}")

        if dicom_files:
            print("\n📋 Sample DICOM files found:")
            for i, file_path in enumerate(dicom_files[:10]):
                print(f"  {i+1}. {file_path}")
            if len(dicom_files) > 10:
                print(f"  ... and {len(dicom_files) - 10} more")

        # Clean up
        tree.disconnect()
        session.disconnect()
        connection.disconnect()
        print("\n🔌 Disconnected from NAS")

        return dicom_files

    except Exception as e:
        print(f"❌ NAS scan failed: {e}")
        return []

if __name__ == "__main__":
    print("=== NAS DICOM Scanner ===")
    files = scan_nas_directory()
    if files:
        print(f"\n✅ Found {len(files)} potential DICOM files ready for import!")
    else:
        print("\n❌ No DICOM files found")
