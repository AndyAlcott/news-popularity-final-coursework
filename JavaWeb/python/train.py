"""数据来源：UCI Online News Popularity，CC BY 4.0。
https://archive.ics.uci.edu/dataset/332/online+news+popularity
运行 python train.py。
"""
import hashlib
import json
import os
from pathlib import Path
import time
import zipfile
import urllib.request

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             classification_report, confusion_matrix)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent
FEATURES = ['n_tokens_title', 'n_tokens_content', 'num_hrefs', 'num_imgs', 'num_videos',
            'average_token_length', 'num_keywords', 'global_subjectivity',
            'global_sentiment_polarity', 'is_weekend']
LABELS = ['标题词数', '正文词数', '链接数', '图片数', '视频数', '平均词长',
          '关键词数', '主观性', '情感极性', '是否周末']
OUT = ROOT / 'results'
MODELS = ROOT / 'models'


def checkpoint(name):
    # 可选的外部同步文件不改变正常输出，默认连续运行。
    gate = os.environ.get('NEWS_GATE')
    if gate:
        p = Path(gate)
        p.with_suffix('.ready').write_text(name, encoding='utf-8')
        while not p.exists():
            time.sleep(.3)
        p.unlink()
        p.with_suffix('.ready').unlink(missing_ok=True)


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def score(y, pred):
    return dict(accuracy=accuracy_score(y, pred), precision=precision_score(y, pred, zero_division=0),
                recall=recall_score(y, pred, zero_division=0), f1=f1_score(y, pred, zero_division=0))


def figure(name, explanation):
    plt.tight_layout()
    plt.savefig(OUT / (name + '.png'), dpi=160, bbox_inches='tight')
    plt.close()
    NOTES.append((name, explanation))


def main():
    OUT.mkdir(exist_ok=True)
    MODELS.mkdir(exist_ok=True)
    data_dir = ROOT / 'data'
    data_dir.mkdir(exist_ok=True)
    csv = data_dir / 'OnlineNewsPopularity.csv'
    if not csv.exists():
        archive = data_dir / 'online_news_popularity.zip'
        urllib.request.urlretrieve('https://archive.ics.uci.edu/static/public/332/online+news+popularity.zip', archive)
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if name.endswith(('.csv', '.names')):
                    (data_dir / Path(name).name).write_bytes(z.read(name))
    df = pd.read_csv(csv)
    df.columns = df.columns.str.strip()
    original_rows = len(df)
    duplicate_urls = int(df.url.duplicated().sum())
    df = df.drop_duplicates('url').reset_index(drop=True)
    raw = df[FEATURES].replace([np.inf, -np.inf], np.nan)
    y = (df.shares >= 1400).astype(int)
    train, test = train_test_split(np.arange(len(df)), test_size=.2, stratify=y, random_state=42)
    Xtr, Xte, ytr, yte = raw.iloc[train], raw.iloc[test], y.iloc[train], y.iloc[test]
    np.savez(OUT / 'split_indices.npz', train=train, test=test)
    raw.describe().to_csv(OUT / 'descriptive_statistics.csv', encoding='utf-8-sig')
    # IQR 只识别长尾，不把高热度新闻或较长文章直接当作错误删除。
    q1, q3 = Xtr.quantile(.25), Xtr.quantile(.75)
    iqr = q3 - q1
    abnormal = ((raw < q1 - 1.5 * iqr) | (raw > q3 + 1.5 * iqr)).sum()
    abnormal = abnormal.drop('is_weekend')  # 二元变量不使用连续数值的 IQR 异常规则。
    quality = {'source': 'https://archive.ics.uci.edu/dataset/332/online+news+popularity',
               'sha256': hashlib.sha256(csv.read_bytes()).hexdigest(),
               'original_rows': original_rows, 'rows': len(df), 'duplicate_urls': duplicate_urls,
               'missing': raw.isna().sum().to_dict(), 'iqr_outliers': abnormal.to_dict(),
               'train_rows': len(train), 'test_rows': len(test),
               'class_counts': y.value_counts().sort_index().to_dict(), 'threshold': 1400}
    save_json(OUT / 'data_quality.json', quality)
    print('Dataset: UCI Online News Popularity / CC BY 4.0')
    print(f'Rows={len(df)}, features={len(FEATURES)}, missing={raw.isna().sum().sum()}, duplicate URLs={duplicate_urls}')
    print(f'Train={len(train)}, test={len(test)}, seed=42, positive: shares >= 1400')
    print('Class counts:', y.value_counts().sort_index().to_dict())
    print('IQR outlier counts (bounds fitted on training data):')
    print(abnormal.to_string())
    checkpoint('Data reading and quality checks completed.')

    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    counts = y.value_counts().sort_index()
    plt.figure(figsize=(6.5, 4))
    ax = counts.set_axis(['普通新闻', '热门新闻']).plot.bar(color='#416b88', rot=0)
    ax.set(ylabel='新闻数（篇）', title='新闻热度类别分布：分享次数阈值为 1400')
    for i, n in enumerate(counts):
        ax.text(i, n, f'{n:,}', ha='center', va='bottom')
    plt.ylim(0, counts.max() * 1.14)
    figure('01_class_distribution', f'普通新闻 {counts.iloc[0]:,} 篇，热门新闻 {counts.iloc[1]:,} 篇。按固定阈值分组，分层抽样保留类别比例。')
    fig, axes = plt.subplots(1, 3, figsize=(10, 4))
    for ax, col, label in zip(axes, ['n_tokens_content', 'num_imgs', 'num_hrefs'], ['正文词数', '图片数', '链接数']):
        sns.boxplot(y=raw[col], ax=ax, color='#c1d4df', fliersize=1)
        ax.set(title=label, ylabel='数值')
    figure('02_boxplots', '箱体表示中间 50% 的观测，须外点为 IQR 规则识别的长尾。长正文、多图片和多链接不必然是错误，本实验保留这些样本。')
    plt.figure(figsize=(10, 8))
    corr = raw.rename(columns=dict(zip(FEATURES, LABELS))).corr()
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='Blues', vmin=-1, vmax=1, square=True)
    figure('03_correlation', '单元格表示特征间 Pearson 相关系数，色阶固定为 −1 至 1。相关性描述线性关系，不代表对新闻热度的因果影响。')
    print('Saved class distribution, boxplots and feature correlation heatmap.')
    print('Source rows, missing values and descriptive statistics saved in results/.')
    checkpoint('Exploratory data analysis completed.')

    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    estimators = {
        'decision_tree': (DecisionTreeClassifier(random_state=42),
                          {'model__max_depth': [4, 8, 12], 'model__min_samples_leaf': [10, 30]}),
        'random_forest': (RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=1),
                          {'model__max_depth': [8, 16], 'model__min_samples_leaf': [5, 15]})}
    comparisons = []
    fitted = {}
    metrics = {}
    for name, (model, grid) in estimators.items():
        for scaled in [False, True]:
            pipe = Pipeline([('imputer', SimpleImputer(strategy='median')),
                             ('scaler', StandardScaler() if scaled else 'passthrough'),
                             ('model', clone(model))])
            search = GridSearchCV(pipe, grid, scoring='f1', cv=cv, n_jobs=2, return_train_score=True)
            search.fit(Xtr, ytr)
            results = pd.DataFrame(search.cv_results_)
            results.to_csv(OUT / f'{name}_{"scaled" if scaled else "raw"}_cv.csv', index=False, encoding='utf-8-sig')
            comparisons.append({'model': name, 'preprocessing': 'median+standard' if scaled else 'median',
                                'cv_f1': search.best_score_, 'params': search.best_params_})
            print(name, 'scaled=' + str(scaled), 'best CV F1=', round(search.best_score_, 4), search.best_params_, flush=True)
            # 固定交付标准化版本；对照仅用交叉验证评价，不以测试集选择方案。
            if scaled:
                fitted[name] = search.best_estimator_
                metrics[name] = {'cv_f1': search.best_score_, 'params': search.best_params_}
    pd.DataFrame(comparisons).to_csv(OUT / 'preprocessing_comparison.csv', index=False, encoding='utf-8-sig')
    print('Tree models are almost invariant to monotonic scaling; no improvement is assumed.')
    checkpoint('Preprocessing comparison and parameter search completed.')

    for name, pipe in fitted.items():
        pred = pipe.predict(Xte)
        metrics[name].update(score(yte, pred))
        metrics[name]['confusion_matrix'] = confusion_matrix(yte, pred).tolist()
        metrics[name]['report'] = classification_report(yte, pred, target_names=['ordinary', 'popular'], output_dict=True, zero_division=0)
        joblib.dump(pipe, MODELS / (name + '.joblib'))
        plt.figure(figsize=(5.5, 4))
        sns.heatmap(confusion_matrix(yte, pred), annot=True, fmt='d', cmap='Blues', cbar=False,
                    xticklabels=['普通', '热门'], yticklabels=['普通', '热门'])
        plt.xlabel('预测类别'); plt.ylabel('实际类别')
        plt.title('决策树混淆矩阵' if name == 'decision_tree' else '随机森林混淆矩阵')
        cm = confusion_matrix(yte, pred)
        figure('04_confusion_' + name, f'行是实际类别，列是预测类别。正确预测 {cm.trace():,}/{cm.sum():,} 篇；普通误判为热门 {cm[0,1]:,} 篇，热门漏判 {cm[1,0]:,} 篇。')
        print('\n' + name)
        print(classification_report(yte, pred, target_names=['ordinary', 'popular'], digits=4, zero_division=0))
        print('Accuracy / Precision / Recall / F1:', {k: round(metrics[name][k], 4) for k in ['accuracy', 'precision', 'recall', 'f1']})
        checkpoint(name)
    imp = pd.Series(fitted['random_forest'].named_steps['model'].feature_importances_, index=LABELS).sort_values()
    plt.figure(figsize=(8, 5))
    imp.plot.barh(color='#416b88')
    plt.xlabel('不纯度重要性'); plt.title('随机森林特征重要性')
    figure('05_feature_importance', f'按随机森林分裂不纯度下降量排序，{imp.index[-1]} 在本模型中的重要性最高。该指标可能偏好连续特征，不应解释为因果贡献。')
    save_json(OUT / 'metrics.json', metrics)
    save_json(MODELS / 'features.json', {'features': FEATURES, 'labels': LABELS, 'threshold': 1400})
    sample = {c: float(Xte.iloc[0][c]) for c in FEATURES}
    save_json(OUT / 'sample_input.json', {'model': 'random_forest', 'features': sample})
    plt.figure(figsize=(7, 4))
    for name, marker, label in [('decision_tree', 'o', '决策树'), ('random_forest', 's', '随机森林')]:
        plt.plot(['准确率', '精确率', '召回率', 'F1'], [metrics[name][k] for k in ['accuracy','precision','recall','f1']], marker=marker, label=label)
    plt.ylim(0, 1); plt.ylabel('指标值'); plt.title('相同测试集上的模型指标对比'); plt.legend()
    figure('06_model_comparison', '横轴为不同评价指标，连线仅用于对照同一模型，不表示时间趋势。热门新闻为正类，F1 是精确率与召回率的调和平均。')
    (OUT / '图表解读.md').write_text('\n\n'.join(f'### {name}\n\n![{name}]({name}.png)\n\n{text}' for name,text in NOTES), encoding='utf-8')
    print('\nModel pipelines and results saved. Test set was not used for parameter search.')
    checkpoint('Model evaluation completed.')


if __name__ == '__main__':
    NOTES = []
    main()
