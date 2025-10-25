import sys
import os
# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(__file__))
from app import app

print('Imported app:', app.name)
print('\n--- URL Map Rules ---')
for r in app.url_map.iter_rules():
    if '/indexing/start' in str(r.rule):
        print('Rule:', r.rule, '->', r.endpoint)
print('--- End URL Map ---\n')
import traceback

with app.test_client() as client:
    # Send a JSON body so the endpoint's request.get_json() works
    resp = client.post('/api/nas/indexing/start', json={})
    print('Client POST -> Status code:', resp.status_code)
    try:
        print('Client POST -> JSON:', resp.get_json())
    except Exception as e:
        print('Client POST -> Response data:', resp.data)
        print('Client POST -> Get JSON error:', e)

    # Also call the view function directly inside a request context to capture full traceback
    try:
        from routes.indexing import start_indexing
        with app.test_request_context('/api/nas/indexing/start', method='POST', json={}):
            try:
                print('\nCalling start_indexing() directly to capture traceback...')
                result = start_indexing()
                print('Direct call result:', result)
            except Exception:
                print('Direct call raised exception:')
                traceback.print_exc()
    except Exception as e:
        print('Could not import start_indexing directly:', e)
