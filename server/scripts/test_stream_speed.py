import requests
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
b = 'http://127.0.0.1:8001/api'
t = requests.post(b + '/auth/login', json={'username': 'demo2026', 'password': 'demo123456'}).json()['access_token']
h = {'Authorization': 'Bearer ' + t}

start = time.time()
first_token_at = None
txt = ''
r = requests.post(
    b + '/chat/stream',
    headers=h,
    json={'model_id': 'local/full_sft_768', 'message': '你是谁？'},
    stream=True,
    timeout=300,
)
for line in r.iter_lines(decode_unicode=True):
    if line and line.startswith('data:'):
        d = line[5:].strip()
        if d == '[DONE]':
            continue
        try:
            o = json.loads(d)
            piece = o.get('delta', '')
            if piece and first_token_at is None:
                first_token_at = time.time()
            txt += piece
        except Exception:
            pass

total = time.time() - start
print(f'首个字出现耗时: {first_token_at - start:.1f}s')
print(f'整段生成耗时: {total:.1f}s')
print(f'回复({len(txt)}字): {txt[:80]}')
