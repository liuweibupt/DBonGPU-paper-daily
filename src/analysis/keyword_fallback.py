"""
Keyword-based fallback for Chinese content generation when no API key is available.
Generates brief Chinese summaries using keyword extraction.
"""

import re
from typing import Dict


_ABSTRACT_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9$])')
_ABBREVIATION = re.compile(r'\b(?:[A-Z](?:\.[A-Z])+|e\.g|i\.e|et al|vs|Fig|Eq|Dr)\.$', re.I)
_OUTCOME = re.compile(
    r'\b(?:achiev\w+|outperform\w+|confirmed|improv\w+|reduc\w+|increas\w+|'
    r'filters? out|cuts?|speeds? up|speedup|complet\w+|less energy|'
    r'(?:times?|fold) (?:lower|higher|faster)|(?:evaluations?|results?|experiments?)\b[^.!?]*?\bshow\w*|'
    r'we (?:show|observe|found|find|demonstrate|report))\b',
    re.I,
)
_CONTRIBUTION = re.compile(
    r'\b(?:we (?:(?:also|further|therefore) )?(?:propose|present|design|introduce|'
    r'develop|describe|implement|build|extend|integrate|formulate|identify|define|construct)|'
    r'(?:this (?:paper|work|study|thesis)|here we) (?:proposes?|presents?|introduces?|'
    r'describes?|develops?|explores?)|'
    r'is (?:to our knowledge,? )?(?:the first|an? (?:open-source|novel|new))|'
    r'co-design\w*|recasts?|redesigns?|employs?|'
    r'(?:first|second|third|finally), [^.!?]+)',
    re.I,
)
_MECHANISM = re.compile(
    r'\b(?:maps?|combines?|pairs?|pipelines?|organizes?|derives?|decompos\w+|'
    r'generates?|us(?:e|es|ing)|leverages?|assigns?|introduces?|constructs?|coordinates?|'
    r'mines?|stores?|schedules?|integrates?|removes?|transforms?)\b',
    re.I,
)
_MEASUREMENT = re.compile(
    r'\d+(?:\.\d+)?\s*(?:%|[xX×]|dB\b|[mµn]?s\b|MHz\b|GHz\b|times?\b|seconds?\b|hours?\b)'
)


def abstract_sentences(abstract: str) -> list:
    """Split an abstract while keeping common abbreviations and amounts intact."""
    sentences = []
    for fragment in _ABSTRACT_BOUNDARY.split(' '.join(abstract.split())):
        if sentences and _ABBREVIATION.search(sentences[-1]):
            sentences[-1] += ' ' + fragment
        elif fragment:
            sentences.append(fragment)
    return sentences


def extract_abstract_evidence(sentences: list) -> tuple:
    """Select result and contribution sentences from the paper's abstract."""
    explicit_contributions = [
        index for index, sentence in enumerate(sentences)
        if _CONTRIBUTION.search(sentence)
    ]
    start = explicit_contributions[0] if explicit_contributions else len(sentences) // 3
    outcomes = [
        (
            bool(_MEASUREMENT.search(sentence)),
            index not in explicit_contributions,
            index,
        )
        for index, sentence in enumerate(sentences)
        if index >= start
        and _OUTCOME.search(sentence)
        and (index not in explicit_contributions or _MEASUREMENT.search(sentence))
    ]
    results = sorted(index for _, _, index in sorted(outcomes, reverse=True)[:2])

    contributions = [index for index in explicit_contributions if index not in results]
    if len(contributions) < 2:
        for index in range(start, len(sentences)):
            if index not in results and index not in contributions and _MECHANISM.search(sentences[index]):
                contributions.append(index)
                if len(contributions) == 2:
                    break

    # A short abstract may describe the method in only one sentence.
    return results, sorted(contributions[:3])


# Topic mapping for keyword extraction
TOPIC_MAP = {
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
    'nvlink': 'NVLink 互连',
    'sharp': 'SHARP 集合计算',
    'collective operation': '集合通信',
    'inter-gpu': 'GPU 间通信',
    'all-reduce': 'All-Reduce',
    'in-switch': '交换机内计算',
    'network': '网络',
    'communication': '通信优化',
    'bandwidth': '带宽优化',
    'latency': '延迟优化',
    'throughput': '吞吐量',
}


def generate_fallback_cn(paper: Dict) -> Dict:
    """Generate keyword-based Chinese content for a paper"""
    abstract = paper.get('abstract', '')
    title = paper.get('title', '')
    text = (title + ' ' + abstract).lower()

    # Find matching topics
    matched = []
    for en_term, cn_term in TOPIC_MAP.items():
        if en_term in text:
            if cn_term not in matched:
                matched.append(cn_term)

    if not matched:
        matched = ['硬件架构或数据系统']

    # Generate abstract_cn - simple keyword-based summary
    abstract_cn = f"本文研究{'、'.join(matched[:5])}相关技术。"
    if abstract:
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
