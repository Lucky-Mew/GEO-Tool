# GEO优化工作台模块
"""
GEO (Generative Engine Optimization) 品牌优化工作台
- 关键词管理
- 独有信息素材库
- 文档智能管理
- 向量检索
- 内容生产助手
- 命中率监测
- 竞品分析
- 执行计划管理
"""

from .keyword_manager import KeywordManager
from .material_manager import MaterialManager
from .content_helper import ContentTemplate
from .hit_tracker import HitTracker
from .competitor_analyzer import CompetitorAnalyzer, CitationContentAnalyzer
from .plan_manager import PlanManager
from .document_processor import DocumentProcessor
from .vector_store import RetrievalEngine, build_context_for_generation
from .geo_quality_scorer import GEOQualityScorer, score_geo_content

__all__ = [
    'KeywordManager',
    'MaterialManager',
    'ContentTemplate',
    'HitTracker',
    'CompetitorAnalyzer',
    'CitationContentAnalyzer',
    'PlanManager',
    'DocumentProcessor',
    'RetrievalEngine',
    'build_context_for_generation',
    'GEOQualityScorer',
    'score_geo_content',
]
