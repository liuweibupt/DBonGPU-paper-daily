#!/usr/bin/env python3
"""Upgrade the current daily issues using Codex and translations already on disk."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from analysis.enrichment_cache import ENRICHMENT_FIELDS, _replace_enrichment
from analysis.translator import CHINESE_FIELDS, CODEX_METHOD, PaperTranslator
from display.html_display import HTMLDisplay


EDITORIAL_METHOD = 'editorial_abstract_summary'
UPGRADABLE_METHODS = {'local_abstract_translation', 'llm_abstract_translation', 'keywords'}
CACHE_LIMIT = 70


def issue_date(value):
    try:
        if date.fromisoformat(value).isoformat() == value:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError('date must be a valid YYYY-MM-DD')


def _daily_issues(directory):
    for path in sorted(directory.glob('????-??-??.json'), reverse=True):
        try:
            issue_date(path.stem)
        except argparse.ArgumentTypeError:
            continue
        if path.is_file():
            yield path


def _read_papers(path):
    papers = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(papers, list) or not all(isinstance(paper, dict) for paper in papers):
        raise ValueError(f'{path} must contain a list of papers')
    return papers


def _optional_papers(path):
    try:
        return _read_papers(path)
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as error:
        print(f'Skipping unreadable translation cache {path} ({type(error).__name__})', file=sys.stderr)
        return []


def _source_key(paper):
    return paper.get('id'), paper.get('abstract')


def _complete(paper):
    return all(isinstance(paper.get(field), str) and paper[field].strip() for field in CHINESE_FIELDS)


def _needs_codex(paper):
    if not paper.get('abstract'):
        return False
    if not _complete(paper):
        return True
    method = paper.get('enrichment_method')
    if method in (CODEX_METHOD, EDITORIAL_METHOD):
        return False
    abstract_cn = paper['abstract_cn']
    return (method in UPGRADABLE_METHODS or paper.get('summary_method') == 'keywords'
            or (abstract_cn.startswith('本文研究') and '\n\n核心内容：' in abstract_cn))


def _repository_translations(archives, annual, wanted):
    cached = {}
    for path in [*archives[:7], annual]:
        for paper in _optional_papers(path):
            key = _source_key(paper)
            method = paper.get('enrichment_method')
            if key not in wanted or method not in (CODEX_METHOD, EDITORIAL_METHOD) or not _complete(paper):
                continue
            if key not in cached or (method == EDITORIAL_METHOD and cached[key]['enrichment_method'] != method):
                cached[key] = paper
    return cached


def _write_cache(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False)
    temporary = Path(stream.name)
    try:
        with stream:
            json.dump(list(entries.values())[-CACHE_LIMIT:], stream, ensure_ascii=False)
            stream.write('\n')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _refresh_issue(directory, feed, topic, cache_dir, selected_date):
    archives = list(_daily_issues(directory))
    if not archives:
        return 0
    report = directory / f'{selected_date}.json' if selected_date else archives[0]
    if report not in archives:
        return 0
    papers = _read_papers(report)
    pending = [paper for paper in papers if _needs_codex(paper)]
    if not pending:
        return 0

    wanted = {_source_key(paper) for paper in pending if paper.get('id')}
    translated = _repository_translations(archives, directory / 'top100.json', wanted)
    cache_path = cache_dir / f'{feed}.json' if cache_dir is not None else None
    saved = {}
    if cache_path is not None:
        saved = {
            _source_key(paper): paper for paper in _optional_papers(cache_path)[-CACHE_LIMIT:]
            if all(_source_key(paper)) and paper.get('enrichment_method') == CODEX_METHOD and _complete(paper)
        }
    for key in wanted.intersection(saved):
        translated.setdefault(key, saved[key])

    candidates = {
        _source_key(paper): {field: paper.get(field, '') for field in ('id', 'abstract', 'title')}
        for paper in pending if _source_key(paper) not in translated
    }
    if candidates:
        translator = PaperTranslator(topic=topic)
        if translator.codex_available:
            translator.batch_translate(list(candidates.values()), delay=0, codex_only=True)

    new_translations = {
        key: paper for key, paper in candidates.items()
        if paper.get('enrichment_method') == CODEX_METHOD and _complete(paper)
    }
    translated.update(new_translations)
    if cache_path is not None and new_translations:
        saved.update({
            key: {field: paper[field] for field in ('id', 'abstract', *ENRICHMENT_FIELDS) if field in paper}
            for key, paper in new_translations.items() if all(key)
        })
        _write_cache(cache_path, saved)

    upgraded = 0
    for paper in pending:
        translation = translated.get(_source_key(paper))
        if translation is not None:
            _replace_enrichment(paper, translation)
            upgraded += 1

    if upgraded:
        output = directory / 'index.html' if report == archives[0] else report.with_suffix('.html')
        HTMLDisplay(feed=feed).save_daily(papers, str(output), report.stem)
    remaining = len(pending) - upgraded
    print(f'{feed} {report.stem}: upgraded {upgraded}, {remaining} pending')
    return remaining


def refresh_daily_translations(docs_dir, cache_dir=None, selected_date=None):
    remaining = 0
    for directory, feed, topic in (
        (docs_dir, 'db', 'GPU 数据库'),
        (docs_dir / 'architecture', 'architecture', '计算机体系结构'),
    ):
        remaining += _refresh_issue(directory, feed, topic, cache_dir, selected_date)
    return 2 if remaining else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', type=issue_date, help='Upgrade this issue date instead of each feed’s latest issue.')
    parser.add_argument('--cache-dir', type=Path, help='Reuse successful translations from an earlier attempt.')
    args = parser.parse_args()
    return refresh_daily_translations(ROOT / 'docs', args.cache_dir, args.date)


if __name__ == '__main__':
    sys.exit(main())
