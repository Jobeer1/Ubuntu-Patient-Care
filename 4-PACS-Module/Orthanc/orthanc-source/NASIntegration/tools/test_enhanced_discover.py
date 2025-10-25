import requests
url='http://127.0.0.1:5000/api/nas/enhanced-discover'
payload={'include_arp': False, 'network_range':'10.0.0.0/30', 'timeout':1}
print('POSTing', payload)
r = requests.post(url, json=payload, timeout=10)
print('STATUS', r.status_code)
print(r.text)
