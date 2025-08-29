import requests

url = 'http://127.0.0.1:5000/dicom-viewer'
try:
    r = requests.get(url, timeout=5)
    print(r.status_code)
    print(r.headers.get('Content-Type'))
    print(r.text[:400])
except Exception as e:
    print('ERROR', e)
