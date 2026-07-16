"""
向量存储与检索模块 - 轻量级实现
使用简单的 TF-IDF + 余弦相似度，不依赖重型向量库
"""

import re
import math
import json
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
import hashlib


class SimpleVectorStore:
    """简单的向量存储与检索"""

    def __init__(self):
        # 停用词（简单版本）
        self.stop_words = set([
            '的', '了', '和', '是', '就', '都', '而', '及', '与', '在',
            '有', '我', '他', '你', '这', '那', '个', '之', '为', '上',
            '下', '中', '大', '小', '多', '少', '很', '最', '也', '不',
            'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
            'in', 'on', 'at', 'to', 'for', 'of', 'with'
        ])

        # 词汇表
        self.vocab = {}
        # IDF值
        self.idf = {}
        # 文档数量
        self.doc_count = 0

    def tokenize(self, text: str) -> List[str]:
        """简单分词（按字符ngram+标点切分）"""
        # 中文按2-gram，英文按空格
        tokens = []

        # 先提取英文单词和数字
        english_parts = re.findall(r'[a-zA-Z0-9]+', text.lower())
        tokens.extend(english_parts)

        # 中文2-gram
        chinese_chars = re.findall(r'[一-鿿]', text)
        for i in range(len(chinese_chars) - 1):
            tokens.append(chinese_chars[i] + chinese_chars[i + 1])

        # 过滤停用词
        tokens = [t for t in tokens if t not in self.stop_words and len(t) >= 2]
        return tokens

    def compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """计算词频 TF"""
        tf_dict = {}
        token_count = len(tokens)
        if token_count == 0:
            return tf_dict

        counter = Counter(tokens)
        for token, count in counter.items():
            tf_dict[token] = count / token_count
        return tf_dict

    def add_documents(self, chunks: List[Dict]):
        """添加文档并建立索引"""
        # 收集所有token
        all_tokens = []
        doc_tokens_list = []

        for chunk in chunks:
            tokens = self.tokenize(chunk['content'])
            doc_tokens_list.append(tokens)
            all_tokens.extend(tokens)

        # 构建词汇表
        self.vocab = {}
        for idx, token in enumerate(sorted(list(set(all_tokens)))):
            self.vocab[token] = idx

        # 计算IDF
        self.doc_count = len(chunks)
        token_doc_count = defaultdict(int)

        for tokens in doc_tokens_list:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                token_doc_count[token] += 1

        self.idf = {}
        for token, count in token_doc_count.items():
            self.idf[token] = math.log(self.doc_count / (count + 1))

    def compute_tfidf(self, tokens: List[str]) -> Dict[str, float]:
        """计算 TF-IDF 向量"""
        tf = self.compute_tf(tokens)
        tfidf = {}
        for token, tf_val in tf.items():
            if token in self.idf:
                tfidf[token] = tf_val * self.idf[token]
        return tfidf

    def compute_cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """计算余弦相似度"""
        common_tokens = set(vec1.keys()) & set(vec2.keys())
        if not common_tokens:
            return 0.0

        dot_product = sum(vec1[t] * vec2[t] for t in common_tokens)

        norm1 = math.sqrt(sum(v * v for v in vec1.values()))
        norm2 = math.sqrt(sum(v * v for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class RetrievalEngine:
    """检索引擎 - 整合摘要优先+全文检索"""

    def __init__(self):
        self.vector_store = SimpleVectorStore()
        self.chunks_index = []  # 索引到原始数据

    def index_chunks(self, chunks: List[Dict]):
        """建立索引"""
        self.chunks_index = chunks
        self.vector_store.add_documents(chunks)

    def search(self, query: str, top_k: int = 5,
               summaries: Optional[List[Dict]] = None) -> List[Dict]:
        """
        检索相关片段

        返回顺序：
        1. 摘要匹配（如果有）
        2. 原文匹配
        """
        results = []

        # 首先搜索摘要（如果提供了）
        if summaries:
            summary_results = self._search_in_summaries(query, summaries, top_k)
            results.extend(summary_results)

        # 然后搜索原文
        text_results = self._search_in_chunks(query, top_k)

        # 合并结果，去重
        seen_ids = set(r.get('id') for r in results)
        for r in text_results:
            if r.get('id') not in seen_ids:
                results.append(r)
                seen_ids.add(r.get('id'))

        # 按分数排序，返回 top_k
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return results[:top_k]

    def _search_in_summaries(self, query: str, summaries: List[Dict], top_k: int) -> List[Dict]:
        """在摘要中搜索"""
        if not summaries:
            return []

        query_tokens = self.vector_store.tokenize(query)
        query_tfidf = self.vector_store.compute_tfidf(query_tokens)

        results = []
        for summary in summaries:
            summary_tokens = self.vector_store.tokenize(summary['content'])
            summary_tfidf = self.vector_store.compute_tfidf(summary_tokens)
            score = self.vector_store.compute_cosine_similarity(query_tfidf, summary_tfidf)

            if score > 0.01:
                results.append({
                    'id': f"summary_{summary['id']}",
                    'type': 'summary',
                    'content': summary['content'],
                    'title': summary.get('title', ''),
                    'level': summary.get('summary_level', ''),
                    'score': score * 1.2,  # 摘要结果加权重
                    'source': f"[摘要] {summary.get('title', '')}"
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def _search_in_chunks(self, query: str, top_k: int) -> List[Dict]:
        """在原文片段中搜索"""
        if not self.chunks_index:
            return []

        query_tokens = self.vector_store.tokenize(query)
        query_tfidf = self.vector_store.compute_tfidf(query_tokens)

        results = []
        for chunk in self.chunks_index:
            chunk_tokens = self.vector_store.tokenize(chunk['content'])
            chunk_tfidf = self.vector_store.compute_tfidf(chunk_tokens)
            score = self.vector_store.compute_cosine_similarity(query_tfidf, chunk_tfidf)

            if score > 0.01:
                results.append({
                    'id': f"chunk_{chunk['id']}",
                    'type': 'chunk',
                    'content': chunk['content'],
                    'document_id': chunk.get('document_id'),
                    'chunk_index': chunk.get('chunk_index'),
                    'filename': chunk.get('original_filename', ''),
                    'category': chunk.get('category', ''),
                    'score': score,
                    'source': f"[{chunk.get('original_filename', '')} 第{chunk.get('chunk_index', 0) + 1}段]"
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def simple_keyword_match(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """简单关键词匹配（备用方案）"""
        query_keywords = set(self.vector_store.tokenize(query))
        results = []

        for chunk in chunks:
            chunk_text = chunk['content'].lower()
            match_count = 0
            for kw in query_keywords:
                if kw.lower() in chunk_text:
                    match_count += 1

            if match_count > 0:
                results.append({
                    'id': f"chunk_{chunk['id']}",
                    'type': 'chunk',
                    'content': chunk['content'],
                    'document_id': chunk.get('document_id'),
                    'filename': chunk.get('original_filename', ''),
                    'category': chunk.get('category', ''),
                    'score': match_count / max(len(query_keywords), 1),
                    'source': f"[{chunk.get('original_filename', '')}]"
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:5]


def build_context_for_generation(retrieval_results: List[Dict], max_length: int = 2000) -> str:
    """
    将检索结果构建成适合大模型的上下文
    """
    if not retrieval_results:
        return ""

    parts = []
    current_length = 0

    for result in retrieval_results:
        source = result.get('source', '来源未知')
        content = result.get('content', '')

        # 截取内容
        if len(content) > 500:
            content = content[:500] + '...'

        part = f"--- {source} ---\n{content}\n"

        if current_length + len(part) > max_length:
            break

        parts.append(part)
        current_length += len(part)

    return "\n".join(parts)
