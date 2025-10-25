import requests

LOGIN_URL = 'http://127.0.0.1:5000/api/auth/login'
VIEWER_URL = 'http://127.0.0.1:5000/dicom-viewer'

s = requests.Session()
resp = s.post(LOGIN_URL, json={'username':'admin','password':'admin','user_type':'admin'})
print('login', resp.status_code, resp.text[:200])
resp2 = s.get(VIEWER_URL)
print('viewer', resp2.status_code)
print(resp2.text[:400])
