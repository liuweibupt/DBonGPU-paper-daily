"""
Translator for Paper Daily

Translates paper abstracts to Chinese and generates AI takeaway/innovation points
using an OpenAI-compatible API.
"""

import hashlib
import json
import os
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import requests
from typing import Dict, Optional

from .keyword_fallback import abstract_sentences, extract_abstract_evidence


_EN_ZH_MODEL = 'translate-en_zh-1_9'
_EN_ZH_URL = f'https://argos-net.com/v1/{_EN_ZH_MODEL}.argosmodel'
_EN_ZH_SHA256 = '433e7c4f034d87fbe2353161e05f18646d7999452f801a4e1f0378522b9850ab'
_CHINESE_CHARACTER = re.compile(r'[\u3400-\u9fff]')
_QUANTITY = re.compile(r'\d+(?:(?<=\d)[.,](?=\d)\d+)*')
_DECREASE = re.compile(r'\b(?:reduc\w+|lower\w*|decreas\w+|cuts?|less|fewer)\b', re.I)
_INCREASE = re.compile(r'\b(?:increas\w+|rais\w+|higher|great\w+|more|improv\w+)\b', re.I)
_PERCENTAGE_CHANGE = re.compile(
    r'\b(?:uses?|consumes?)\s+(\d+(?:\.\d+)?%)\s+(less|more)\s+'
    r'(energy(?: per token)?|power|bandwidth|memory)\b',
    re.I,
)
_TECHNICAL_TERMS = {
    'access latency': '访问延迟',
    'approximate nearest neighbor search': '近似最近邻搜索',
    'arithmetic intensity': '算术强度',
    'affine striping': '仿射条带化',
    'agentic': '智能体式',
    'autoregressive transformer': '自回归 Transformer',
    'back-pressure': '反压',
    'bus utilization': '总线利用率',
    'cache coherence': '缓存一致性',
    'cache hit rate': '缓存命中率',
    'chip-level interconnects': '芯片级互连',
    'content residual': '内容残差',
    'contention': '争用',
    'coverage closure': '覆盖率收敛',
    'critical path': '关键路径',
    'cycle-exact': '周期精确',
    'data locality': '数据局部性',
    'decode latency': '解码延迟',
    'design space exploration': '设计空间探索',
    'design families': '设计族',
    'dynamic range': '动态范围',
    'field-programmable gate array': '现场可编程门阵列',
    'formal verification': '形式验证',
    'functional coverage': '功能覆盖率',
    'hardware accelerator': '硬件加速器',
    'hardware bus': '硬件总线',
    'hardware design': '硬件设计',
    'hardware synthesis': '硬件综合',
    'head-of-line stalls': '队头阻塞',
    'heterogeneous': '异构',
    'hierarchical folding': '分层折叠',
    'host traffic': '主机流量',
    'inference': '推理',
    'interconnect traffic': '互连流量',
    'key-value cache': '键值缓存',
    'latency-energy-monetary-cost objective': '延迟、能耗与货币成本复合目标',
    'logic synthesis': '逻辑综合',
    'look-up table': '查找表',
    'logical error rate': '逻辑错误率',
    'mapping inflation': '映射膨胀',
    'memory bandwidth': '内存带宽',
    'memory controller': '内存控制器',
    'memory controllers': '内存控制器',
    'memory hierarchy': '存储层次结构',
    'memory streams': '内存访问流',
    'microarchitecture': '微体系结构',
    'microarchitectural': '微体系结构的',
    'microprocessor': '微处理器',
    'multi-chiplet': '多芯粒',
    'node-level': '节点级',
    'out-of-order': '乱序',
    'parameter sharing': '参数共享',
    'performance bottlenecks': '性能瓶颈',
    'pipeline hazards': '流水线冒险',
    'positional carrier': '位置载波',
    'positional phase engine': '位置相位引擎',
    'prefetch': '预取',
    'processing-in-memory': '存内计算',
    'program synthesis': '程序综合',
    'quantization noise': '量化噪声',
    'register-transfer level': '寄存器传输级',
    'residual variance': '残差方差',
    'rotary position embedding': '旋转位置编码',
    'scoreboard': '记分板',
    'sparse tensors': '稀疏张量',
    'spiking neural network': '脉冲神经网络',
    'stencil computations': '模板计算',
    'store buffer': '存储缓冲区',
    'streaming neural decoder': '流式神经解码器',
    'streaming softmax': '流式 softmax',
    'superscalar': '超标量',
    'synthesis trajectory': '综合轨迹',
    'synthesis trajectories': '综合轨迹',
    'tail latency': '尾延迟',
    'tensor cores': '张量核心',
    'traffic generators': '流量生成器',
    'vector search': '向量搜索',
    'wall-clock time': '实际运行时间',
    'warp scheduling': 'warp 调度',
    'workload': '工作负载',
    'workloads': '工作负载',
}
_TECHNICAL_TERM = re.compile(
    r'(?<![\w-])(?:'
    + '|'.join(re.escape(term) for term in sorted(_TECHNICAL_TERMS, key=len, reverse=True))
    + r')(?![\w-])|\b[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*\b',
    re.I,
)
_TERM_MARKER = re.compile(r'\[\s*T\s*(\d+)\s*\]')
_NAMED_METHOD = re.compile(r'\b(?:present|propose|introduce|design|develop|called|named) ([A-Z][\w-]*)')


def _translation_cache() -> Path:
    configured = os.environ.get('PAPER_DAILY_CACHE_DIR')
    if configured:
        return Path(configured).expanduser()
    cache_home = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    return cache_home / 'paper-daily'


def _get_local_model() -> Path:
    """Install the pinned English–Chinese model atomically in the user cache."""
    cache = _translation_cache()
    destination = cache / _EN_ZH_MODEL
    if destination.is_dir():
        return destination

    cache.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=cache) as temp:
        work = Path(temp)
        archive = work / 'translation-model.zip'
        digest = hashlib.sha256()
        with requests.get(_EN_ZH_URL, stream=True, timeout=(15, 60)) as response:
            response.raise_for_status()
            with archive.open('wb') as target:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    digest.update(chunk)
                    target.write(chunk)
        if digest.hexdigest() != _EN_ZH_SHA256:
            raise ValueError('Unexpected checksum for English–Chinese translation model')

        # Verify the archive before extracting the pinned upstream package.
        with ZipFile(archive) as package:
            package.extractall(work)
        try:
            (work / _EN_ZH_MODEL).rename(destination)
        except OSError:
            if not destination.is_dir():
                raise
    return destination


def _prepare_source(text: str) -> str:
    """Normalize arXiv's inline LaTeX without dropping scientific values."""
    text = re.sub(r'\{\\(?:em|it|bf)\s+([^{}]+)\}', r'\1', text)
    return text.replace(r'\times', '×').replace(r'\%', '%').replace('$', '')


def _translation_input(text: str, names: set) -> tuple:
    """Make comparison wording explicit and protect architecture terms."""
    def clarify_comparison(match):
        value, comparison, quantity = match.groups()
        verb = 'reduces' if comparison.lower() == 'less' else 'increases'
        return f'{verb} {quantity} use by {value}'

    terms = {}

    def protect_term(match):
        word = match.group()
        translated = _TECHNICAL_TERMS.get(word.lower())
        if translated is None:
            if word not in names and sum(character.isupper() for character in word) < 2:
                return word
            translated = word
        index = str(len(terms))
        terms[index] = translated
        return f'[T{index}]'

    text = _PERCENTAGE_CHANGE.sub(clarify_comparison, text)
    return _TECHNICAL_TERM.sub(protect_term, text), terms


def _restore_terms(text: str, terms: dict) -> str:
    text = unicodedata.normalize('NFKC', text).replace('▁', '').strip()
    if Counter(_TERM_MARKER.findall(text)) != Counter(terms.keys()):
        return ''
    return _TERM_MARKER.sub(lambda match: terms[match.group(1)], text)


def _quantities(text: str) -> Counter:
    normalized = unicodedata.normalize('NFKC', text)
    normalized = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', normalized)
    return Counter(_QUANTITY.findall(normalized))


def _keeps_source_values(source: str, translated: str) -> bool:
    amounts = _quantities(source)
    if amounts != _quantities(translated):
        return False
    if amounts and _DECREASE.search(source) and not re.search(r'少|降|减|削|低|节省|压缩', translated):
        return False
    if amounts and _INCREASE.search(source) and not re.search(r'高|增|多|升|改进|优化', translated):
        return False
    return True


class LocalChineseTranslator:
    """Translate arXiv abstract sentences and extract claims from the source."""

    def __init__(self):
        import ctranslate2
        import sentencepiece

        model = _get_local_model()
        self.tokenizer = sentencepiece.SentencePieceProcessor(
            model_file=str(model / 'sentencepiece.model'),
        )
        self.model = ctranslate2.Translator(
            str(model / 'model'), device='cpu', compute_type='int8', intra_threads=2,
        )

    def enrich(self, abstract: str, title: str) -> Dict:
        source = [_prepare_source(sentence) for sentence in abstract_sentences(abstract)]
        names = set(_NAMED_METHOD.findall(abstract))
        name, separator, _ = title.partition(':')
        if separator and re.fullmatch(r'[A-Z][\w-]*', name):
            names.add(name)
        prepared = [_translation_input(sentence, names) for sentence in source]
        batches = self.tokenizer.encode([text for text, _ in prepared], out_type=str)
        outputs = self.model.translate_batch(batches, beam_size=4, max_batch_size=16)
        translations = []
        for original, (_, terms), output in zip(source, prepared, outputs):
            translated = _restore_terms(self.tokenizer.decode(output.hypotheses[0]), terms)
            if not _CHINESE_CHARACTER.search(translated) or not _keeps_source_values(original, translated):
                translations.append(f'【该句原文】{original}')
            else:
                translations.append(translated)

        results, contributions = extract_abstract_evidence(source)
        return {
            'abstract_cn': ' '.join(translations),
            'takeaway': ' '.join(translations[index] for index in results) or '摘要未明确报告可提取的结论。',
            'innovation': '；'.join(
                f'{number}. {translations[index]}'
                for number, index in enumerate(contributions, 1)
            ) or '摘要未明确列出可提取的方法贡献。',
            'takeaway_source': [source[index] for index in results],
            'innovation_source': [source[index] for index in contributions],
            'enrichment_method': 'local_abstract_translation',
        }


class PaperTranslator:
    """Translates paper abstracts and generates AI summaries"""

    def __init__(self, topic: str = 'GPU 数据库', local_fallback: bool = False):
        self.topic = topic
        self.api_key = os.environ.get('OPENAI_API_KEY', '')
        self.api_base = os.environ.get('OPENAI_API_BASE') or 'https://api.openai.com/v1'
        self.model = os.environ.get('OPENAI_MODEL') or 'gpt-4o-mini'
        self._api_available = bool(self.api_key)
        self._local_fallback = local_fallback
        self._local_translator = None

    @property
    def enabled(self) -> bool:
        return self._api_available or self._local_fallback

    def translate_and_summarize(self, paper: Dict) -> Dict:
        """
        Translate abstract to Chinese and generate takeaway + innovation points.
        Returns the paper dict with added fields: abstract_cn, takeaway, innovation.
        """
        abstract = paper.get('abstract', '')
        title = paper.get('title', '')
        fields = ('abstract_cn', 'takeaway', 'innovation')
        paper.update(dict.fromkeys(fields, ''))

        if not abstract or not self.enabled:
            return paper

        prompt = f"""你是一位 {self.topic}领域的研究专家。请对以下论文进行分析：

标题：{title}

摘要：{abstract}

请用中文完成以下三个任务，严格按照 JSON 格式输出（不要包含 markdown 代码块标记）：

1. "abstract_cn": 将英文摘要完整翻译为中文，保留技术术语的英文原文（用括号标注），如"谓词迁移（Predicate Transfer）"
2. "takeaway": 用1-2句话总结这篇论文的核心洞察或关键结论，突出对 {self.topic}领域的意义
3. "innovation": 列出2-4个主要创新点，用分号分隔，每个创新点简洁明了

输出格式示例：
{{"abstract_cn": "中文翻译...", "takeaway": "核心洞察...", "innovation": "1. 创新点一；2. 创新点二；3. 创新点三"}}"""

        if self._api_available:
            try:
                result = self._call_api(prompt)
                parsed = self._parse_response(result) if result else {}
                if isinstance(parsed, dict):
                    for field in fields:
                        value = parsed.get(field)
                        paper[field] = value.strip() if isinstance(value, str) else ''
            except (KeyError, IndexError, TypeError, ValueError) as error:
                print(f'Unexpected translation API response ({type(error).__name__})')

        if self._local_fallback and not all(_CHINESE_CHARACTER.search(paper[field]) for field in fields):
            if self._local_translator is None:
                print('Loading local English–Chinese translation model')
                try:
                    self._local_translator = LocalChineseTranslator()
                except (ImportError, OSError, RuntimeError, ValueError) as error:
                    raise RuntimeError(
                        f'Could not load the local English–Chinese translation model ({type(error).__name__})'
                    ) from error
            paper.update(self._local_translator.enrich(abstract, title))

        return paper

    def batch_translate(self, papers: list, delay: float = 1.0) -> list:
        """Translate a batch of papers with rate limiting"""
        total = len(papers)
        for i, paper in enumerate(papers):
            print(f"  Translating paper {i+1}/{total}: {paper.get('title', '')[:60]}...")
            self.translate_and_summarize(paper)
            if delay > 0 and self._api_available and i < total - 1:
                time.sleep(delay)
        return papers

    def _call_api(self, prompt: str) -> Optional[str]:
        """Call the OpenAI-compatible API"""
        url = f"{self.api_base.rstrip('/')}/chat/completions"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': f'你是一位 {self.topic}领域的研究专家，擅长翻译和总结学术论文。请始终以纯 JSON 格式输出，不要包含任何 markdown 标记。'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,
            'max_tokens': 2000,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except requests.exceptions.RequestException as error:
            status = error.response.status_code if error.response is not None else None
            if status in (401, 403):
                self._api_available = False
            print(f'Translation API unavailable ({status or type(error).__name__})')
            return None

    def _parse_response(self, response: str) -> Dict:
        """Parse the API response as JSON"""
        # Strip markdown code block markers if present
        cleaned = response.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            # Remove first and last lines (code block markers)
            lines = [l for l in lines if not l.strip().startswith('```')]
            cleaned = '\n'.join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            print("Failed to parse translation API response as JSON")
            return {}
