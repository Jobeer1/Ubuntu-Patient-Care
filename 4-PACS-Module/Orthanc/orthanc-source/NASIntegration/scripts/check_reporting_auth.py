import requests

LOGIN_URL = 'http://127.0.0.1:5000/api/auth/login'
REPORT_URL = 'http://127.0.0.1:5000/reporting'

s = requests.Session()
resp = s.post(LOGIN_URL, json={'username':'admin','password':'admin','user_type':'admin'})
print('login', resp.status_code)
resp2 = s.get(REPORT_URL)
print('reporting', resp2.status_code)
print(resp2.text[:400])
