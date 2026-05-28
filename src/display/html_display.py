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

    def generate_daily_html(self, recommendations: List[Dict], date: str = None, all_dates: List[str] = None) -> str:
        """Generate daily paper recommendation HTML page"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        papers_html = ""
        if recommendations:
            for i, paper in enumerate(recommendations, 1):
                papers_html += self._render_paper_card(paper, i)
        else:
            papers_html = """
            <div class="empty-state">
                <div class="empty-icon">📭</div>
                <div class="empty-text">今日暂无符合条件的 GPU 数据库论文</div>
                <div class="empty-hint">arXiv 可能在当天尚未发布新论文，请稍后再试</div>
            </div>"""

        history_html = self._render_date_nav(date, all_dates)

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
    <nav class="top-nav">
        <div class="nav-brand">⚡ GPU DB Daily</div>
        <div class="nav-links">
            <a href="index.html" class="active">每日推荐</a>
            <a href="top100.html">年度 Top 100</a>
            <a href="https://github.com/liuweibupt/DBonGPU-paper-daily" target="_blank">GitHub</a>
        </div>
    </nav>

    <section class="hero">
        <h1>GPU 数据库论文日报</h1>
        <p class="hero-desc">自动追踪 GPU 加速数据库领域最新研究进展</p>
        <div class="hero-date">{date}</div>
    </section>

    {history_html}

    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-value">{len(recommendations)}</div>
            <div class="stat-label">推荐论文</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{high_relevance}</div>
            <div class="stat-label">高相关度</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{date}</div>
            <div class="stat-label">更新日期</div>
        </div>
    </div>

    <div class="paper-list">
        {papers_html}
    </div>

    <footer>
        <div class="footer-content">
            <span>由 Paper Daily 自动生成（GPU DB 聚焦版）</span>
            <span class="footer-sep">·</span>
            <span>上次运行：{generated_time}</span>
            <span class="footer-sep">·</span>
            <span>数据来源：arXiv cs.AR / cs.DB / cs.DC</span>
        </div>
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
            padding: 40px 0 20px;
        }}
        .yearly-hero h2 {{
            font-size: 1.8em;
            color: var(--accent);
            margin-bottom: 8px;
        }}
        .yearly-hero p {{
            color: var(--text-secondary);
            font-size: 1em;
        }}
    </style>
</head>
<body>
    <nav class="top-nav">
        <div class="nav-brand">⚡ GPU DB Daily</div>
        <div class="nav-links">
            <a href="index.html">每日推荐</a>
            <a href="top100.html" class="active">年度 Top 100</a>
            <a href="https://github.com/liuweibupt/DBonGPU-paper-daily" target="_blank">GitHub</a>
        </div>
    </nav>

    <div class="yearly-hero">
        <h2>{year} 年度 GPU 数据库热门论文</h2>
        <p>基于 arXiv 过去一年 cs.AR / cs.DB / cs.DC 领域论文，按 GPU 数据库相关度排序</p>
    </div>

    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-value">{len(display_papers)}</div>
            <div class="stat-label">入选论文</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{high_relevance}</div>
            <div class="stat-label">高相关度</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{mid_relevance}</div>
            <div class="stat-label">中等相关度</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{year}</div>
            <div class="stat-label">统计年份</div>
        </div>
    </div>

    <div class="paper-list">
        {papers_html}
    </div>

    <footer>
        <div class="footer-content">
            <span>由 Paper Daily 自动生成（GPU DB 聚焦版）</span>
            <span class="footer-sep">·</span>
            <span>上次运行：{generated_time}</span>
            <span class="footer-sep">·</span>
            <span>数据来源：arXiv cs.AR / cs.DB / cs.DC</span>
        </div>
    </footer>
</body>
</html>"""

    def _common_styles(self) -> str:
        """Common CSS styles shared across pages"""
        return """<style>
        :root {
            --bg: #0a0e17;
            --bg-secondary: #111827;
            --card-bg: #151d2e;
            --card-hover: #1a2540;
            --border: #1e2d4a;
            --border-hover: #2d4a7a;
            --text: #e2e8f0;
            --text-secondary: #8892a8;
            --text-dim: #5a6480;
            --accent: #60a5fa;
            --accent-bright: #93c5fd;
            --accent-green: #34d399;
            --accent-orange: #fbbf24;
            --accent-red: #f87171;
            --accent-purple: #a78bfa;
            --gradient-1: linear-gradient(135deg, #60a5fa, #34d399);
            --gradient-2: linear-gradient(135deg, #60a5fa, #a78bfa);
            --shadow: 0 4px 24px rgba(0,0,0,0.3);
            --shadow-hover: 0 8px 32px rgba(0,0,0,0.4);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }

        /* Top Navigation */
        .top-nav {
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 24px;
            background: rgba(10,14,23,0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border);
        }
        .nav-brand {
            font-weight: 700;
            font-size: 1.1em;
            color: var(--accent);
        }
        .nav-links {
            display: flex;
            gap: 8px;
        }
        .nav-links a {
            color: var(--text-secondary);
            text-decoration: none;
            padding: 6px 16px;
            border-radius: 8px;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        .nav-links a:hover {
            color: var(--text);
            background: rgba(96,165,250,0.1);
        }
        .nav-links a.active {
            color: var(--accent);
            background: rgba(96,165,250,0.15);
        }

        /* Hero */
        .hero {
            text-align: center;
            padding: 60px 24px 30px;
            max-width: 800px;
            margin: 0 auto;
        }
        .hero h1 {
            font-size: 2.4em;
            font-weight: 800;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 12px;
            letter-spacing: -0.02em;
        }
        .hero-desc {
            color: var(--text-secondary);
            font-size: 1.15em;
            margin-bottom: 16px;
        }
        .hero-date {
            display: inline-block;
            background: rgba(96,165,250,0.12);
            color: var(--accent-bright);
            padding: 6px 20px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 1.1em;
            border: 1px solid rgba(96,165,250,0.2);
        }

        /* Date Navigation */
        .date-nav {
            display: flex;
            gap: 8px;
            justify-content: center;
            flex-wrap: wrap;
            padding: 0 24px;
            margin-bottom: 30px;
        }
        .date-nav a {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 6px 16px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.88em;
            transition: all 0.2s;
        }
        .date-nav a:hover {
            border-color: var(--accent);
            color: var(--accent);
            background: rgba(96,165,250,0.08);
        }
        .date-nav a.active {
            border-color: var(--accent);
            color: var(--accent);
            background: rgba(96,165,250,0.15);
            font-weight: 600;
        }

        /* Stats */
        .stats-row {
            display: flex;
            gap: 16px;
            justify-content: center;
            margin: 0 auto 36px;
            padding: 0 24px;
            flex-wrap: wrap;
            max-width: 800px;
        }
        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 28px;
            text-align: center;
            min-width: 120px;
            transition: border-color 0.2s;
        }
        .stat-card:hover {
            border-color: var(--border-hover);
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: 700;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-label {
            font-size: 0.82em;
            color: var(--text-dim);
            margin-top: 4px;
        }

        /* Paper List */
        .paper-list {
            max-width: 860px;
            margin: 0 auto;
            padding: 0 24px;
        }

        /* Paper Card */
        .paper-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 16px;
            transition: all 0.25s ease;
            position: relative;
        }
        .paper-card:hover {
            border-color: var(--border-hover);
            background: var(--card-hover);
            box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }
        .paper-card.compact {
            padding: 18px 22px;
        }

        .paper-header {
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }
        .paper-rank {
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            border-radius: 10px;
            font-weight: 700;
            font-size: 0.9em;
            color: #fff;
            background: var(--gradient-1);
        }
        .compact .paper-rank {
            width: 28px;
            height: 28px;
            font-size: 0.8em;
            border-radius: 8px;
        }
        .paper-title {
            font-size: 1.12em;
            font-weight: 600;
            line-height: 1.5;
        }
        .compact .paper-title {
            font-size: 1.0em;
        }
        .paper-title a {
            color: var(--text);
            text-decoration: none;
            transition: color 0.2s;
        }
        .paper-title a:hover {
            color: var(--accent);
        }

        .paper-meta {
            margin-top: 10px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
        }
        .score-badge {
            display: inline-flex;
            align-items: center;
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 0.82em;
            font-weight: 600;
        }
        .score-high { background: rgba(52,211,153,0.12); color: var(--accent-green); }
        .score-mid { background: rgba(251,191,36,0.12); color: var(--accent-orange); }
        .score-low { background: rgba(90,100,128,0.15); color: var(--text-dim); }

        .tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 5px;
            font-size: 0.78em;
            background: rgba(96,165,250,0.08);
            color: var(--accent);
            border: 1px solid rgba(96,165,250,0.15);
        }

        .paper-authors {
            color: var(--text-secondary);
            font-size: 0.88em;
            margin-top: 8px;
        }

        .paper-abstract {
            color: var(--text-secondary);
            font-size: 0.92em;
            margin-top: 12px;
            line-height: 1.75;
        }
        .compact .paper-abstract {
            font-size: 0.86em;
            margin-top: 8px;
        }

        .paper-reasons {
            margin-top: 12px;
            padding: 10px 14px;
            background: rgba(52,211,153,0.06);
            border-left: 3px solid var(--accent-green);
            border-radius: 0 8px 8px 0;
            font-size: 0.88em;
            color: var(--accent-green);
        }

        .paper-links {
            margin-top: 14px;
            display: flex;
            gap: 10px;
        }
        .paper-links a {
            color: var(--accent);
            text-decoration: none;
            font-size: 0.86em;
            padding: 5px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            transition: all 0.2s;
        }
        .paper-links a:hover {
            border-color: var(--accent);
            background: rgba(96,165,250,0.1);
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
        }
        .empty-icon {
            font-size: 3em;
            margin-bottom: 16px;
        }
        .empty-text {
            font-size: 1.2em;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }
        .empty-hint {
            font-size: 0.9em;
            color: var(--text-dim);
        }

        /* Footer */
        footer {
            text-align: center;
            padding: 40px 24px;
            border-top: 1px solid var(--border);
            margin-top: 60px;
            color: var(--text-dim);
            font-size: 0.82em;
        }
        .footer-content {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 4px;
        }
        .footer-sep {
            color: var(--border);
        }
        footer a { color: var(--accent); text-decoration: none; }

        /* Details/Summary */
        details {
            margin-top: 6px;
        }
        details summary {
            cursor: pointer;
            color: var(--text-dim);
            font-size: 0.85em;
            user-select: none;
        }
        details summary:hover {
            color: var(--text-secondary);
        }

        /* Responsive */
        @media (max-width: 640px) {
            .hero { padding: 40px 16px 20px; }
            .hero h1 { font-size: 1.7em; }
            .paper-list { padding: 0 12px; }
            .paper-card { padding: 16px; }
            .paper-title { font-size: 1.02em; }
            .top-nav { padding: 10px 12px; }
            .nav-brand { font-size: 1em; }
            .stats-row { gap: 10px; padding: 0 12px; }
            .stat-card { padding: 12px 18px; min-width: 90px; }
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
        <div class="paper-header">
            <span class="paper-rank">{rank}</span>
            <span class="paper-title"><a href="{arxiv_url}" target="_blank">{title}</a></span>
        </div>
        <div class="paper-meta">
            <span class="score-badge {score_class}">相关度 {score:.3f}</span>
            <span class="tag">{source}</span>
            {cat_tags}
        </div>
        <div class="paper-authors">{author_str}</div>
        {abstract_section}
        {reasons_html}
        <div class="paper-links">
            <a href="{arxiv_url}" target="_blank">📄 arXiv</a>
            <a href="{pdf_url}" target="_blank">⬇ PDF</a>
        </div>
    </div>"""

    def _render_date_nav(self, current_date: str, all_dates: List[str] = None) -> str:
        """Render navigation links to previous dates"""
        if all_dates is None:
            all_dates = self._scan_available_dates()

        links = ""
        for d in sorted(all_dates, reverse=True):
            is_active = (d == current_date)
            href = f"{d}.html"
            active_class = " active" if is_active else ""
            links += f'<a href="{href}" class="{active_class.strip()}">{d}</a>'

        if not links:
            links = f'<a href="index.html" class="active">{current_date}</a>'

        return f'<nav class="date-nav">{links}</nav>'

    def _scan_available_dates(self) -> List[str]:
        """Scan docs directory for available date HTML files"""
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs')
        dates = []
        if os.path.exists(docs_dir):
            for f in os.listdir(docs_dir):
                if f.startswith('20') and f.endswith('.html') and f != 'top100.html':
                    date_str = f.replace('.html', '')
                    # Validate date format
                    try:
                        datetime.strptime(date_str, '%Y-%m-%d')
                        dates.append(date_str)
                    except ValueError:
                        continue
        return sorted(set(dates))

    def save_daily(self, recommendations: List[Dict], output_path: str, date: str = None) -> None:
        """Generate and save daily HTML"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # Scan for all available dates
        all_dates = self._scan_available_dates()
        if date not in all_dates:
            all_dates.append(date)

        html = self.generate_daily_html(recommendations, date, all_dates)

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        # Save as index.html (always shows latest)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        # Save as date-specific page
        date_path = os.path.join(os.path.dirname(output_path), f'{date}.html')
        with open(date_path, 'w', encoding='utf-8') as f:
            f.write(html)

        # Save JSON data
        json_path = os.path.join(os.path.dirname(output_path), f'{date}.json')
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
