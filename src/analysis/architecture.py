"""Computer architecture ranking and reuse of previously enriched abstracts."""

import json
import re
from pathlib import Path

from analysis.translator import PaperTranslator


ARCHITECTURE_CATEGORY = 'cs.AR'
CHINESE_FIELDS = ('abstract_cn', 'takeaway', 'innovation')
ENRICHMENT_FIELDS = (*CHINESE_FIELDS, 'enrichment_method', 'takeaway_source', 'innovation_source')
ARCHITECTURE_TOPICS = {
    '处理器与微架构': r'processors?|microarchitectures?|risc[- ]?v|instruction sets?|out[- ]of[- ]order|branch prediction|speculative execution',
    '存储与缓存': r'memory hierarch(?:y|ies)|caches?|coherence|dram|sram|hbm|non[- ]volatile memory|memory bandwidth|processing[- ]in[- ]memory',
    'GPU 与异构计算': r'gpus?|simt|warps?|tensor cores?|heterogeneous computing|cuda|vector processors?',
    'AI 加速器与可重构计算': r'accelerators?|systolic arrays?|dataflows?|fpgas?|reconfigurable computing|high[- ]level synthesis',
    '互连与多芯片系统': r'chiplets?|interconnects?|networks?[- ]on[- ]chip|nocs?|multicores?|multi[- ]core|multi[- ]socket',
    '架构评估与硬件效率': r'cycle[- ]accurate|hardware simulation|design space exploration|energy efficiency|power consumption|silicon area|area overhead',
}
TOPIC_PATTERNS = {
    topic: re.compile(rf'\b(?:{terms})\b', re.IGNORECASE)
    for topic, terms in ARCHITECTURE_TOPICS.items()
}


def rank_architecture_papers(papers, limit=100):
    """Rank cs.AR submissions by primary category and distinct topic matches."""
    ranked = []
    for paper in papers:
        title = paper['title']
        abstract = paper['abstract']
        title_topics = {topic for topic, pattern in TOPIC_PATTERNS.items() if pattern.search(title)}
        abstract_topics = {topic for topic, pattern in TOPIC_PATTERNS.items() if pattern.search(abstract)}
        primary = paper.get('primary_category') == ARCHITECTURE_CATEGORY
        points = 4 * primary + 3 * len(title_topics) + len(abstract_topics)
        reasons = ['arXiv 主分类为 cs.AR'] if primary else []
        reasons.extend(topic for topic in TOPIC_PATTERNS if topic in title_topics | abstract_topics)
        ranked.append(dict(paper, score=points / (4 + 4 * len(TOPIC_PATTERNS)), reasons=reasons))
    return sorted(ranked, key=lambda paper: (paper['score'], paper['published_date'], paper['id']), reverse=True)[:limit]


def enrich_architecture_papers(papers, report_directory):
    """Generate Chinese content and reuse it when the original abstract is unchanged."""
    directory = Path(report_directory)
    archives = sorted(directory.glob('????-??-??.json'), reverse=True)[:7]
    cached = {}
    for path in [*archives, directory / 'top100.json']:
        if not path.is_file():
            continue
        for paper in json.loads(path.read_text(encoding='utf-8')):
            if all(paper.get(field) for field in CHINESE_FIELDS):
                cached.setdefault((paper['id'], paper.get('abstract')), paper)

    pending = []
    for paper in papers:
        previous = cached.get((paper['id'], paper.get('abstract')))
        if previous:
            paper.update({field: previous[field] for field in ENRICHMENT_FIELDS if field in previous})
        else:
            pending.append(paper)

    if pending:
        PaperTranslator(topic='计算机体系结构', local_fallback=True).batch_translate(pending)

    missing = [paper['id'] for paper in papers if not all(paper.get(field) for field in CHINESE_FIELDS)]
    if missing:
        raise RuntimeError(f"Chinese architecture summaries unavailable for {', '.join(missing)}")
