"""
Recommender for Paper Daily

Generates paper recommendations based on semantic similarity to a focus topic.
"""

import numpy as np
from typing import List, Dict, Optional

from embedding.embedder import Embedder


class Recommender:
    """Generates paper recommendations based on semantic relevance"""
    
    FOCUS_TOPIC = "GPU-accelerated database systems, GPU database query processing, GPU-accelerated data processing, GPU memory management for databases, GPU hash join, GPU sorting, GPU indexing, GPU columnar storage, GPU transaction processing, CUDA database operations"
    
    def __init__(self, top_k: int = 10):
        self.top_k = top_k
        self.embedder = Embedder()
        self.focus_embedding: Optional[np.ndarray] = None
        self._init_focus_embedding()
    
    def _init_focus_embedding(self):
        """Pre-compute the embedding for the focus topic"""
        if self.embedder.model is not None:
            self.focus_embedding = self.embedder.generate_embedding(self.FOCUS_TOPIC)
    
    def recommend(self, papers: List[Dict], top_k: int = None) -> List[Dict]:
        """Generate paper recommendations based on semantic relevance to focus topic"""
        if not papers:
            return []
        
        k = top_k or self.top_k
        
        scored_papers = []
        
        if self.embedder.model is not None and self.focus_embedding is not None:
            for paper in papers:
                paper_embedding = self.embedder.generate_paper_embedding(paper)
                score = self.embedder.compute_similarity(paper_embedding, self.focus_embedding)
                
                boost = self._compute_keyword_boost(paper)
                final_score = min(1.0, score + boost)
                
                paper_copy = paper.copy()
                paper_copy['score'] = final_score
                paper_copy['reasons'] = self._generate_reasons(paper, final_score)
                scored_papers.append(paper_copy)
        else:
            for paper in papers:
                score = self._compute_keyword_boost(paper) / 0.1
                score = min(1.0, score)
                paper_copy = paper.copy()
                paper_copy['score'] = score
                paper_copy['reasons'] = self._generate_reasons(paper, score)
                scored_papers.append(paper_copy)
        
        scored_papers.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_papers[:k]

    # Keep backward compatibility
    def recommend_top_10(self, papers: List[Dict]) -> List[Dict]:
        return self.recommend(papers, top_k=10)
    
    def _compute_keyword_boost(self, paper: Dict) -> float:
        """Compute a score boost based on presence of key GPU+DB terms"""
        text = (paper.get('title', '') + ' ' + paper.get('abstract', '')).lower()
        
        primary_terms = [
            'gpu database', 'gpu-accelerated', 'gpu query', 'gpu processing',
            'gpu hash', 'gpu join', 'gpu sort', 'gpu index', 'gpu storage',
            'cuda database', 'gpu columnar', 'gpu olap', 'gpu oltp',
            'gpu transaction', 'gpu data processing', 'gpu analytics',
            'gpu relational', 'gpu sql', 'gpu nosql', 'gpu kv',
            'gpu in-memory', 'gpu memory database', 'gpu data warehouse',
        ]
        
        secondary_terms = [
            'gpu', 'cuda', 'opencl', 'kernel', 'wavefront',
            'gpu memory', 'gpu parallel', 'gpu compute', 'gpu acceleration',
            'coalesced', 'shared memory', 'warp', 'thread block',
            'database', 'query processing', 'join algorithm', 'hash table',
            'b-tree', 'column store', 'row store', 'olap', 'oltp',
            'data processing', 'in-memory database', 'vectorized',
            'simd', 'parallel database', 'analytical query',
        ]
        
        boost = 0.0
        for term in primary_terms:
            if term in text:
                boost += 0.08
        
        for term in secondary_terms:
            if term in text:
                boost += 0.015
        
        return boost
    
    def _generate_reasons(self, paper: Dict, score: float) -> List[str]:
        """Generate a brief reason for why the paper was recommended (Chinese)"""
        text = (paper.get('title', '') + ' ' + paper.get('abstract', '')).lower()
        reasons = []
        
        if 'gpu' in text and any(db_term in text for db_term in ['database', 'query', 'join', 'sql', 'olap', 'oltp', 'storage', 'index', 'hash']):
            reasons.append('直接涉及 GPU 加速数据库操作')
        elif 'gpu' in text or 'cuda' in text:
            reasons.append('涉及 GPU 计算技术')
        elif any(db_term in text for db_term in ['database', 'query', 'join', 'sql']):
            reasons.append('与数据库系统和查询处理相关')
        
        if score > 0.8:
            reasons.append('与 GPU 数据库主题高度相关')
        elif score > 0.6:
            reasons.append('与 GPU 数据库主题中等相关')
        
        if not reasons:
            reasons.append('与硬件架构或数据系统相关')
        
        return reasons
