#!/usr/bin/env python3
"""
Local script to enrich existing paper JSON data with Chinese translations,
AI takeaway and innovation points, then regenerate all HTML pages.

Uses the translator module if API key is available, otherwise generates
keyword-based fallback content.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from display.html_display import HTMLDisplay
from analysis.translator import PaperTranslator


def main():
    docs_dir = os.path.join(os.path.dirname(__file__), 'docs')
    html_display = HTMLDisplay()
    translator = PaperTranslator()

    if translator.enabled:
        print(f"API key found, using model: {translator.model}")
        print(f"API base: {translator.api_base}")
    else:
        print("No API key configured. Using keyword-based fallback.")
        from analysis.keyword_fallback import generate_fallback_cn

    # Collect all JSON files to process
    json_files = []

    # Daily pages
    for filename in sorted(os.listdir(docs_dir)):
        if filename.startswith('20') and filename.endswith('.json'):
            json_files.append(('daily', os.path.join(docs_dir, filename)))

    # Top100
    top100_json = os.path.join(docs_dir, 'top100.json')
    if os.path.exists(top100_json):
        json_files.append(('top100', top100_json))

    # Translate and enrich each file
    for file_type, json_path in json_files:
        date_or_type = os.path.basename(json_path).replace('.json', '')
        print(f"\nProcessing {file_type}: {date_or_type}...")

        with open(json_path, 'r', encoding='utf-8') as f:
            papers = json.load(f)

        if not papers:
            print(f"  No papers found, skipping.")
            continue

        # Translate/enrich papers
        needs_save = False
        for i, paper in enumerate(papers):
            if not paper.get('abstract_cn') or paper.get('abstract_cn', '').startswith('本文研究'):
                if translator.enabled:
                    print(f"  Translating {i+1}/{len(papers)}: {paper.get('title', '')[:60]}...")
                    translator.translate_and_summarize(paper)
                    needs_save = True
                    import time
                    time.sleep(0.5)
                else:
                    generate_fallback_cn(paper)
                    needs_save = True

        if needs_save:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(papers, f, ensure_ascii=False, indent=2, default=str)
            print(f"  Saved enriched JSON: {json_path}")

        # Generate HTML
        if file_type == 'daily':
            all_dates = _scan_dates(docs_dir)
            html = html_display.generate_daily_html(papers, date_or_type, all_dates)
            html_path = os.path.join(docs_dir, f'{date_or_type}.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  Saved HTML: {html_path}")
        elif file_type == 'top100':
            html = html_display.generate_top100_html(papers)
            html_path = os.path.join(docs_dir, 'top100.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  Saved HTML: {html_path}")

    # Regenerate index.html from latest date
    date_files = [f for f in os.listdir(docs_dir) if f.startswith('20') and f.endswith('.json')]
    if date_files:
        latest_date = sorted([f.replace('.json', '') for f in date_files])[-1]
        json_path = os.path.join(docs_dir, f'{latest_date}.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            papers = json.load(f)

        all_dates = _scan_dates(docs_dir)
        html = html_display.generate_daily_html(papers, latest_date, all_dates)
        index_path = os.path.join(docs_dir, 'index.html')
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\nRegenerated index.html from {latest_date}")

    # Process classics (already has full Chinese content)
    classics_json = os.path.join(docs_dir, 'classics.json')
    if os.path.exists(classics_json):
        print(f"\nProcessing Classics...")
        with open(classics_json, 'r', encoding='utf-8') as f:
            papers = json.load(f)
        html = html_display.generate_classics_html(papers)
        classics_path = os.path.join(docs_dir, 'classics.html')
        with open(classics_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  Saved {classics_path}")

    print("\nDone! All pages enriched and regenerated.")


def _scan_dates(docs_dir: str) -> list:
    """Scan available date HTML files"""
    from datetime import datetime
    all_dates = []
    for fn in os.listdir(docs_dir):
        if fn.startswith('20') and fn.endswith('.html') and fn != 'top100.html':
            try:
                d = fn.replace('.html', '')
                datetime.strptime(d, '%Y-%m-%d')
                all_dates.append(d)
            except ValueError:
                continue
    return sorted(set(all_dates))


if __name__ == '__main__':
    main()
