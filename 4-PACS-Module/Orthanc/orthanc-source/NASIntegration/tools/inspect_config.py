import sys
import os
import importlib

# Add NASIntegration to sys.path
base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base not in sys.path:
    sys.path.insert(0, base)

print('sys.path[0]=', sys.path[0])

# Try importing backend.config
try:
    cfg = importlib.import_module('backend.config')
    print('Imported backend.config from:', getattr(cfg, '__file__', None))
    for name in ('DB_PATH', 'ARP_COMMAND_TIMEOUT', 'PING_TIMEOUT', 'SOCKET_TIMEOUT'):
        print(name, 'present:', hasattr(cfg, name), 'value:', getattr(cfg, name, None))
    print('\nbackend.config dir():')
    print(sorted([n for n in dir(cfg) if n.isupper()]))
except Exception as e:
    print('Importing backend.config FAILED:', repr(e))

# Show any modules named 'config' or 'backend.config' in sys.modules
print('\nModules in sys.modules matching "config":')
for mname in sorted(m for m in sys.modules if 'config' in m):
    mo = sys.modules[mname]
    print(mname, '->', getattr(mo, '__file__', None))

# Search the NASIntegration tree for files named config.py
print('\nSearching filesystem for config.py files under:', base)
matches = []
for root, dirs, files in os.walk(base):
    for fn in files:
        if fn == 'config.py':
            matches.append(os.path.join(root, fn))

print('Found', len(matches), 'config.py files:')
for p in matches:
    print(' -', p)

# Also search one level up (workspace) for other config.py
workspace_root = os.path.abspath(os.path.join(base, '..', '..'))
print('\nSearching workspace root for config.py under:', workspace_root)
for root, dirs, files in os.walk(workspace_root):
    for fn in files:
        if fn == 'config.py':
            print(' *', os.path.join(root, fn))

print('\nDone')
