"""模拟浏览器路径：走 Vite 代理(5173) 测试 SSE 是否被缓冲。"""
import requests
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
BACK = 'http://127.0.0.1:8001'
PROXY = 'http://127.0.0.1:5173'

# 登录拿 token（直连后端拿 token 即可，token 通用）
t = requests.post(BACK + '/api/auth/login', json={'username': 'demo2026', 'password': 'demo123456'}).json()['access_token']
h = {'Authorization': 'Bearer ' + t, 'Accept': 'text/event-stream'}

start = time.time()
chunks = []
r = requests.post(
    PROXY + '/api/chat/stream',
    headers=h,
    json={'model_id': 'local/full_sft_768', 'message': '你好'},
    stream=True,
    timeout=300,
)
print('HTTP', r.status_code, '| headers:', dict(r.headers))
for chunk in r.iter_content(chunk_size=1):
    if chunk:
        chunks.append((round(time.time() - start, 1), chunk.decode('utf-8', 'ignore')))

# 分析：chunk 到达时间的分布
times = sorted(set(t for t, _ in chunks))
print('chunk 到达时间点(去重):', times[:20], '...' if len(times) > 20 else '')
text = ''.join(c for _, c in chunks)
deltas = [json.loads(l[5:]).get('delta', '') for l in text.split('\n') if l.startswith('data:') and l[5:].strip() not in ('', '[DONE]') and 'delta' in l]
print('收到 delta 数:', len(deltas))
if len(times) <= 2:
    print('>>> 结论：代理把所有数据攒到最后一次性返回 = 被缓冲！')
else:
    print('>>> 结论：数据是分批到达的 = 流式正常')
