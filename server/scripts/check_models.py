import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
b = 'http://127.0.0.1:8001/api'
t = requests.post(b + '/auth/login', json={'username': 'demo2026', 'password': 'demo123456'}).json()['access_token']
h = {'Authorization': 'Bearer ' + t}
for m in requests.get(b + '/models', headers=h).json():
    print(f"{m['id']}  {m['name']}  available={m['is_available']}")
