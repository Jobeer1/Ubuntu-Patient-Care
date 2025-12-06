import requests

URL = 'http://127.0.0.1:5000/device-discovery'
LOGIN = 'http://127.0.0.1:5000/api/auth/login'

# Unauthenticated
r = requests.get(URL)
print('unauth status', r.status_code)

# Authenticated
s = requests.Session()
login = s.post(LOGIN, json={'username':'admin','password':'admin','user_type':'admin'})
print('login', login.status_code)
r2 = s.get(URL)
print('auth status', r2.status_code)
print(r2.text[:400])
