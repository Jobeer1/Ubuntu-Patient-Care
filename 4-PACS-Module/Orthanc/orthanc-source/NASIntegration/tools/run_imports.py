import importlib
import sys
import os
base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base not in sys.path:
    sys.path.insert(0, base)

modules = [
    'backend.device_management',
    'backend.core',
    'backend.core.manager',
    'backend.repository',
    'backend.discovery_service',
    'backend.connectivity_service',
    'backend.models',
    'backend.config'
]

for m in modules:
    try:
        mod = importlib.import_module(m)
        print(m, 'OK ->', getattr(mod, '__file__', None))
    except Exception as e:
        print(m, 'ERROR ->', repr(e))
