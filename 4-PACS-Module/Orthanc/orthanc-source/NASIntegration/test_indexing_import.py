"""
Quick test to verify the indexing route imports correctly after the fix
"""
import sys
import os

# Add backend to path
backend_path = r"c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend"
sys.path.insert(0, backend_path)

print("=" * 60)
print("TESTING INDEXING ROUTE IMPORT")
print("=" * 60)

try:
    from routes.indexing import indexing_bp, start_indexing
    print("\n✅ Successfully imported indexing blueprint")
    print(f"   Blueprint name: {indexing_bp.name}")
    print(f"   start_indexing function: {start_indexing}")
    
    # Check if the function can be inspected (no syntax errors)
    import inspect
    sig = inspect.signature(start_indexing)
    print(f"   Function signature: {sig}")
    
    print("\n✅ No syntax or import errors detected!")
    print("\nThe indexing route is ready to use.")
    
except Exception as e:
    print(f"\n❌ Failed to import indexing route: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("=" * 60)
