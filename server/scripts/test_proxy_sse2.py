"""长回复对比测试：直连8001 vs 代理5173，看 chunk 时间分布差异。"""
import requests
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
BACK = 'http://127.0.0.1:8001'
PROXY = 'http://127.0.0.1:5173'

t = requests.post(BACK + '/api/auth/login', json={'username': 'demo2026', 'password': 'demo123456'}).json()['access_token']
h = {'Authorization': 'Bearer ' + t, 'Accept': 'text/event-stream'}
body = {'model_id': 'local/full_sft_768', 'message': '给我讲一个完整的故事，至少100字'}

for name, base in [('直连后端8001', BACK), ('Vite代理5173', PROXY)]:
    start = time.time()
    times = []
    r = requests.post(base + '/api/chat/stream', headers=h, json=body, stream=True, timeout=300)
    buf = b''
    for chunk in r.iter_content(chunk_size=64):
        if chunk:
            times.append(round(time.time() - start, 1))
            buf += chunk
    uniq = sorted(set(times))
    print(f'{name}: 共{len(times)}个chunk，时间点 {uniq[:15]}{"..." if len(uniq) > 15 else ""}')
    if len(uniq) > 3 and (uniq[-1] - uniq[0]) > 1:
        print('   -> 流式正常（分批到达）')
    else:
        print('   -> 被缓冲（一次性到达）')
