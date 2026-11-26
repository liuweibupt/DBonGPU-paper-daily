import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from src.analysis.enrichment_cache import enrich_papers_with_cache


def source(paper_id, abstract='The original abstract.'):
    return {'id': paper_id, 'title': f'Paper {paper_id}', 'abstract': abstract}


def enrichment(text, method):
    return {
        'abstract_cn': text,
        'takeaway': '结论',
        'innovation': '贡献',
        'enrichment_method': method,
    }


class EnrichmentCacheTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)

    def save(self, name, papers):
        (self.directory / name).write_text(json.dumps(papers, ensure_ascii=False), encoding='utf-8')

    def test_prefers_codex_and_editorial_versions_in_any_archive(self):
        first, second = source('1'), source('2')
        self.save('2026-11-26.json', [
            {**first, **enrichment('机器翻译', 'local_abstract_translation')},
            {**second, **enrichment('自动译文', 'codex')},
        ])
        self.save('top100.json', [
            {**first, **enrichment('早期的 Codex 译文', 'codex')},
            {**second, **enrichment('编辑译文', 'editorial_abstract_summary')},
        ])
        translator = Mock(codex_available=False, enabled=False)

        enrich_papers_with_cache([first, second], self.directory, translator)

        self.assertEqual(first['abstract_cn'], '早期的 Codex 译文')
        self.assertEqual(second['abstract_cn'], '编辑译文')
        translator.batch_translate.assert_not_called()

    def test_upgrades_legacy_content_and_preserves_old_fields_when_codex_fails(self):
        first, second = source('1'), source('2')
        first['score'] = 0.8
        local = enrichment('机器翻译', 'local_abstract_translation')
        keyword = {'abstract_cn': '本文研究缓存技术。\n\n核心内容：Our design…',
                   'takeaway': '关键词结论', 'innovation': '关键词贡献'}
        self.save('2026-11-26.json', [
            {**first, **keyword, 'summary_cn': '关键词摘要'},
            {**second, **local, 'takeaway_source': 'abstract_result_sentences'},
        ])
        new = enrichment('更新的中文译文', 'codex')
        translator = Mock(codex_available=True, enabled=True)

        def translate(papers, *, codex_only):
            self.assertTrue(codex_only)
            self.assertEqual(papers, [source('1'), source('2')])
            papers[0].update(new)
            papers[1]['abstract_cn'] = '不完整的译文'

        translator.batch_translate.side_effect = translate
        enrich_papers_with_cache([first, second], self.directory, translator)

        self.assertEqual(first, {**source('1'), **new, 'score': 0.8})
        self.assertEqual(second, {**source('2'), **local, 'takeaway_source': 'abstract_result_sentences'})

    def test_changed_abstract_uses_normal_translation_and_fallback(self):
        paper = source('1', 'The updated abstract.')
        self.save('top100.json', [{**source('1'), **enrichment('早期译文', 'codex')}])
        translator = Mock(codex_available=False, enabled=True)
        new = enrichment('新译文', 'local_abstract_translation')

        def translate(papers, *, codex_only):
            self.assertFalse(codex_only)
            papers[0].update(new)

        translator.batch_translate.side_effect = translate
        enrich_papers_with_cache([paper], self.directory, translator)

        self.assertEqual(paper, {**source('1', 'The updated abstract.'), **new})
