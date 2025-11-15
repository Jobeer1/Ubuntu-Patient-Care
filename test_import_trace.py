#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# DON'T add backend path yet - let's see what imports naturally

# First, try to import from backend.services like nas_core.py does
try:
    from backend.services import nas_patient_search as _ns
    search_service_func = _ns.search_patient_comprehensive
    print(f"✅ Successfully imported: backend.services.nas_patient_search.search_patient_comprehensive")
    print(f"   File: {search_service_func.__code__.co_filename}")
    print(f"   Line: {search_service_func.__code__.co_firstlineno}")
except Exception as e:
    print(f"❌ Failed to import backend.services.nas_patient_search: {e}")
    search_service_func = None

if not search_service_func:
    try:
        from services import nas_patient_search as _ns2
        search_service_func = _ns2.search_patient_comprehensive
        print(f"✅ Successfully imported: services.nas_patient_search.search_patient_comprehensive")
    except Exception as e:
        print(f"❌ Failed to import services.nas_patient_search: {e}")

if not search_service_func:
    try:
        from backend.services import search_patient_comprehensive as _fn
        search_service_func = _fn
        print(f"✅ Successfully imported: backend.services.search_patient_comprehensive")
        print(f"   File: {search_service_func.__code__.co_filename}")
        print(f"   Line: {search_service_func.__code__.co_firstlineno}")
    except Exception as e:
        print(f"❌ Failed to import backend.services.search_patient_comprehensive: {e}")
