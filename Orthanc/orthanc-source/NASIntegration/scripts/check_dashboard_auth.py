import requests
s = requests.Session()
login = s.post('http://127.0.0.1:5000/api/auth/login', json={'username':'admin','password':'admin','user_type':'admin'})
print('login', login.status_code)
resp = s.get('http://127.0.0.1:5000/')
print('status', resp.status_code)
text = resp.text
print('device_count', text.count('Device Management'))
# Show surrounding area after NAS Integration to verify placement
idx = text.find('📁 NAS Integration')
if idx!=-1:
    print(text[idx:idx+400])
else:
    print('NAS not found')
