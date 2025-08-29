#!/usr/bin/env python3
"""
Emergency Test - Quick check if STT file handling is fixed
"""

import os
import tempfile
import sys

def test_file_access():
    """Test Windows temp file creation and access"""
    print("🔧 Testing Windows temp file access...")
    
    try:
        # Test our new approach
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav', prefix='test_')
        os.close(temp_fd)  # Close immediately
        
        # Write test data
        test_data = b'TEST_AUDIO_DATA'
        with open(temp_path, 'wb') as f:
            f.write(test_data)
        
        # Verify accessibility
        if os.path.exists(temp_path) and os.access(temp_path, os.R_OK):
            print("✅ Temp file creation and access: WORKING")
            
            # Verify reading
            with open(temp_path, 'rb') as f:
                read_data = f.read()
            
            if read_data == test_data:
                print("✅ File read/write: WORKING")
                result = True
            else:
                print("❌ File read/write: FAILED")
                result = False
        else:
            print("❌ File access: FAILED")
            result = False
        
        # Cleanup
        try:
            os.unlink(temp_path)
            print("✅ File cleanup: SUCCESS")
        except:
            print("⚠️  File cleanup: WARNING")
        
        return result
        
    except Exception as e:
        print(f"❌ Temp file test failed: {e}")
        return False

def main():
    """Run emergency test"""
    print("🚨 Emergency STT Fix Test")
    print("=" * 30)
    
    if test_file_access():
        print("\n🎉 File handling should now work!")
        print("💡 Restart the app and test voice dictation")
        return 0
    else:
        print("\n⚠️  File handling still has issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
