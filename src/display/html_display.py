"""
HTML Display for Paper Daily

Generates a beautiful static HTML page for GitHub Pages.
"""

from typing import List, Dict
from datetime import datetime
import os
import json


class HTMLDisplay:
    """Generates HTML page for paper recommendations"""

    def __init__(self):
        self.title = "GPU 数据库论文日报"

    def generate_daily_html(self, recommendations: List[Dict], date: str = None) -> str:
        """Generate daily paper recommendation HTML page"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        papers_html = ""
        for i, paper in enumerate(recommendations, 1):
            papers_html += self._render_paper_card(paper, i)

        history_html = self._render_history_nav(date, 'daily')

        high_relevance = sum(1 for p in recommendations if p.get('score', 0) >= 0.7)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GPU 数据库论文日报 - {date}</title>
    {self._common_styles()}
</head>
<body>
    <header>
        <h1>GPU 数据库论文日报</h1>
        <div class="subtitle">自动追踪 GPU 加速数据库领域最新研究</div>
        <div class="date">{date}</div>
        <nav class="page-nav">
            <a href="index.html" class="active">每日推荐</a>
            <a href="top100.html">年度 Top 100</a>
        </nav>
    </header>

    {history_html}

    <div class="stats">
        <div class="stat-item">
            <div class="stat-value">{len(recommendations)}</div>
            <div class="stat-label">推荐论文数</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{high_relevance}</div>
            <div class="stat-label">高相关度</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{date}</div>
            <div class="stat-label">更新日期</div>
        </div>
    </div>

    {papers_html}

    <footer>
        <p>由 <a href="https://github.com/nysa-liu/paper-daily">Paper Daily</a> 自动生成（GPU DB 聚焦版）</p>
        <p>上次运行：{generated_time} &middot; 数据来源：arXiv cs.AR / cs.DB / cs.DC</p>
    </footer>
</body>
</html>"""

    def generate_top100_html(self, papers: List[Dict], year: str = None) -> str:
        """Generate top 100 yearly papers HTML page"""
        if year is None:
            year = str(datetime.now().year)

        generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        display_papers = papers[:100]

        papers_html = ""
        for i, paper in enumerate(display_papers, 1):
            papers_html += self._render_paper_card(paper, i, compact=True)

        high_relevance = sum(1 for p in display_papers if p.get('score', 0) >= 0.7)
        mid_relevance = sum(1 for p in display_papers if 0.5 <= p.get('score', 0) < 0.7)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GPU 数据库年度热门论文 Top 100 - {year}</title>
    {self._common_styles()}
    <style>
        .yearly-hero {{
            text-align: center;
            padding: 30px 0;
        }}
        .yearly-hero h2 {{
            font-size: 1.6em;
            color: var(--accent);
            margin-bottom: 8px;
        }}
        .yearly-hero p {{
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <header>
        <h1>GPU 数据库论文日报</h1>
        <div class="subtitle">自动追踪 GPU 加速数据库领域最新研究</div>
        <nav class="page-nav">
            <a href="index.html">每日推荐</a>
            <a href="top100.html" class="active">年度 Top 100</a>
        </nav>
    </header>

    <div class="yearly-hero">
        <h2>{year} 年度 GPU 数据库热门论文 Top {len(display_papers)}</h2>
        <p>基于 arXiv 过去一年 cs.AR / cs.DB / cs.DC 领域论文，按 GPU 数据库相关度排序</p>
    </div>

    <div class="stats">
        <div class="stat-item">
            <div class="stat-value">{len(display_papers)}</div>
            <div class="stat-label">入选论文</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{high_relevance}</div>
            <div class="stat-label">高相关度</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{mid_relevance}</div>
            <div class="stat-label">中等相关度</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{year}</div>
            <div class="stat-label">统计年份</div>
        </div>
    </div>

    {papers_html}

    <footer>
        <p>由 <a href="https://github.com/nysa-liu/paper-daily">Paper Daily</a> 自动生成（GPU DB 聚焦版）</p>
        <p>上次运行：{generated_time} &middot; 数据来源：arXiv cs.AR / cs.DB / cs.DC</p>
    </footer>
</body>
</html>"""

    def _common_styles(self) -> str:
        """Common CSS styles shared across pages"""
        return """<style>
        :root {
            --bg: #0d1117;
            --card-bg: #161b22;
            --border: #30363d;
            --text: #e6edf3;
            --text-secondary: #8b949e;
            --accent: #58a6ff;
            --accent-green: #3fb950;
            --accent-orange: #d29922;
            --accent-red: #f85149;
            --score-high: #3fb950;
            --score-mid: #d29922;
            --score-low: #8b949e;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            max-width: 960px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            text-align: center;
            padding: 40px 0 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 30px;
        }
        header h1 {
            font-size: 2em;
            background: linear-gradient(135deg, var(--accent), var(--accent-green));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        header .subtitle {
            color: var(--text-secondary);
            font-size: 1.1em;
        }
        header .date {
            color: var(--accent);
            font-size: 1.3em;
            font-weight: 600;
            margin-top: 10px;
        }
        .page-nav {
            display: flex;
            gap: 12px;
            justify-content: center;
            margin-top: 16px;
        }
        .page-nav a {
            color: var(--text-secondary);
            text-decoration: none;
            padding: 6px 18px;
            border: 1px solid var(--border);
            border-radius: 20px;
            font-size: 0.95em;
            transition: all 0.2s;
        }
        .page-nav a:hover, .page-nav a.active {
            border-color: var(--accent);
            color: var(--accent);
        }
        .page-nav a.active {
            background: rgba(88,166,255,0.1);
        }
        .stats {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin: 20px 0 30px;
            flex-wrap: wrap;
        }
        .stat-item {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 24px;
            text-align: center;
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: 700;
            color: var(--accent);
        }
        .stat-label {
            font-size: 0.85em;
            color: var(--text-secondary);
        }
        .history-nav {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: center;
            margin: 20px 0 30px;
        }
        .history-nav a {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 6px 14px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        .history-nav a:hover, .history-nav a.active {
            border-color: var(--accent);
            color: var(--accent);
        }
        .history-nav a.active {
            background: rgba(88,166,255,0.1);
        }
        .paper-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            transition: border-color 0.2s;
        }
        .paper-card:hover {
            border-color: var(--accent);
        }
        .paper-card.compact {
            padding: 16px 20px;
        }
        .paper-rank {
            display: inline-block;
            background: linear-gradient(135deg, var(--accent), var(--accent-green));
            color: #fff;
            width: 32px;
            height: 32px;
            line-height: 32px;
            text-align: center;
            border-radius: 50%;
            font-weight: 700;
            font-size: 0.9em;
            margin-right: 10px;
            vertical-align: middle;
        }
        .compact .paper-rank {
            width: 28px;
            height: 28px;
            line-height: 28px;
            font-size: 0.8em;
        }
        .paper-title {
            font-size: 1.15em;
            font-weight: 600;
            display: inline;
            vertical-align: middle;
        }
        .compact .paper-title {
            font-size: 1.0em;
        }
        .paper-title a {
            color: var(--text);
            text-decoration: none;
        }
        .paper-title a:hover {
            color: var(--accent);
        }
        .paper-meta {
            margin-top: 10px;
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: center;
        }
        .score-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .score-high { background: rgba(63,185,80,0.15); color: var(--score-high); }
        .score-mid { background: rgba(210,153,34,0.15); color: var(--score-mid); }
        .score-low { background: rgba(139,148,158,0.1); color: var(--score-low); }
        .tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            background: rgba(88,166,255,0.1);
            color: var(--accent);
            border: 1px solid rgba(88,166,255,0.2);
        }
        .paper-authors {
            color: var(--text-secondary);
            font-size: 0.9em;
            margin-top: 8px;
        }
        .paper-abstract {
            color: var(--text-secondary);
            font-size: 0.95em;
            margin-top: 12px;
            line-height: 1.7;
        }
        .compact .paper-abstract {
            font-size: 0.88em;
            margin-top: 8px;
        }
        .paper-reasons {
            margin-top: 12px;
            padding: 8px 12px;
            background: rgba(63,185,80,0.05);
            border-left: 3px solid var(--accent-green);
            border-radius: 0 6px 6px 0;
            font-size: 0.9em;
            color: var(--accent-green);
        }
        .paper-links {
            margin-top: 12px;
            display: flex;
            gap: 12px;
        }
        .paper-links a {
            color: var(--accent);
            text-decoration: none;
            font-size: 0.9em;
            padding: 4px 10px;
            border: 1px solid var(--border);
            border-radius: 6px;
            transition: all 0.2s;
        }
        .paper-links a:hover {
            border-color: var(--accent);
            background: rgba(88,166,255,0.1);
        }
        footer {
            text-align: center;
            padding: 30px 0;
            border-top: 1px solid var(--border);
            margin-top: 40px;
            color: var(--text-secondary);
            font-size: 0.85em;
        }
        footer a { color: var(--accent); text-decoration: none; }
        @media (max-width: 640px) {
            body { padding: 12px; }
            header h1 { font-size: 1.5em; }
            .paper-card { padding: 16px; }
            .paper-title { font-size: 1.05em; }
        }
    </style>"""

    def _render_paper_card(self, paper: Dict, rank: int, compact: bool = False) -> str:
        """Render a single paper as an HTML card"""
        title = paper.get('title', '无标题')
        authors = paper.get('authors', [])
        abstract = paper.get('abstract', '无摘要')
        score = paper.get('score', 0.0)
        paper_id = paper.get('id', '')
        source = paper.get('source', 'arxiv').upper()
        arxiv_url = paper.get('arxiv_url', f'https://arxiv.org/abs/{paper_id}')
        pdf_url = paper.get('pdf_url', f'https://arxiv.org/pdf/{paper_id}')
        reasons = paper.get('reasons', [])
        categories = paper.get('categories', [])
        summary = paper.get('summary_cn', '')

        if score >= 0.7:
            score_class = 'score-high'
        elif score >= 0.5:
            score_class = 'score-mid'
        else:
            score_class = 'score-low'

        if authors:
            author_str = ", ".join(authors[:4])
            if len(authors) > 4:
                author_str += f" 等 ({len(authors)} 位作者)"
        else:
            author_str = "未知作者"

        cat_tags = ""
        for cat in categories[:3]:
            cat_tags += f'<span class="tag">{cat}</span> '

        reasons_html = ""
        if reasons:
            reasons_html = f'<div class="paper-reasons">{" &middot; ".join(reasons)}</div>'

        compact_class = " compact" if compact else ""
        abstract_len = 300 if compact else 500
        abstract_display = abstract[:abstract_len] + ("..." if len(abstract) > abstract_len else "")

        # If Chinese summary exists, show it instead of raw abstract
        abstract_section = ""
        if summary:
            abstract_section = f'<div class="paper-abstract"><strong>中文简述：</strong>{summary}</div>'
            if not compact:
                abstract_section += f'<details><summary>查看英文原文摘要</summary><div class="paper-abstract" style="margin-top:6px">{abstract_display}</div></details>'
        else:
            abstract_section = f'<div class="paper-abstract">{abstract_display}</div>'

        return f"""
    <div class="paper-card{compact_class}">
        <div>
            <span class="paper-rank">{rank}</span>
            <span class="paper-title"><a href="{arxiv_url}" target="_blank">{title}</a></span>
        </div>
        <div class="paper-meta">
            <span class="score-badge {score_class}">相关度: {score:.3f}</span>
            <span class="tag">{source}</span>
            {cat_tags}
        </div>
        <div class="paper-authors">{author_str}</div>
        {abstract_section}
        {reasons_html}
        <div class="paper-links">
            <a href="{arxiv_url}" target="_blank">arXiv 页面</a>
            <a href="{pdf_url}" target="_blank">PDF 下载</a>
        </div>
    </div>"""

    def _render_history_nav(self, current_date: str, page_type: str = 'daily') -> str:
        """Render navigation links to previous dates"""
        links = f'<a href="index.html" class="active">{current_date}</a>'

        docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs')
        if os.path.exists(docs_dir):
            for f in sorted(os.listdir(docs_dir), reverse=True):
                if f.startswith('2') and f.endswith('.html') and f != 'index.html':
                    date_str = f.replace('.html', '')
                    links = f'<a href="{f}">{date_str}</a> ' + links

        return f'<nav class="history-nav">{links}</nav>'

    def save_daily(self, recommendations: List[Dict], output_path: str, date: str = None) -> None:
        """Generate and save daily HTML"""
        html = self.generate_daily_html(recommendations, date)

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        if date:
            date_path = os.path.join(os.path.dirname(output_path), f'{date}.html')
            with open(date_path, 'w', encoding='utf-8') as f:
                f.write(html)

        json_path = os.path.join(os.path.dirname(output_path), f'{date or "latest"}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, ensure_ascii=False, indent=2, default=str)

        print(f"每日页面已保存到 {output_path}")

    def save_top100(self, papers: List[Dict], output_path: str, year: str = None) -> None:
        """Generate and save top 100 yearly HTML"""
        html = self.generate_top100_html(papers, year)

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        json_path = os.path.join(os.path.dirname(output_path), 'top100.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(papers[:100], f, ensure_ascii=False, indent=2, default=str)

        print(f"年度 Top100 页面已保存到 {output_path}")
