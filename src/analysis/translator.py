"""
Translator for Paper Daily

Translates paper abstracts to Chinese and generates AI takeaway/innovation points
using an OpenAI-compatible API.
"""

import os
import json
import time
import requests
from typing import Dict, Optional


class PaperTranslator:
    """Translates paper abstracts and generates AI summaries"""

    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY', '')
        self.api_base = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com/v1')
        self.model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
        self.enabled = bool(self.api_key)

    def translate_and_summarize(self, paper: Dict) -> Dict:
        """
        Translate abstract to Chinese and generate takeaway + innovation points.
        Returns the paper dict with added fields: abstract_cn, takeaway, innovation.
        """
        if not self.enabled:
            # Fallback: generate brief keyword-based summary
            paper['abstract_cn'] = ''
            paper['takeaway'] = ''
            paper['innovation'] = ''
            return paper

        abstract = paper.get('abstract', '')
        title = paper.get('title', '')

        if not abstract:
            paper['abstract_cn'] = ''
            paper['takeaway'] = ''
            paper['innovation'] = ''
            return paper

        prompt = f"""你是一位 GPU 数据库领域的研究专家。请对以下论文进行分析：

标题：{title}

摘要：{abstract}

请用中文完成以下三个任务，严格按照 JSON 格式输出（不要包含 markdown 代码块标记）：

1. "abstract_cn": 将英文摘要完整翻译为中文，保留技术术语的英文原文（用括号标注），如"谓词迁移（Predicate Transfer）"
2. "takeaway": 用1-2句话总结这篇论文的核心洞察或关键结论，突出对 GPU 数据库领域的意义
3. "innovation": 列出2-4个主要创新点，用分号分隔，每个创新点简洁明了

输出格式示例：
{{"abstract_cn": "中文翻译...", "takeaway": "核心洞察...", "innovation": "1. 创新点一；2. 创新点二；3. 创新点三"}}"""

        try:
            result = self._call_api(prompt)
            if result:
                parsed = self._parse_response(result)
                paper['abstract_cn'] = parsed.get('abstract_cn', '')
                paper['takeaway'] = parsed.get('takeaway', '')
                paper['innovation'] = parsed.get('innovation', '')
            else:
                paper['abstract_cn'] = ''
                paper['takeaway'] = ''
                paper['innovation'] = ''
        except Exception as e:
            print(f"Translation error for '{title[:50]}...': {e}")
            paper['abstract_cn'] = ''
            paper['takeaway'] = ''
            paper['innovation'] = ''

        return paper

    def batch_translate(self, papers: list, delay: float = 1.0) -> list:
        """Translate a batch of papers with rate limiting"""
        total = len(papers)
        for i, paper in enumerate(papers):
            print(f"  Translating paper {i+1}/{total}: {paper.get('title', '')[:60]}...")
            self.translate_and_summarize(paper)
            if delay > 0 and i < total - 1:
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
                {'role': 'system', 'content': '你是一位 GPU 数据库领域的研究专家，擅长翻译和总结学术论文。请始终以纯 JSON 格式输出，不要包含任何 markdown 标记。'},
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
        except requests.exceptions.RequestException as e:
            print(f"API call failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response status: {e.response.status_code}")
                print(f"  Response body: {e.response.text[:500]}")
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
            import re
            json_match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            print(f"Failed to parse API response as JSON: {cleaned[:200]}")
            return {}
