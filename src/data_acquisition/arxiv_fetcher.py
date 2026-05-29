"""
ArXiv Fetcher for Paper Daily

Fetches papers from arXiv using its API.
Uses category-based fetching with local keyword filtering for robustness.
Falls back to web scraping when the API is rate-limited (429).
"""

import requests
import feedparser
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlencode


class ArxivFetcher:
    """Fetches papers from arXiv API"""
    
    def __init__(self, categories: List[str] = None):
        self.categories = categories or ['cs.AR', 'cs.DB', 'cs.DC']
        self.base_url = "http://export.arxiv.org/api/query"
        self.max_results = 100

    def _request_with_retry(self, url: str, max_retries: int = 3, timeout: int = 60) -> Optional[requests.Response]:
        """Make a request with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    wait = 5 * (2 ** attempt)
                    print(f"Rate limited (429), waiting {wait}s before retry {attempt+1}/{max_retries}...")
                    time.sleep(wait)
                else:
                    print(f"HTTP error: {e}")
                    time.sleep(3)
            except requests.exceptions.RequestException as e:
                print(f"Request error: {e}, retry {attempt+1}/{max_retries}...")
                time.sleep(3 * (attempt + 1))
        return None

    def fetch_papers(self, date: str = None, max_results: int = None) -> List[Dict]:
        """Fetch papers from arXiv for a specific date by category"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        if max_results is None:
            max_results = self.max_results

        papers = []
        for category in self.categories:
            try:
                category_papers = self._fetch_category_papers(category, date, max_results)
                papers.extend(category_papers)
                time.sleep(3)  # Rate limiting between category requests
            except Exception as e:
                print(f"Error fetching papers for category {category}: {e}")
                continue

        return self._remove_duplicates(papers)

    def fetch_recent_papers(self, days: int = 365, max_results_per_category: int = 500) -> List[Dict]:
        """Fetch papers from the last N days across all categories"""
        papers = []
        for category in self.categories:
            try:
                query_params = {
                    'search_query': f'cat:{category}',
                    'start': 0,
                    'max_results': max_results_per_category,
                    'sortBy': 'submittedDate',
                    'sortOrder': 'descending'
                }
                url = f"{self.base_url}?{urlencode(query_params)}"

                response = self._request_with_retry(url)
                if response is None:
                    continue

                feed = feedparser.parse(response.content)
                cutoff_date = (datetime.now() - timedelta(days=days)).date()

                for entry in feed.entries:
                    try:
                        submitted_date = datetime.strptime(entry.published, '%Y-%m-%dT%H:%M:%SZ').date()
                        if submitted_date >= cutoff_date:
                            paper = self._parse_paper_entry(entry, category)
                            papers.append(paper)
                    except (ValueError, AttributeError):
                        continue

                time.sleep(3)
            except Exception as e:
                print(f"Error fetching recent papers for {category}: {e}")
                continue

        return self._remove_duplicates(papers)

    def search_papers_by_keywords(self, keywords: List[str], categories: List[str] = None, max_results: int = 100) -> List[Dict]:
        """
        Search papers using keyword-based query across specified categories.
        Splits keywords into small groups to avoid overly long URLs that trigger 429.
        """
        if categories is None:
            categories = self.categories

        all_papers = []

        # Search each keyword individually to keep queries short and avoid 429
        for kw in keywords:
            cat_parts = [f'cat:{cat}' for cat in categories]
            cat_query = ' OR '.join(cat_parts)
            full_query = f'(ti:"{kw}" OR abs:"{kw}") AND ({cat_query})'

            query_params = {
                'search_query': full_query,
                'start': 0,
                'max_results': max_results,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }

            url = f"{self.base_url}?{urlencode(query_params)}"

            response = self._request_with_retry(url)
            if response is None:
                continue

            try:
                feed = feedparser.parse(response.content)
                for entry in feed.entries:
                    primary_cat = 'search'
                    if hasattr(entry, 'tags') and entry.tags:
                        primary_cat = entry.tags[0].term
                    paper = self._parse_paper_entry(entry, primary_cat)
                    all_papers.append(paper)
            except Exception as e:
                print(f"Error parsing results for keyword '{kw}': {e}")

            time.sleep(3)  # Rate limiting between keyword searches

        return self._remove_duplicates(all_papers)

    def _fetch_category_papers(self, category: str, date: str, max_results: int) -> List[Dict]:
        """Fetch papers for a specific category and date"""
        query_params = {
            'search_query': f'cat:{category}',
            'start': 0,
            'max_results': max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }

        url = f"{self.base_url}?{urlencode(query_params)}"
        response = self._request_with_retry(url)
        if response is None:
            return []

        try:
            feed = feedparser.parse(response.content)
            target_date = datetime.strptime(date, '%Y-%m-%d').date()

            papers = []
            for entry in feed.entries:
                submitted_date = datetime.strptime(entry.published, '%Y-%m-%dT%H:%M:%SZ').date()
                if submitted_date == target_date:
                    paper = self._parse_paper_entry(entry, category)
                    papers.append(paper)

            return papers
        except Exception as e:
            print(f"Error parsing arXiv response for {category}: {e}")
            return []

    def _parse_paper_entry(self, entry, category: str) -> Dict:
        """Parse a single paper entry from arXiv feed"""
        arxiv_id = entry.id.split('/')[-1]

        authors = []
        if hasattr(entry, 'authors'):
            authors = [author.name for author in entry.authors]
        elif hasattr(entry, 'author'):
            authors = [entry.author]

        pdf_url = None
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.type == 'application/pdf':
                    pdf_url = link.href
                    break

        categories = []
        if hasattr(entry, 'tags'):
            categories = [tag.term for tag in entry.tags]

        paper = {
            'id': arxiv_id,
            'title': entry.title,
            'authors': authors,
            'abstract': entry.summary,
            'published_date': entry.published,
            'updated_date': entry.updated if hasattr(entry, 'updated') else entry.published,
            'categories': categories,
            'primary_category': category,
            'pdf_url': pdf_url,
            'arxiv_url': entry.link,
            'source': 'arxiv'
        }

        return paper

    def _remove_duplicates(self, papers: List[Dict]) -> List[Dict]:
        """Remove duplicate papers based on arXiv ID"""
        seen_ids = set()
        unique_papers = []
        for paper in papers:
            if paper['id'] not in seen_ids:
                seen_ids.add(paper['id'])
                unique_papers.append(paper)
        return unique_papers

    def search_papers(self, query: str, max_results: int = 50) -> List[Dict]:
        """Search papers by query string"""
        query_params = {
            'search_query': query,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }

        url = f"{self.base_url}?{urlencode(query_params)}"
        response = self._request_with_retry(url)
        if response is None:
            return []

        try:
            feed = feedparser.parse(response.content)
            papers = []
            for entry in feed.entries:
                paper = self._parse_paper_entry(entry, 'search')
                papers.append(paper)
            return papers
        except Exception as e:
            print(f"Error searching arXiv papers: {e}")
            return []

    # ------------------------------------------------------------------
    # Web-scraping fallback (used when API returns 429 rate-limit)
    # ------------------------------------------------------------------

    def fetch_papers_via_web(self, date: str = None) -> List[Dict]:
        """
        Fallback: scrape arXiv listing pages for each category when the
        API is rate-limited.  Returns paper dicts with the same schema
        as the API-based methods.
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        all_ids = set()
        for cat in self.categories:
            try:
                url = f'https://arxiv.org/list/{cat}/new'
                resp = requests.get(url, timeout=30,
                                    headers={'User-Agent': 'Mozilla/5.0 (paper-daily)'})
                if resp.status_code != 200:
                    print(f"Web scrape for {cat}: HTTP {resp.status_code}")
                    continue
                ids = re.findall(r'/abs/(\d+\.\d+)', resp.text)
                print(f"Web scrape {cat}: found {len(ids)} paper IDs")
                all_ids.update(ids)
                time.sleep(1)
            except Exception as e:
                print(f"Web scrape for {cat}: {e}")

        # Filter IDs that match the target date prefix
        # arXiv IDs use YYMM.NNNNN format; e.g. 2605.29xxx = May 2026
        year = date[2:4]   # e.g. '26'
        month = date[5:7]  # e.g. '05'
        prefix = f'{year}{month}'
        recent_ids = sorted(pid for pid in all_ids if pid.startswith(prefix))

        if not recent_ids:
            # If no exact-prefix match, take all IDs from the listing
            recent_ids = sorted(all_ids)

        print(f"Scraping details for {len(recent_ids)} papers …")
        papers = []
        for pid in recent_ids:
            try:
                paper = self._scrape_paper_page(pid)
                if paper:
                    papers.append(paper)
                time.sleep(1.5)
            except Exception as e:
                print(f"  {pid}: scrape error – {e}")
                time.sleep(2)

        return self._remove_duplicates(papers)

    def _scrape_paper_page(self, arxiv_id: str) -> Optional[Dict]:
        """Scrape a single paper's abs page for metadata."""
        url = f'https://arxiv.org/abs/{arxiv_id}'
        resp = requests.get(url, timeout=30,
                            headers={'User-Agent': 'Mozilla/5.0 (paper-daily)'})
        if resp.status_code != 200:
            return None

        text = resp.text

        # Title
        title_match = re.search(
            r'<h1\s+class="title\s+mathjax">(.*?)</h1>', text, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ''
        title = re.sub(r'<.*?>', '', title).strip()
        title = re.sub(r'^Title:\s*', '', title).strip()

        # Abstract
        abs_match = re.search(
            r'<blockquote\s+class="abstract\s+mathjax">(.*?)</blockquote>',
            text, re.DOTALL)
        abstract = abs_match.group(1).strip() if abs_match else ''
        abstract = re.sub(r'<.*?>', '', abstract).strip()
        abstract = re.sub(r'^Abstract:\s*', '', abstract).strip()
        abstract = re.sub(r'&#39;', "'", abstract)
        abstract = re.sub(r'&amp;', '&', abstract)
        abstract = re.sub(r'&lt;', '<', abstract)
        abstract = re.sub(r'&gt;', '>', abstract)
        abstract = re.sub(r'\s+', ' ', abstract).strip()

        # Authors
        authors_match = re.search(
            r'<div\s+class="authors">(.*?)</div>', text, re.DOTALL)
        authors = []
        if authors_match:
            authors = re.findall(r'>([^<]+)<', authors_match.group(1))
            authors = [a.strip() for a in authors
                       if a.strip() and a.strip() != 'Authors:']

        # Primary category
        cat_match = re.search(
            r'<span\s+class="primary-subject">(.*?)</span>', text)
        primary_cat = cat_match.group(1).strip() if cat_match else ''

        if not title or not abstract:
            return None

        return {
            'id': arxiv_id,
            'title': title,
            'authors': authors,
            'abstract': abstract,
            'published_date': '',
            'updated_date': '',
            'categories': [primary_cat] if primary_cat else [],
            'primary_category': primary_cat,
            'pdf_url': f'https://arxiv.org/pdf/{arxiv_id}',
            'arxiv_url': f'https://arxiv.org/abs/{arxiv_id}',
            'source': 'arxiv'
        }
