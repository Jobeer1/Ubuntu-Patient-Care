#!/usr/bin/env python3
"""
Test script for dashboard routes
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

try:
    from core.routes import core_bp
    from flask import Flask
    
    app = Flask(__name__)
    app.register_blueprint(core_bp)
    
    print('✅ Routes loaded successfully')
    print('Available routes:')
    for rule in app.url_map.iter_rules():
        print(f'  {rule.rule} -> {rule.endpoint}')
        
    print('\n✅ Dashboard routes test completed successfully')
    
except Exception as e:
    print(f'❌ Error loading routes: {e}')
    import traceback
    traceback.print_exc()