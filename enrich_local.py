#!/usr/bin/env python3
"""
Local script to enrich existing paper JSON data with Chinese translations,
AI takeaway and innovation points.

This script reads existing JSON files, uses a keyword-based fallback
to generate Chinese content, and regenerates all HTML pages.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from display.html_display import HTMLDisplay


def generate_fallback_cn(paper: dict) -> dict:
    """Generate keyword-based Chinese content for a paper"""
    abstract = paper.get('abstract', '')
    title = paper.get('title', '')
    text = (title + ' ' + abstract).lower()

    # Topic mapping for keyword extraction
    topic_map = {
        'gpu database': 'GPU 数据库',
        'gpu-accelerated': 'GPU 加速',
        'gpu query': 'GPU 查询处理',
        'gpu hash join': 'GPU 哈希连接',
        'gpu sort': 'GPU 排序',
        'gpu index': 'GPU 索引',
        'gpu storage': 'GPU 存储',
        'gpu transaction': 'GPU 事务处理',
        'gpu in-memory': 'GPU 内存数据库',
        'gpu olap': 'GPU OLAP 分析',
        'gpu oltp': 'GPU OLTP 处理',
        'gpu columnar': 'GPU 列式存储',
        'cuda database': 'CUDA 数据库',
        'gpu analytics': 'GPU 分析处理',
        'gpu sql': 'GPU SQL 处理',
        'gpu data processing': 'GPU 数据处理',
        'gpu memory': 'GPU 内存管理',
        'gpu parallel': 'GPU 并行计算',
        'gpu compute': 'GPU 计算',
        'gpu acceleration': 'GPU 加速',
        'gpu scheduling': 'GPU 调度',
        'gpu kernel': 'GPU 核函数',
        'gpu cache': 'GPU 缓存',
        'cuda': 'CUDA',
        'private information retrieval': '隐私信息检索',
        'pir': '隐私信息检索',
        'tensor parallelism': '张量并行',
        'llm inference': '大模型推理',
        'llm training': '大模型训练',
        'query processing': '查询处理',
        'query optimization': '查询优化',
        'join algorithm': '连接算法',
        'hash table': '哈希表',
        'b-tree': 'B 树索引',
        'column store': '列式存储',
        'in-memory': '内存数据库',
        'vectorized': '向量化执行',
        'simd': 'SIMD 并行',
        'parallel database': '并行数据库',
        'data processing': '数据处理',
        'olap': 'OLAP',
        'oltp': 'OLTP',
        'data compression': '数据压缩',
        'nearest neighbor': '近邻搜索',
        'vector database': '向量数据库',
        'rdma': 'RDMA 网络',
        'nvme': 'NVMe 存储',
        'distributed query': '分布式查询',
        'analytical query': '分析查询',
        'join order': '连接顺序优化',
        'predicate transfer': '谓词迁移',
        'tensor computation': '张量计算',
        'pytorch': 'PyTorch',
        'heterogeneous': '异构计算',
        'multi-gpu': '多 GPU',
        'data placement': '数据放置',
        'caching': '缓存',
        'scan': '扫描',
        'aggregation': '聚合',
        'sorting': '排序',
        'storage engine': '存储引擎',
        'database system': '数据库系统',
    }

    # Find matching topics
    matched = []
    for en_term, cn_term in topic_map.items():
        if en_term in text:
            if cn_term not in matched:
                matched.append(cn_term)

    if not matched:
        matched = ['硬件架构或数据系统']

    # Generate abstract_cn - translate key sentences
    abstract_cn = f"本文研究{'、'.join(matched[:5])}相关技术。"
    if abstract:
        # Extract first two sentences as key content
        sentences = abstract.replace('! ', '. ').replace('? ', '. ').split('. ')
        key_sentences = sentences[:2]
        key_text = '. '.join(key_sentences)
        if len(key_text) > 300:
            key_text = key_text[:300] + '...'
        abstract_cn += f"\n\n核心内容：{key_text}。"

    # Generate takeaway
    takeaway = f"本文聚焦{'、'.join(matched[:3])}，"
    score = paper.get('score', 0)
    if score >= 0.7:
        takeaway += '与 GPU 数据库主题高度相关，提供了该领域的直接技术贡献。'
    elif score >= 0.5:
        takeaway += '与 GPU 数据库主题中等相关，可能提供间接参考价值。'
    else:
        takeaway += '涉及相关技术领域，对理解系统整体架构有参考意义。'

    # Generate innovation
    innovations = []
    if 'gpu' in text or 'cuda' in text:
        innovations.append('利用 GPU 并行计算能力加速数据处理')
    if 'query' in text:
        innovations.append('优化查询处理流程')
    if 'memory' in text:
        innovations.append('改进内存管理策略')
    if 'distributed' in text or 'multi-gpu' in text:
        innovations.append('支持分布式/多 GPU 扩展')
    if 'tensor' in text or 'pytorch' in text:
        innovations.append('基于张量计算运行时构建查询引擎')
    if 'heterogeneous' in text:
        innovations.append('异构 CPU-GPU 协同执行策略')
    if 'caching' in text or 'cache' in text:
        innovations.append('智能缓存与数据放置优化')
    if not innovations:
        innovations.append('针对特定场景提出优化方案')

    innovation = '；'.join([f'{i+1}. {inv}' for i, inv in enumerate(innovations[:4])])

    paper['abstract_cn'] = abstract_cn
    paper['takeaway'] = takeaway
    paper['innovation'] = innovation

    return paper


def enrich_json_file(json_path: str) -> list:
    """Read a JSON file, enrich papers with Chinese content, save back"""
    if not os.path.exists(json_path):
        print(f"  File not found: {json_path}")
        return []

    with open(json_path, 'r', encoding='utf-8') as f:
        papers = json.load(f)

    if not papers:
        print(f"  No papers in {json_path}")
        return papers

    print(f"  Enriching {len(papers)} papers in {json_path}...")

    for paper in papers:
        if not paper.get('abstract_cn'):
            generate_fallback_cn(paper)

    # Save enriched JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(papers, f, ensure_ascii=False, indent=2, default=str)

    return papers


def main():
    docs_dir = os.path.join(os.path.dirname(__file__), 'docs')

    # Enrich and regenerate each JSON file
    html_display = HTMLDisplay()

    # Process daily pages
    for filename in sorted(os.listdir(docs_dir)):
        if filename.startswith('20') and filename.endswith('.json'):
            date = filename.replace('.json', '')
            json_path = os.path.join(docs_dir, filename)
            print(f"\nProcessing daily page: {date}")

            papers = enrich_json_file(json_path)

            if papers:
                # Regenerate HTML
                all_dates = []
                for f in os.listdir(docs_dir):
                    if f.startswith('20') and f.endswith('.html') and f != 'top100.html':
                        try:
                            from datetime import datetime
                            d = f.replace('.html', '')
                            datetime.strptime(d, '%Y-%m-%d')
                            all_dates.append(d)
                        except ValueError:
                            continue
                all_dates = sorted(set(all_dates))
                if date not in all_dates:
                    all_dates.append(date)

                html = html_display.generate_daily_html(papers, date, all_dates)

                # Save as date page
                html_path = os.path.join(docs_dir, f'{date}.html')
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"  Saved {html_path}")

    # Also regenerate index.html from the latest date
    date_files = [f for f in os.listdir(docs_dir) if f.startswith('20') and f.endswith('.json')]
    if date_files:
        latest_date = sorted([f.replace('.json', '') for f in date_files])[-1]
        json_path = os.path.join(docs_dir, f'{latest_date}.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            papers = json.load(f)

        all_dates = []
        for fn in os.listdir(docs_dir):
            if fn.startswith('20') and fn.endswith('.html') and fn != 'top100.html':
                try:
                    from datetime import datetime
                    d = fn.replace('.html', '')
                    datetime.strptime(d, '%Y-%m-%d')
                    all_dates.append(d)
                except ValueError:
                    continue
        all_dates = sorted(set(all_dates))

        html = html_display.generate_daily_html(papers, latest_date, all_dates)
        index_path = os.path.join(docs_dir, 'index.html')
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\nRegenerated index.html from {latest_date}")

    # Process top100
    top100_json = os.path.join(docs_dir, 'top100.json')
    if os.path.exists(top100_json):
        print(f"\nProcessing Top 100...")
        papers = enrich_json_file(top100_json)
        if papers:
            html = html_display.generate_top100_html(papers)
            top100_path = os.path.join(docs_dir, 'top100.html')
            with open(top100_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  Saved {top100_path}")

    # Process classics (already has full Chinese content)
    classics_json = os.path.join(docs_dir, 'classics.json')
    if os.path.exists(classics_json):
        print(f"\nProcessing Classics...")
        with open(classics_json, 'r', encoding='utf-8') as f:
            papers = json.load(f)
        html = html_display.generate_classics_html(papers)
        classics_path = os.path.join(docs_dir, 'classics.html')
        with open(classics_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  Saved {classics_path}")

    print("\nDone! All pages enriched and regenerated.")


if __name__ == '__main__':
    main()
