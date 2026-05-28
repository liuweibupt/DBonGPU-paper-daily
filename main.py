#!/usr/bin/env python3
"""
Paper Daily - Main Entry Point

This is the main entry point for the Paper Daily application.
It supports daily, top100, CLI and web interfaces.
"""

import click
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.config_manager import ConfigManager
from utils.logger import Logger
from data_acquisition.arxiv_fetcher import ArxivFetcher
from data_acquisition.openreview_fetcher import OpenReviewFetcher
from parsing.pdf_parser import PDFParser
from parsing.text_cleaner import TextCleaner
from embedding.embedder import Embedder
from analysis.recommender import Recommender
from analysis.translator import PaperTranslator
from display.cli_display import CLIDisplay
from display.web_display import WebDisplay
from display.html_display import HTMLDisplay

# Shared GPU DB keywords
GPU_DB_KEYWORDS = [
    'GPU database',
    'GPU-accelerated',
    'GPU query processing',
    'GPU data processing',
    'GPU hash join',
    'GPU in-memory',
    'CUDA database',
    'GPU analytics',
    'GPU sorting',
    'GPU indexing',
]

GPU_DB_CATEGORIES = ['cs.AR', 'cs.DB', 'cs.DC']


@click.command()
@click.option('--web', is_flag=True, help='Launch web interface')
@click.option('--cli', is_flag=True, help='Use command line interface')
@click.option('--html', 'gen_html', is_flag=True, help='Generate static HTML page')
@click.option('--top100', is_flag=True, help='Generate top 100 yearly papers page')
@click.option('--output', default='docs/index.html', help='Output HTML file path')
@click.option('--config', default='config.json', help='Config file path')
@click.option('--date', default=None, help='Specific date to fetch papers (YYYY-MM-DD)')
def main(web, cli, gen_html, top100, output, config, date):
    """GPU 数据库论文日报 - 自动追踪 GPU 加速数据库领域最新研究"""

    config_manager = ConfigManager(config)
    logger = Logger("paper_daily.log")

    logger.log("Starting Paper Daily application", "INFO")

    if web:
        logger.log("Launching web interface", "INFO")
        web_display = WebDisplay()
        web_display.run()
    elif cli:
        run_cli_mode(config_manager, logger, date)
    elif top100:
        run_top100_pipeline(logger, output)
    else:
        run_daily_pipeline(config_manager, logger, date, gen_html=gen_html, output=output)


def run_daily_pipeline(config_manager, logger, date=None, gen_html=False, output='docs/index.html'):
    """Run the complete daily paper processing pipeline"""

    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    logger.log(f"Running daily pipeline for date: {date}", "INFO")

    try:
        arxiv_fetcher = ArxivFetcher(GPU_DB_CATEGORIES)

        papers = arxiv_fetcher.search_papers_by_keywords(
            keywords=GPU_DB_KEYWORDS,
            categories=GPU_DB_CATEGORIES,
            max_results=200
        )
        logger.log(f"Fetched {len(papers)} papers from arXiv", "INFO")

        recommender = Recommender()
        recommendations = recommender.recommend(papers, top_k=10)

        # Translate abstracts and generate AI takeaway/innovation
        translator = PaperTranslator()
        if translator.enabled:
            logger.log(f"Translating {len(recommendations)} daily papers...", "INFO")
            translator.batch_translate(recommendations, delay=1.0)
        else:
            # Fallback: generate brief keyword-based summaries
            for paper in recommendations:
                paper['abstract_cn'] = ''
                paper['takeaway'] = ''
                paper['innovation'] = ''
            logger.log("Translation skipped (no API key configured)", "WARN")

        if gen_html:
            html_display = HTMLDisplay()
            html_display.save_daily(recommendations, output, date)
            logger.log(f"HTML output saved to {output}", "INFO")
        else:
            cli_display = CLIDisplay()
            cli_display.print_recommendations(recommendations)

        logger.log("Daily pipeline completed successfully", "INFO")

    except Exception as e:
        logger.log(f"Error in daily pipeline: {str(e)}", "ERROR")
        raise


def run_top100_pipeline(logger, output='docs/top100.html'):
    """Search past year's GPU DB papers and generate Top 100 page"""

    logger.log("Running Top 100 yearly pipeline", "INFO")

    try:
        arxiv_fetcher = ArxivFetcher(GPU_DB_CATEGORIES)
        recommender = Recommender()

        # Strategy: fetch recent papers by category, then local keyword filter
        logger.log("Fetching recent papers from arXiv categories...", "INFO")
        all_papers = arxiv_fetcher.fetch_recent_papers(days=365, max_results_per_category=500)
        logger.log(f"Fetched {len(all_papers)} total papers from categories", "INFO")

        # Local keyword filter: only keep papers with GPU+DB relevance
        gpu_db_filter_keywords = [
            'gpu', 'cuda', 'opencl', 'graphic', 'accelerat',
            'database', 'query', 'join', 'sql', 'olap', 'oltp',
            'hash table', 'b-tree', 'index', 'column store', 'in-memory',
            'data process', 'analyt', 'simd', 'vectoriz', 'parallel',
            'sort', 'scan', 'aggregat', 'storage', 'kv-store', 'nosql',
        ]

        filtered_papers = []
        for paper in all_papers:
            text = (paper.get('title', '') + ' ' + paper.get('abstract', '')).lower()
            has_gpu = any(kw in text for kw in ['gpu', 'cuda', 'opencl', 'graphic', 'accelerat'])
            has_db = any(kw in text for kw in [
                'database', 'query', 'join', 'sql', 'olap', 'oltp',
                'hash table', 'b-tree', 'index', 'column', 'in-memory',
                'data process', 'analyt', 'simd', 'vectoriz',
                'sort', 'scan', 'aggregat', 'storage', 'kv', 'nosql',
            ])
            # Keep papers that have at least some GPU or DB relevance
            if has_gpu or has_db:
                filtered_papers.append(paper)

        logger.log(f"After GPU+DB keyword filter: {len(filtered_papers)} papers", "INFO")

        # If we got too few from category fetch, supplement with keyword search
        if len(filtered_papers) < 50:
            logger.log("Supplementing with keyword search...", "INFO")
            keyword_groups = [
                ['GPU database', 'GPU-accelerated database', 'GPU query processing'],
                ['GPU hash join', 'GPU sorting', 'GPU indexing', 'GPU storage'],
                ['CUDA database', 'GPU analytics', 'GPU OLAP', 'GPU columnar'],
            ]
            for keywords in keyword_groups:
                try:
                    kw_papers = arxiv_fetcher.search_papers_by_keywords(
                        keywords=keywords,
                        categories=GPU_DB_CATEGORIES,
                        max_results=100
                    )
                    filtered_papers.extend(kw_papers)
                    logger.log(f"  Keyword search found {len(kw_papers)} papers", "INFO")
                except Exception as e:
                    logger.log(f"  Keyword search error: {e}", "WARN")

            # Re-deduplicate
            seen_ids = set()
            unique_filtered = []
            for p in filtered_papers:
                pid = p.get('id', '')
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    unique_filtered.append(p)
            filtered_papers = unique_filtered

        logger.log(f"Total papers to rank: {len(filtered_papers)}", "INFO")

        # Score and rank all papers
        scored_papers = recommender.recommend(filtered_papers, top_k=100)

        # Translate abstracts and generate AI takeaway/innovation
        translator = PaperTranslator()
        if translator.enabled:
            logger.log(f"Translating {len(scored_papers)} top papers...", "INFO")
            translator.batch_translate(scored_papers, delay=1.0)
        else:
            # Fallback: generate brief keyword-based summaries
            for paper in scored_papers:
                paper['abstract_cn'] = ''
                paper['takeaway'] = ''
                paper['innovation'] = ''
                paper['summary_cn'] = _generate_summary_cn(paper)
            logger.log("Translation skipped (no API key configured), using keyword summaries", "WARN")

        # Generate HTML
        html_display = HTMLDisplay()
        html_display.save_top100(scored_papers, output)
        logger.log(f"Top 100 HTML saved to {output}", "INFO")

        logger.log("Top 100 pipeline completed successfully", "INFO")

    except Exception as e:
        logger.log(f"Error in Top 100 pipeline: {str(e)}", "ERROR")
        raise


def _generate_summary_cn(paper: dict) -> str:
    """Generate a brief Chinese summary from the abstract using keyword extraction"""
    abstract = paper.get('abstract', '')
    title = paper.get('title', '')
    text = (title + ' ' + abstract).lower()

    # Map of English key phrases to Chinese descriptions
    topic_map = {
        'gpu database': 'GPU 数据库',
        'gpu-accelerated': 'GPU 加速',
        'gpu query': 'GPU 查询处理',
        'gpu hash join': 'GPU 哈希连接',
        'gpu sort': 'GPU 排序',
        'gpu index': 'GPU 索引',
        'gpu storage': 'GPU 存储',
        'gpu transaction': 'GPU 事务处理',
        'gpu in-memory': 'GPU 内存数据库',
        'gpu olap': 'GPU OLAP 分析',
        'gpu oltp': 'GPU OLTP 处理',
        'gpu columnar': 'GPU 列式存储',
        'cuda database': 'CUDA 数据库',
        'gpu analytics': 'GPU 分析处理',
        'gpu sql': 'GPU SQL 处理',
        'gpu nosql': 'GPU NoSQL',
        'gpu data warehouse': 'GPU 数据仓库',
        'hash table': '哈希表',
        'b-tree': 'B 树索引',
        'join algorithm': '连接算法',
        'query optimization': '查询优化',
        'query processing': '查询处理',
        'column store': '列式存储',
        'row store': '行式存储',
        'in-memory': '内存数据库',
        'vectorized': '向量化执行',
        'simd': 'SIMD 并行',
        'parallel database': '并行数据库',
        'data processing': '数据处理',
        'gpu memory': 'GPU 内存管理',
        'gpu parallel': 'GPU 并行计算',
        'gpu compute': 'GPU 计算',
        'gpu acceleration': 'GPU 加速',
        'cuda': 'CUDA',
        'coalesced': '合并访存',
        'shared memory': '共享内存',
        'warp': 'warp 调度',
        'thread block': '线程块',
        'analytical query': '分析查询',
        'gpu scan': 'GPU 扫描',
        'gpu aggregation': 'GPU 聚合',
        'gpu scan': 'GPU 扫描',
        'nearest neighbor': '近邻搜索',
        'vector database': '向量数据库',
        'gpu scheduling': 'GPU 调度',
        'gpu kernel': 'GPU 核函数',
        'gpu cache': 'GPU 缓存',
        'data compression': '数据压缩',
    }

    # Find matching topics
    matched = []
    for en_term, cn_term in topic_map.items():
        if en_term in text:
            if cn_term not in matched:
                matched.append(cn_term)

    if not matched:
        return ''

    # Build a concise summary
    title_en = paper.get('title', '')
    summary = f"本文研究{'、'.join(matched[:5])}相关技术。"

    # Add a brief abstract excerpt
    if abstract:
        first_sentence = abstract.split('.')[0]
        if len(first_sentence) > 150:
            first_sentence = first_sentence[:150] + '...'
        summary += f" 核心内容：{first_sentence}。"

    return summary


def run_cli_mode(config_manager, logger, date=None):
    """Run in CLI interactive mode"""
    logger.log("Starting CLI mode", "INFO")

    cli_display = CLIDisplay()
    cli_display.run_interactive_mode()


if __name__ == '__main__':
    main()
