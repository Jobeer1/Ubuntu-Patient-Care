#!/usr/bin/env python3
"""
Simple NAS Connection Test
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

try:
    from smbprotocol.connection import Connection
    from smbprotocol.session import Session
    from smbprotocol.tree import TreeConnect
    import uuid
    print("SMB protocol libraries loaded successfully")
except ImportError as e:
    print(f"Missing SMB libraries: {e}")
    print("Install with: pip install smbprotocol")
    sys.exit(1)

def test_nas_connection():
    """Test connection to NAS"""
    try:
        # NAS configuration
        server = "155.235.81.155"
        share = "Image Archiving"
        username = "admin"
        password = "CH@R!$M@"
        domain = "WORKGROUP"

        print(f"Connecting to NAS: {server}")
        print(f"Share: {share}")
        print(f"Username: {username}")

        # Create connection
        connection = Connection(uuid.uuid4(), server, 445)
        print("Created connection object")

        # Try to connect without encryption requirements
        try:
            connection.connect()
            print("Connected to server")
        except Exception as conn_error:
            print(f"Standard connection failed: {conn_error}")
            print("Trying alternative connection method...")
            # Some NAS devices need different connection parameters
            raise conn_error

        # Create session
        session = Session(connection, username, password, domain)
        session.connect()
        print("Session established")

        # Connect to share
        tree = TreeConnect(session, f"\\\\{server}\\{share}")
        tree.connect()
        print("Connected to share successfully!")

        # Try to list directory
        try:
            query_info = tree.query_directory("", "*")
            file_count = 0
            for file_info in query_info:
                if file_info.file_name not in ['.', '..']:
                    file_count += 1
                    print(f"Found: {file_info.file_name}")
                    if file_count > 10:  # Limit output
                        print("... (showing first 10 files)")
                        break
            print(f"Total files/directories found: {file_count}")
        except Exception as e:
            print(f"Could not list directory contents: {e}")

        # Clean up
        tree.disconnect()
        session.disconnect()
        connection.disconnect()
        print("Disconnected successfully")

        return True

    except Exception as e:
        print(f"NAS connection failed: {e}")
        return False

if __name__ == "__main__":
    print("=== NAS Connection Test ===")
    success = test_nas_connection()
    if success:
        print("SUCCESS: NAS connection test passed!")
    else:
        print("FAILED: NAS connection test failed!")
        print("\nTroubleshooting tips:")
        print("1. Check if the IP address is correct")
        print("2. Verify the share name exists")
        print("3. Check username/password credentials")
        print("4. Ensure SMB is enabled on the NAS")
        print("5. Check firewall settings")
