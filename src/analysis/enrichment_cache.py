"""Reuse paper translations from earlier reports."""

import json
from pathlib import Path

from .translator import CHINESE_FIELDS, CODEX_METHOD


ENRICHMENT_FIELDS = (
    *CHINESE_FIELDS, 'enrichment_method', 'takeaway_source', 'innovation_source',
    'summary_cn', 'summary_method',
)


def _enrichment_quality(paper):
    if not all(isinstance(paper.get(field), str) and paper[field].strip() for field in CHINESE_FIELDS):
        return 0
    method = paper.get('enrichment_method')
    if method == 'editorial_abstract_summary':
        return 4
    if method == CODEX_METHOD:
        return 3
    abstract_cn = paper['abstract_cn']
    if (method == 'local_abstract_translation' or paper.get('summary_method') == 'keywords'
            or (abstract_cn.startswith('本文研究') and '\n\n核心内容：' in abstract_cn)):
        return 1
    return 2


def _replace_enrichment(paper, enrichment):
    for field in ENRICHMENT_FIELDS:
        if field in enrichment:
            paper[field] = enrichment[field]
        else:
            paper.pop(field, None)


def enrich_papers_with_cache(papers, report_directory, translator):
    """Reuse complete enrichments and upgrade cached fallbacks when Codex is available."""
    directory = Path(report_directory)
    archives = sorted(directory.glob('????-??-??.json'), reverse=True)[:7]
    inputs = {(paper.get('id'), paper.get('abstract')) for paper in papers if paper.get('id')}
    cached = {}
    for path in [*archives, directory / 'top100.json']:
        if not path.is_file():
            continue
        try:
            stored = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            print(f'Skipping translation cache {path.name} ({type(error).__name__})')
            continue
        for paper in stored:
            key = paper.get('id'), paper.get('abstract')
            if key in inputs and _enrichment_quality(paper) > _enrichment_quality(cached.get(key, {})):
                cached[key] = paper

    upgrades = []
    untranslated = []
    for paper in papers:
        previous = cached.get((paper.get('id'), paper.get('abstract')), {})
        if _enrichment_quality(previous) > _enrichment_quality(paper):
            _replace_enrichment(paper, previous)
        quality = _enrichment_quality(paper)
        if paper.get('abstract') and (quality == 0 or (quality == 1 and translator.codex_available)):
            candidate = {field: paper[field] for field in ('id', 'title', 'abstract') if field in paper}
            group = upgrades if quality == 1 else untranslated
            group.append((paper, candidate, quality))

    for candidates, codex_only in ((upgrades, True), (untranslated, False)):
        if not candidates or not translator.enabled:
            continue
        translator.batch_translate([candidate for _, candidate, _ in candidates], codex_only=codex_only)
        for paper, candidate, quality in candidates:
            if _enrichment_quality(candidate) > quality:
                _replace_enrichment(paper, candidate)
