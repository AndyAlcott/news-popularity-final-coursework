"""从标准输入读取 JSON，向标准输出返回预测；Java 与命令行共用。"""
import json
import math
from pathlib import Path
import sys
import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parent


def predict(request):
    schema = json.loads((ROOT / 'models/features.json').read_text(encoding='utf-8'))
    name = request.get('model', 'random_forest')
    if name not in ('decision_tree', 'random_forest'):
        raise ValueError('请选择决策树或随机森林')
    values = request.get('features', {})
    row = []
    for key in schema['features']:
        value = values.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{key} 必须填写有限数值')
        if key == 'global_sentiment_polarity':
            valid = -1 <= value <= 1
        elif key == 'global_subjectivity':
            valid = 0 <= value <= 1
        elif key == 'is_weekend':
            valid = value in (0, 1)
        else:
            valid = value >= 0
        if not valid:
            raise ValueError(f'{key} 超出允许范围')
        if key in ('n_tokens_title', 'n_tokens_content', 'num_hrefs', 'num_imgs', 'num_videos', 'num_keywords') and value != int(value):
            raise ValueError(f'{key} 必须为非负整数')
        row.append(value)
    model = joblib.load(ROOT / 'models' / (name + '.joblib'))
    X = pd.DataFrame([row], columns=schema['features'])
    result = int(model.predict(X)[0])
    return {'model': name, 'prediction': result, 'label': '热门新闻' if result else '普通新闻',
            'probability': float(model.predict_proba(X)[0, 1]), 'threshold': schema['threshold']}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        print(json.dumps(predict(json.load(sys.stdin)), ensure_ascii=False))
    except (ValueError, TypeError, KeyError, FileNotFoundError) as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        sys.exit(1)
