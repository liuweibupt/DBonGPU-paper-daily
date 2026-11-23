"""Render the GPU database and computer architecture paper collections."""

import json
from datetime import date as calendar_date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlsplit


BEIJING_TIME = timezone(timedelta(hours=8))
COLLECTIONS = (
    ('daily', 'index.html', '每日推荐'),
    ('top100', 'top100.html', '年度 Top 100'),
    ('classics', 'classics.html', '经典论文'),
)
GITHUB_URL = 'https://github.com/liuweibupt/DBonGPU-paper-daily'


class HTMLDisplay:
    """Generate both collections using the same page and paper templates."""

    def __init__(self, feed: str = 'db'):
        self.is_architecture = feed == 'architecture'
        self.subject = '计算机体系结构' if self.is_architecture else 'GPU 数据库'
        self.title = f'{self.subject}论文日报'
        self.arxiv_categories = 'cs.AR' if self.is_architecture else 'cs.AR / cs.DB / cs.DC'

    def generate_daily_html(self, recommendations: List[Dict], date: str = None, all_dates: List[str] = None) -> str:
        """Render a daily issue and its date navigation."""
        date = date or datetime.now(BEIJING_TIME).date().isoformat()
        description = (
            '最近 7 天在 arXiv cs.AR 提交的体系结构论文，含交叉分类。按首次提交时间倒序。'
            if self.is_architecture else '最近 7 天的 arXiv 新论文，按 GPU 加速数据库主题相关度排序。'
        )
        return self._render_page(
            'daily',
            self.title,
            description,
            recommendations,
            [(date, '日报日期')],
            archive=self._render_date_nav(date, all_dates),
            document_title=f'{self.title} - {date}',
        )

    def generate_top100_html(self, papers: List[Dict], year: str = None, *, coverage: str = None) -> str:
        """Render the annual relevance ranking for the selected collection."""
        year = str(year or datetime.now(BEIJING_TIME).year)
        description = (
            '在 arXiv cs.AR 的过去 365 天投稿中，按主分类及题名、摘要的体系结构主题匹配排序。'
            if self.is_architecture else
            f'从 arXiv {self.arxiv_categories} 选取研究论文，按 GPU 加速数据库主题相关度排序。'
        )
        stats = [(year, '榜单年份')]
        if coverage:
            stats.append((coverage, '投稿日期范围'))
        else:
            stats.append(('过去 12 个月', '投稿日期范围'))
        return self._render_page(
            'top100', f'{self.subject}年度 Top 100', description, papers[:100], stats
        )

    def generate_classics_html(self, papers: List[Dict]) -> str:
        """Render a curated list of classic papers."""
        description = (
            '收录处理器、存储层次、互连与专用加速器等方向的代表性工作。'
            if self.is_architecture else '收录 GPU 加速数据库领域及相关数据处理技术的代表性工作。'
        )
        years = [str(paper['year']) for paper in papers if paper.get('year')]
        span = f'{min(years)} 至 {max(years)}' if len(set(years)) > 1 else next(iter(years), '')
        stats = [(span, '出版年份')] if span else []
        return self._render_page('classics', f'{self.subject}经典论文', description, papers, stats)

    def _render_page(self, collection, title, description, papers, stats, *, archive='', document_title=None):
        display_title = escape(title)
        rendered_at = datetime.now(BEIJING_TIME)
        theme = 'architecture' if self.is_architecture else 'db'
        stat_html = '\n'.join(
            f'<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>'
            for value, label in [(str(len(papers)), '收录论文'), *stats]
        )
        cards = '\n'.join(
            self._render_paper_card(paper, index, collection)
            for index, paper in enumerate(papers, 1)
        )
        if not cards:
            cards = '<p class="empty-state">本期暂无符合条件的论文。</p>'
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(document_title or title)}</title>
    {self._common_styles()}
</head>
<body class="{theme}">
    <a class="skip-nav" href="#main">跳到论文列表</a>
    {self._render_navigation(collection)}
    <main class="page" id="main">
        <section class="intro">
            <div class="intro-text">
                <h1>{display_title}</h1>
                <p>{escape(description)}</p>
            </div>
            <dl class="stats">{stat_html}</dl>
        </section>
        {archive}
        <div class="paper-list {collection}">
            {cards}
        </div>
    </main>
    <footer class="page">
        <span>Paper Daily</span>
        <span>页面生成于 <time datetime="{rendered_at.isoformat(timespec='minutes')}">{rendered_at:%Y-%m-%d %H:%M}</time>（北京时间）</span>
    </footer>
</body>
</html>"""

    def _render_navigation(self, collection):
        active_file = next(path for key, path, _ in COLLECTIONS if key == collection)
        if self.is_architecture:
            db_path, architecture_path = f'../{active_file}', active_file
        else:
            db_path, architecture_path = active_file, f'architecture/{active_file}'
        db_current = '' if self.is_architecture else ' aria-current="true"'
        architecture_current = ' aria-current="true"' if self.is_architecture else ''
        subnav = '\n            '.join(
            f'<a href="{path}"{self._current_page(key, collection)}>{label}</a>'
            for key, path, label in COLLECTIONS
        )
        return f"""<header class="site-header">
        <div class="page masthead">
            <nav class="feed-nav" aria-label="选择领域">
                <a href="{db_path}"{db_current}>GPU 数据库</a>
                <a href="{architecture_path}"{architecture_current}>计算机体系结构</a>
            </nav>
            <a class="github-link" href="{GITHUB_URL}" target="_blank" rel="noopener">GitHub ↗</a>
        </div>
        <div class="subnav-wrap">
            <nav class="page subnav" aria-label="{self.subject}栏目">
            {subnav}
            </nav>
        </div>
    </header>"""

    @staticmethod
    def _current_page(key, current):
        return ' aria-current="page"' if key == current else ''

    def _render_date_nav(self, current_date: str, all_dates: List[str] = None) -> str:
        if all_dates is None:
            all_dates = self._scan_available_dates()
        dates = sorted(set(all_dates) | {current_date}, reverse=True)
        recent = dates[:7]
        if current_date not in recent:
            recent.append(current_date)
        remaining = [date for date in dates if date not in recent]
        links = '\n'.join(self._archive_link(date, current_date) for date in recent)
        more = ''
        if remaining:
            older = '\n'.join(self._archive_link(date, current_date) for date in remaining)
            more = f"""<details class="archive-more">
                <summary>更多日期</summary>
                <div class="archive-links">{older}</div>
            </details>"""
        return f"""<nav class="archive" aria-label="{self.subject}日报归档">
            <span class="archive-label">日报归档</span>
            <div class="archive-links">{links}</div>
            {more}
        </nav>"""

    def _archive_link(self, date, current_date):
        return f'<a href="{escape(date)}.html"{self._current_page(date, current_date)}>{escape(date)}</a>'

    def _render_paper_card(self, paper, rank, collection):
        title = escape(paper.get('title') or '无标题')
        links = self._paper_links(paper, collection)
        if links:
            title = f'<a href="{links[0][1]}" target="_blank" rel="noopener">{title}</a>'
        authors = paper.get('authors') or []
        author_text = ', '.join(escape(author) for author in authors[:4])
        if len(authors) > 4:
            author_text += f' 等 {len(authors)} 人'
        metadata = self._render_paper_metadata(paper, collection)
        link_html = '\n'.join(
            f'<a href="{url}" target="_blank" rel="noopener">{label} <span aria-hidden="true">↗</span></a>'
            for label, url in links
        )
        reasons_html = ''
        if paper.get('reasons'):
            reasons = ' · '.join(map(escape, paper['reasons']))
            reasons_html = f'<p class="paper-reasons">{reasons}</p>'
        heading = f'<h2 class="paper-title">{title}</h2>'
        if collection != 'classics':
            heading = f"""<div class="paper-heading">
                <span class="paper-rank" aria-label="第 {rank} 篇">{rank:02d}</span>
                {heading}
            </div>"""
        return f"""<article class="paper-card">
            {heading}
            <div class="paper-meta">{metadata}</div>
            <p class="paper-authors">{author_text}</p>
            {self._render_abstracts(paper)}
            {self._render_notes(paper)}
            {reasons_html}
            <div class="paper-links">{link_html}</div>
        </article>"""

    def _render_paper_metadata(self, paper, collection):
        tags = []
        if collection == 'classics':
            for value in (paper.get('venue'), paper.get('year'), *(paper.get('topics') or [])):
                if value:
                    tags.append(self._tag(str(value)))
        else:
            submitted = (paper.get('published_date') or '')[:10]
            if submitted:
                tags.append(self._tag(f'arXiv 提交 {submitted}'))
            categories = paper.get('categories') or []
            if self.is_architecture and 'cs.AR' in categories:
                categories = ['cs.AR'] + [category for category in categories if category != 'cs.AR']
            tags.extend(self._tag(category) for category in categories[:3])
            score = paper.get('score')
            if isinstance(score, (int, float)):
                tags.append(f'<span class="score-badge">主题相关度 {score:.3f}</span>')
        return ' '.join(tags)

    @staticmethod
    def _tag(value):
        return f'<span class="tag">{escape(value)}</span>'

    def _render_abstracts(self, paper):
        english = paper.get('abstract') or ''
        translation = paper.get('abstract_cn') or ''
        summary = paper.get('summary_cn') or ''
        is_keyword_summary = paper.get('summary_method') == 'keywords'
        if translation.startswith('本文研究') and '\n\n核心内容：' in translation:
            # Legacy GPU DB keyword summaries combine a Chinese topic line with an English excerpt.
            summary = translation.partition('\n\n核心内容：')[0]
            translation = ''
            is_keyword_summary = True
        if summary:
            label = '主题提示' if is_keyword_summary else '中文摘要'
            html = self._abstract_block(label, summary, 'paper-abstract-cn')
            if translation:
                html += self._abstract_details('查看中文译文', translation)
            if english:
                html += self._abstract_details('查看英文原文摘要', english)
            return html
        if translation:
            marker = '机器翻译' if paper.get('enrichment_method') == 'local_abstract_translation' else ''
            html = self._abstract_block('中文摘要', translation, 'paper-abstract-cn', marker=marker)
            if english:
                html += self._abstract_details('查看英文原文摘要', english)
            return html
        if english:
            return self._abstract_details('英文原文摘要', english, expanded=True)
        return ''

    @staticmethod
    def _abstract_block(label, value, css_class, *, marker=''):
        suffix = f'<span class="translation-note">{marker}</span>' if marker else ''
        return f'<div class="{css_class}"><h3>{label}{suffix}</h3><p>{escape(value)}</p></div>'

    @staticmethod
    def _abstract_details(label, value, *, expanded=False):
        options = ' open' if expanded else ''
        return f'<details class="original-abstract"{options}><summary>{label}</summary><p>{escape(value)}</p></details>'

    @staticmethod
    def _render_notes(paper):
        notes = []
        for field, label in (('takeaway', '核心结论'), ('innovation', '创新点')):
            if paper.get(field):
                notes.append(f'<div><dt>{label}</dt><dd>{escape(paper[field])}</dd></div>')
        if notes:
            return f'<dl class="paper-notes">{"".join(notes)}</dl>'
        return ''

    def _paper_links(self, paper, collection):
        arxiv = self._paper_url(paper.get('arxiv_url'))
        pdf = self._paper_url(paper.get('pdf_url'))
        publisher = self._paper_url(paper.get('publisher_url') or paper.get('url'))
        if collection != 'classics' and paper.get('id') and paper.get('source', 'arxiv') == 'arxiv':
            paper_id = paper['id']
            arxiv = arxiv or self._paper_url(f'https://arxiv.org/abs/{paper_id}')
            pdf = pdf or self._paper_url(f'https://arxiv.org/pdf/{paper_id}')
        doi = paper.get('doi') or ''
        if doi.startswith('10.'):
            doi = f'https://doi.org/{doi}'
        doi = self._paper_url(doi)
        links = []
        for label, url in [('arXiv', arxiv), ('出版页', publisher), ('DOI', doi), ('PDF', pdf)]:
            if url and all(url != existing for _, existing in links):
                links.append((label, url))
        return links

    @staticmethod
    def _paper_url(url):
        if isinstance(url, str):
            try:
                split = urlsplit(url)
            except ValueError:
                return ''
            if split.scheme in ('https', 'http') and split.hostname:
                return escape(url)
        return ''

    def _scan_available_dates(self, output_dir: Path = None) -> List[str]:
        """Find dated HTML archives for the current collection."""
        if output_dir is None:
            output_dir = Path(__file__).resolve().parents[2] / 'docs'
            if self.is_architecture:
                output_dir /= 'architecture'
        dates = []
        for path in output_dir.glob('????-??-??.html'):
            try:
                if path.is_file() and calendar_date.fromisoformat(path.stem).isoformat() == path.stem:
                    dates.append(path.stem)
            except ValueError:
                continue
        return dates

    def save_daily(self, recommendations: List[Dict], output_path: str, date: str = None) -> None:
        """Save the issue and update the latest page when appropriate."""
        date = calendar_date.fromisoformat(date).isoformat() if date else datetime.now(BEIJING_TIME).date().isoformat()
        output = Path(output_path)
        all_dates = set(self._scan_available_dates(output.parent)) | {date}
        html = self.generate_daily_html(recommendations, date, all_dates)
        data = json.dumps(recommendations, ensure_ascii=False, indent=2, default=str)
        output.parent.mkdir(parents=True, exist_ok=True)
        date_path = output.with_name(f'{date}.html')
        date_path.with_suffix('.json').write_text(data, encoding='utf-8')
        self._write_html(date_path, html)
        if output != date_path and (output.name != 'index.html' or date == max(all_dates)):
            self._write_html(output, html)
        print(f'每日页面已保存到 {date_path}')

    def save_top100(self, papers: List[Dict], output_path: str, year: str = None, *, coverage: str = None) -> None:
        """Save the annual ranking and its machine-readable paper list."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._write_html(output, self.generate_top100_html(papers, year, coverage=coverage))
        data = json.dumps(papers[:100], ensure_ascii=False, indent=2, default=str)
        output.with_name('top100.json').write_text(data, encoding='utf-8')
        print(f'年度 Top 100 页面已保存到 {output}')

    def save_classics(self, papers: List[Dict], output_path: str) -> None:
        """Save the curated classics page."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._write_html(output, self.generate_classics_html(papers))
        print(f'经典论文页面已保存到 {output}')

    @staticmethod
    def _write_html(output, html):
        output.write_text('\n'.join(line.rstrip() for line in html.splitlines()) + '\n', encoding='utf-8')

    @staticmethod
    def _common_styles():
        return """<style>
        :root {
            color-scheme: light;
            --page: #f5f7fa;
            --surface: #ffffff;
            --ink: #172232;
            --muted: #516175;
            --line: #dbe3eb;
            --accent: #075c68;
            --tint: #e9f5f3;
            --panel: #eef6f6;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            color: var(--ink);
            background: var(--page);
            font: 16px/1.65 system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
        }
        body.architecture {
            --page: #f8f7fc;
            --line: #e3deee;
            --accent: #563a91;
            --tint: #f1ebfb;
            --panel: #f4f0fb;
        }
        h1, h2, h3, p, dl, dd { margin: 0; }
        a { color: var(--accent); text-decoration: none; }
        a:hover { text-decoration: underline; text-underline-offset: .2em; }
        a:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; }
        .page { width: min(1220px, 100% - 64px); margin: 0 auto; }
        .skip-nav { position: fixed; top: 12px; left: 12px; z-index: 2; transform: translateY(-180%); }
        .skip-nav:focus { transform: none; background: var(--surface); padding: 6px 12px; }
        .site-header { background: var(--surface); border-bottom: 1px solid var(--line); }
        .masthead { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 0; }
        .feed-nav { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
        .feed-nav a { padding: 6px 14px; border: 1px solid transparent; border-radius: 7px; font-weight: 650; }
        .feed-nav a:not([aria-current]) { color: var(--muted); }
        .feed-nav a[aria-current] { background: var(--tint); border-color: var(--line); }
        .github-link { color: var(--muted); white-space: nowrap; font-size: .85rem; }
        .subnav-wrap { border-top: 1px solid var(--line); }
        .subnav { display: flex; align-items: center; gap: 1.65rem; }
        .subnav a { color: var(--muted); white-space: nowrap; padding: 8px 0 7px; border-bottom: 2px solid transparent; font-size: .9rem; }
        .subnav a[aria-current] { color: var(--accent); border-bottom-color: var(--accent); font-weight: 650; }
        main { padding: 32px 0 40px; }
        .intro {
            padding: 25px 28px;
            border: 1px solid var(--line);
            border-inline-start: 4px solid var(--accent);
            border-radius: 10px;
            background: var(--panel);
            display: flex;
            gap: 18px 36px;
            align-items: flex-end;
            justify-content: space-between;
            margin-bottom: 24px;
        }
        h1 { font-size: clamp(1.6rem, 3.8vw, 2.35rem); line-height: 1.2; letter-spacing: -.025em; }
        .intro p { color: var(--muted); margin-top: 9px; font-size: .93rem; }
        .stats { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 8px 22px; flex-shrink: 0; }
        .stats dt { color: var(--muted); font-size: .77rem; }
        .stats dd { font-size: .95rem; font-weight: 650; font-variant-numeric: tabular-nums; }
        .archive { margin: -5px 0 24px; }
        .archive-label { display: block; color: var(--muted); font-size: .84rem; font-weight: 650; margin-bottom: 6px; }
        .archive-links { display: flex; flex-wrap: wrap; gap: 5px; }
        .archive-links a {
            padding: 3px 8px;
            border: 1px solid var(--line);
            border-radius: 5px;
            color: var(--muted);
            background: var(--surface);
            font-size: .83rem;
            font-variant-numeric: tabular-nums;
        }
        .archive-links a[aria-current] { background: var(--tint); color: var(--accent); font-weight: 650; }
        .archive-more { margin-top: 5px; }
        .archive-more[open] > .archive-links { margin-top: 5px; max-height: 14rem; overflow: auto; }
        .paper-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; align-items: start; }
        .paper-card { padding: 18px 20px; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); min-width: 0; }
        .paper-heading { display: grid; grid-template-columns: 2.15rem minmax(0, 1fr); align-items: start; gap: 9px; }
        .paper-rank {
            background: var(--tint);
            color: var(--accent);
            border-radius: 5px;
            font-variant-numeric: tabular-nums;
            font-weight: 650;
            font-size: .77rem;
            padding: 4px 0;
            text-align: center;
        }
        .paper-title { font-size: 1.12rem; line-height: 1.38; letter-spacing: -.008em; overflow-wrap: anywhere; }
        .paper-title a { color: var(--ink); }
        .paper-title a:hover { color: var(--accent); }
        .paper-meta, .paper-links { display: flex; flex-wrap: wrap; gap: 4px 6px; }
        .paper-meta:not(:empty) { margin-top: 9px; }
        .tag, .score-badge {
            border-radius: 4px;
            border: 1px solid var(--line);
            color: var(--muted);
            padding: 0 6px;
            line-height: 1.65;
            font-size: .76rem;
        }
        .score-badge { background: var(--tint); color: var(--accent); font-weight: 600; }
        .paper-authors, .paper-reasons { color: var(--muted); font-size: .82rem; margin-top: 7px; overflow-wrap: anywhere; }
        .paper-authors:empty { display: none; }
        .paper-abstract-cn {
            padding: 10px 12px;
            background: var(--panel);
            border-radius: 5px;
            margin-top: 12px;
        }
        .paper-abstract-cn h3, .paper-notes dt { color: var(--accent); font-size: .83rem; font-weight: 700; }
        .translation-note { color: var(--muted); font-size: .75rem; font-weight: 500; margin-inline-start: .65rem; }
        .paper-abstract-cn p, .original-abstract p, .paper-notes dd {
            font-size: .91rem;
            margin-top: 3px;
            white-space: pre-line;
            overflow-wrap: anywhere;
        }
        .original-abstract { margin: 6px 0; }
        summary { width: fit-content; color: var(--accent); font-size: .85rem; font-weight: 600; cursor: pointer; padding: 4px 0; }
        summary:hover { text-decoration: underline; text-underline-offset: .2em; }
        .original-abstract p { border-inline-start: 2px solid var(--line); padding-inline-start: 11px; color: var(--muted); }
        .paper-notes { margin-top: 10px; display: grid; gap: 8px; }
        .paper-notes dd { color: var(--ink); }
        .paper-links:not(:empty) { margin-top: 12px; }
        .paper-links a { font-size: .83rem; font-weight: 650; border: 1px solid var(--line); border-radius: 5px; padding: 2px 9px; }
        .empty-state { grid-column: 1 / -1; background: var(--surface); border: 1px solid var(--line); padding: 26px; border-radius: 10px; }
        footer { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 4px 12px; color: var(--muted); padding: 12px 0 26px; border-top: 1px solid var(--line); font-size: .8rem; }
        @media (max-width: 940px) {
            .intro { align-items: flex-start; flex-direction: column; }
        }
        @media (max-width: 760px) {
            .paper-list { grid-template-columns: 1fr; }
        }
        @media (max-width: 520px) {
            .page { width: calc(100% - 28px); }
            .masthead { gap: 3px 8px; }
            .feed-nav { gap: 2px; }
            .feed-nav a { font-size: .88rem; padding: 5px 6px; }
            .subnav { gap: 1rem; }
            main { padding-top: 16px; }
            .intro { padding: 14px 12px; margin-bottom: 16px; gap: 8px; }
            h1 { font-size: clamp(1.35rem, 5.8vw, 1.6rem); text-wrap: balance; }
            .stats { gap: 5px 14px; }
            .archive { margin: 0 0 14px; }
            .paper-card { padding: 13px; }
        }
    </style>"""
