import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from scripts import refresh_daily_translations as refresh


def paper(paper_id, abstract='English abstract'):
    return {'id': paper_id, 'title': f'Paper {paper_id}', 'abstract': abstract, 'score': 0.75}


def translated(text, method=None):
    translation = {'abstract_cn': text, 'takeaway': '结论', 'innovation': '贡献'}
    if method is not None:
        translation['enrichment_method'] = method
    return translation


class RefreshDailyTranslationsTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.docs = root / 'docs'
        self.cache = root / 'cache'

    def save(self, name, papers):
        path = self.docs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(papers, ensure_ascii=False), encoding='utf-8')
        return path

    def test_latest_of_each_feed_reuses_annual_and_archive_translations(self):
        first = paper('1')
        second = paper('2')
        self.save('2026-11-25.json', [{**first, **translated('旧日 Codex 译文', 'codex')}])
        db = self.save('2026-11-26.json', [
            {**first, **translated('已有 API 译文', 'llm_abstract_translation')},
        ])
        self.save('2026-11-31.json', [{**first, **translated('无效日期记录', 'codex')}])
        annual = self.save('architecture/top100.json', [
            {**second, **translated('编辑译文', 'editorial_abstract_summary')},
        ])
        arch = self.save('architecture/2026-11-25.json', [
            {**second, **translated('本地机翻', 'local_abstract_translation')},
        ])
        annual_content = annual.read_bytes()

        with patch.object(refresh, 'PaperTranslator') as translator:
            self.assertEqual(refresh.refresh_daily_translations(self.docs), 0)
        translator.assert_not_called()

        self.assertEqual(json.loads(db.read_text()), [{**first, **translated('旧日 Codex 译文', 'codex')}])
        self.assertEqual(json.loads(arch.read_text()), [{**second, **translated('编辑译文', 'editorial_abstract_summary')}])
        self.assertEqual(annual.read_bytes(), annual_content)
        self.assertIn('旧日 Codex 译文', (self.docs / 'index.html').read_text())
        self.assertIn('编辑译文', (self.docs / 'architecture/index.html').read_text())
        self.assertFalse((self.docs / '2026-11-25.html').exists())

    def test_partial_upgrade_is_saved_and_reused_after_fresh_checkout(self):
        first = paper('1')
        fallback = {**first, **translated('本文研究缓存技术。\n\n核心内容：English'), 'summary_cn': '旧摘要'}
        second = {**paper('2'), 'abstract_cn': ''}
        protected = {**paper('3'), **translated('既有完整译文')}
        report = self.save('2026-11-26.json', [fallback, second, protected])
        new = translated('Codex 译文', 'codex')
        backend = Mock(codex_available=True)

        def translate(papers, *, delay, codex_only):
            self.assertEqual(delay, 0)
            self.assertTrue(codex_only)
            self.assertEqual([item['id'] for item in papers], ['1', '2'])
            papers[0].update(new)

        backend.batch_translate.side_effect = translate
        with patch.object(refresh, 'PaperTranslator', return_value=backend):
            self.assertEqual(refresh.refresh_daily_translations(self.docs, self.cache), 2)
        expected = [{**first, **new}, second, protected]
        self.assertEqual(json.loads(report.read_text()), expected)

        self.save('2026-11-26.json', [fallback, second, protected])
        backend = Mock(codex_available=False)
        with patch.object(refresh, 'PaperTranslator', return_value=backend):
            self.assertEqual(refresh.refresh_daily_translations(self.docs, self.cache), 2)
        backend.batch_translate.assert_not_called()
        self.assertEqual(json.loads(report.read_text()), expected)
        self.assertEqual([path.name for path in self.cache.iterdir()], ['db.json'])

        updated = {**fallback, 'abstract': 'English abstract, revised after the earlier attempt'}
        self.save('2026-11-26.json', [updated, second, protected])
        with patch.object(refresh, 'PaperTranslator', return_value=backend):
            self.assertEqual(refresh.refresh_daily_translations(self.docs, self.cache), 2)
        self.assertEqual(json.loads(report.read_text()), [updated, second, protected])

    def test_explicit_older_issue_leaves_the_latest_index_untouched(self):
        first = paper('1')
        report = self.save('2026-11-25.json', [{**first, **translated('机器译文', 'local_abstract_translation')}])
        self.save('2026-11-26.json', [{**first, **translated('应复用的 Codex 译文', 'codex')}])
        index = self.docs / 'index.html'
        index.write_text('Current home page')

        self.assertEqual(refresh.refresh_daily_translations(self.docs, selected_date='2026-11-25'), 0)
        self.assertEqual(index.read_text(), 'Current home page')
        self.assertEqual(json.loads(report.read_text())[0]['abstract_cn'], '应复用的 Codex 译文')
