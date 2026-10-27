"""验证课程系统的登录、预测、缓存和记录接口。"""
from pathlib import Path
from http.cookiejar import CookieJar
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.error import HTTPError
from urllib.parse import urlencode
import json
import re
import subprocess

root = Path(__file__).resolve().parent
config = (root / 'local.ps1').read_text(encoding='utf-8-sig')
username = re.search(r"NEWS_LOGIN_USER='([^']+)'", config).group(1)
password = re.search(r"NEWS_LOGIN_PASSWORD='([^']+)'", config).group(1)
python = re.search(r"NEWS_PYTHON='([^']+)'", config).group(1)
base = 'http://127.0.0.1:8088'
opener = build_opener(HTTPCookieProcessor(CookieJar()))
token = {}

def call(path, method='GET', data=None, csrf=True):
    headers = {}
    if csrf and token:
        headers[token['header']] = token['token']
    if isinstance(data, dict):
        headers['Content-Type'] = 'application/json'
        data = json.dumps(data).encode()
    try:
        response = opener.open(Request(base + path, data=data, headers=headers, method=method), timeout=40)
        text = response.read()
        return response.status, json.loads(text) if text else None
    except HTTPError as e:
        return e.code, None

def check(name, condition):
    print(name + ': ' + ('通过' if condition else '失败'), flush=True)
    if not condition:
        raise SystemExit(1)

check('未登录访问', call('/api/records')[0] == 401)
token = call('/api/csrf')[1]
wrong = urlencode({'username': username, 'password': 'incorrect'}).encode()
check('错误密码', call('/login', 'POST', wrong)[0] == 401)
token = call('/api/csrf')[1]
login = urlencode({'username': username, 'password': password}).encode()
check('正确登录', call('/login', 'POST', login)[0] == 200)
token = call('/api/csrf')[1]
check('CSRF 校验', call('/api/records/0', 'DELETE', csrf=False)[0] == 403)
check('Redis 缓存读取', call('/api/metrics')[0] == 200 and call('/api/metrics')[1]['cached'])
sample = json.loads((root / 'JavaWeb/python/results/sample_input.json').read_text(encoding='utf8'))
for model in ('decision_tree', 'random_forest'):
    sample['model'] = model
    direct = subprocess.run([python, str(root / 'JavaWeb/python/predict.py')], input=json.dumps(sample), text=True, capture_output=True, encoding='utf8', check=True)
    expected = json.loads(direct.stdout)
    status, actual = call('/api/predict', 'POST', sample)
    check(model + ' 与 Python 一致', status == 200 and actual['label'] == expected['label'] and abs(actual['probability'] - expected['probability']) < 1e-9)
    record_id = actual['id']
    check(model + ' 记录查询', any(x['id'] == record_id for x in call('/api/records')[1]))
    check(model + ' 记录删除', call('/api/records/' + str(record_id), 'DELETE')[1]['deleted'])
invalid = {'model': 'random_forest', 'features': {}}
check('非法输入', call('/api/predict', 'POST', invalid)[0] == 400)
check('退出登录', call('/logout', 'POST')[0] == 200 and call('/api/records')[0] == 401)
