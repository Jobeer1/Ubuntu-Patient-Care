#!/usr/bin/env python3
"""
Test script for Onboarding Collection Tool

Quick test to verify OCT is working.
"""

import sys
from pathlib import Path
import subprocess

def test_oct():
    """Test OCT with example signature"""
    print("=" * 60)
    print("TESTING ONBOARDING COLLECTION TOOL")
    print("=" * 60)
    
    # Check if owner signature exists
    sig_file = Path(__file__).parent / "owner_sig_example.json"
    if not sig_file.exists():
        print(f"❌ Owner signature file not found: {sig_file}")
        return False
    
    print(f"✅ Owner signature file found: {sig_file}")
    
    # Run OCT
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "collect_credentials.py"),
        "--owner-sig", str(sig_file),
        "--target-subnet", "192.168.1.0/24",
        "--mode", "test",
        "--output-dir", "./test_output"
    ]
    
    print(f"\nRunning: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✅ OCT TEST PASSED!")
            return True
        else:
            print(f"\n❌ OCT TEST FAILED (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_oct()
    sys.exit(0 if success else 1)
