import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
b = 'http://127.0.0.1:8001/api'
t = requests.post(b + '/auth/login', json={'username': 'demo2026', 'password': 'demo123456'}).json()['access_token']
h = {'Authorization': 'Bearer ' + t}
r = requests.post(
    b + '/chat/stream',
    headers=h,
    json={'model_id': 'remote/deepseek/deepseek-chat', 'message': '你好，用一句话介绍你自己。'},
    stream=True,
    timeout=120,
)
print('HTTP', r.status_code)
txt = ''
for line in r.iter_lines(decode_unicode=True):
    if line and line.startswith('data:'):
        d = line[5:].strip()
        if d == '[DONE]':
            continue
        try:
            o = json.loads(d)
            txt += o.get('delta', '')
        except Exception:
            pass
print('DeepSeek 回复:', txt[:100])

# 确认消息写入了 MySQL
conv_id = requests.get(b + '/conversations', headers=h).json()[0]['id']
msgs = requests.get(b + f'/conversations/{conv_id}/messages', headers=h).json()
print('MySQL 中该会话消息数:', len(msgs), '| 最后一条角色:', msgs[-1]['role'])
