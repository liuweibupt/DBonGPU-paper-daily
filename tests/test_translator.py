import json
import subprocess
from pathlib import Path

from src.analysis import translator


TRANSLATION = {
    'abstract_cn': '在 96 个工作线程上达到 1,010 MIPS。',
    'takeaway': '仿真吞吐量随工作线程数增加。',
    'innovation': '1. 并行重放指令轨迹。',
}


def test_codex_matches_papers_by_index_and_falls_back_per_paper(monkeypatch):
    monkeypatch.delenv('PAPER_DAILY_CODEX', raising=False)
    monkeypatch.setenv('OPENAI_API_KEY', 'test')
    monkeypatch.setattr(translator.shutil, 'which', lambda _: '/bin/codex')
    papers = [
        {'title': 'A', 'abstract': 'First paper.', 'summary_cn': '旧主题提示', 'takeaway_source': ['Old']},
        {'title': 'B', 'abstract': 'Second paper.'},
        {'title': 'C', 'abstract': 'Third paper.'},
    ]
    api_prompts = []

    def run(command, *, cwd, input, **kwargs):
        assert command[0] == '/bin/codex'
        assert command[command.index('--sandbox') + 1] == 'read-only'
        assert command[-1] == '-'
        source = json.loads(input.split('待译资料：\n')[1])
        assert [row['index'] for row in source] == [0, 1, 2]
        destination = Path(command[command.index('--output-last-message') + 1])
        assert destination.parent == Path(cwd)
        destination.write_text(json.dumps({
            'papers': [
                {'index': 2, **TRANSLATION},
                {'index': 0, **TRANSLATION},
                {'index': 1, 'abstract_cn': 'Incomplete'},
            ]
        }), encoding='utf-8')

    def translate_with_api(prompt):
        api_prompts.append(prompt)
        return json.dumps(TRANSLATION)

    monkeypatch.setattr(translator.subprocess, 'run', run)
    paper_translator = translator.PaperTranslator()
    monkeypatch.setattr(paper_translator, '_call_api', translate_with_api)
    assert paper_translator.batch_translate(papers, delay=0) is papers
    assert [paper['enrichment_method'] for paper in papers] == [
        translator.CODEX_METHOD, 'llm_abstract_translation', translator.CODEX_METHOD,
    ]
    assert len(api_prompts) == 1
    assert 'Second paper.' in api_prompts[0]
    assert 'summary_cn' not in papers[0]
    assert 'takeaway_source' not in papers[0]


def test_codex_failure_preserves_previous_enrichment(monkeypatch):
    monkeypatch.delenv('PAPER_DAILY_CODEX', raising=False)
    monkeypatch.setenv('OPENAI_API_KEY', 'test')
    monkeypatch.setattr(translator.shutil, 'which', lambda _: '/bin/codex')
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        raise subprocess.TimeoutExpired(command, kwargs['timeout'])

    def unexpected_api_call(_):
        raise AssertionError('codex_only should not call the API fallback')

    monkeypatch.setattr(translator.subprocess, 'run', run)
    paper_translator = translator.PaperTranslator()
    monkeypatch.setattr(paper_translator, '_call_api', unexpected_api_call)
    original = {'abstract': 'Prior paper.', 'enrichment_method': 'local_abstract_translation', **TRANSLATION}
    papers = [original.copy() for _ in range(8)]
    paper_translator.batch_translate(papers, codex_only=True)
    assert papers == [original] * 8
    assert len(calls) == 1
    assert not paper_translator.codex_available
