# 竞品分析模块
"""
竞品GEO分析:
- 分析AI引用了竞品的哪些内容
- 分析竞品内容结构(表格/列表/纯文字)
- 识别我们的空白切入机会
- 抓取豆包引用的来源内容并深度分析
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from src.db.models import get_connection
import time
import random


class CompetitorAnalyzer:
    """竞品GEO分析"""

    def add_competitor(self, project_id: Optional[int], name: str,
                       url: Optional[str] = None, notes: Optional[str] = None) -> int:
        """添加竞品"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO geo_competitors (project_id, name, url, notes)
                VALUES (?, ?, ?, ?)
            ''', (project_id, name, url, notes))
            competitor_id = cursor.lastrowid
            conn.commit()
            return competitor_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_competitors(self, project_id: Optional[int]) -> List[Dict]:
        """获取竞品列表"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM geo_competitors
                WHERE project_id IS ?
                ORDER BY created_at DESC
            ''', (project_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def add_citation(self, project_id: Optional[int], competitor_id: int,
                     keyword: str, cited_content: str,
                     content_structure: Optional[str] = None,
                     source_url: Optional[str] = None) -> int:
        """记录竞品被引用情况"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            date_str = datetime.now().strftime('%Y%m%d')
            cursor.execute('''
                INSERT INTO geo_competitor_citations
                (project_id, competitor_id, keyword, cited_content, content_structure, source_url, date_str)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, competitor_id, keyword, cited_content,
                  content_structure, source_url, date_str))
            citation_id = cursor.lastrowid
            conn.commit()
            return citation_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_competitor_citations(self, project_id: Optional[int],
                                  competitor_id: Optional[int] = None,
                                  days: int = 30) -> List[Dict]:
        """获取竞品引用记录"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            query = '''
                SELECT c.*, comp.name as competitor_name
                FROM geo_competitor_citations c
                LEFT JOIN geo_competitors comp ON c.competitor_id = comp.id
                WHERE c.project_id IS ? AND c.date_str >= ?
            '''
            params = [project_id, cutoff]

            if competitor_id:
                query += ' AND c.competitor_id = ?'
                params.append(competitor_id)

            query += ' ORDER BY c.date_str DESC'

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def analyze_competitor_content_patterns(self, project_id: Optional[int],
                                             competitor_id: int) -> Dict[str, Any]:
        """分析竞品内容模式"""
        citations = self.get_competitor_citations(project_id, competitor_id)

        if not citations:
            return {'patterns': [], 'suggestions': []}

        # 统计内容结构
        structure_counts = {}
        content_keywords = {}

        for cite in citations:
            structure = cite.get('content_structure', 'unknown')
            structure_counts[structure] = structure_counts.get(structure, 0) + 1

            # 简单关键词提取
            content = cite.get('cited_content', '')
            if len(content) > 10:
                # 这里可以加更复杂的NLP分析
                pass

        # 生成建议
        suggestions = self._generate_optimization_suggestions(structure_counts)

        return {
            'total_citations': len(citations),
            'structure_distribution': structure_counts,
            'suggestions': suggestions
        }

    def _generate_optimization_suggestions(self, structure_counts: Dict[str, int]) -> List[str]:
        """基于竞品分析生成优化建议"""
        suggestions = []

        if 'table' in structure_counts:
            suggestions.append("竞品使用了表格,我们也应该增加表格内容")
        if 'list' in structure_counts:
            suggestions.append("竞品使用了列表,我们也应该使用编号列表")
        if 'data' in structure_counts:
            suggestions.append("竞品使用了具体数据,我们需要增加更多数据支持")

        if not suggestions:
            suggestions.append("建议分析竞品被引用的具体内容,寻找空白切入点")

        return suggestions

    def get_gap_analysis(self, project_id: Optional[int]) -> Dict[str, Any]:
        """获取空白分析(我们没有覆盖但竞品有的内容)"""
        # 获取竞品被引用的关键词
        citations = self.get_competitor_citations(project_id)
        competitor_keywords = set(c['keyword'] for c in citations if c.get('keyword'))

        # 获取我们自己的关键词库
        from .keyword_manager import KeywordManager
        km = KeywordManager()
        our_keywords = set(
            k['keyword'] for k in km.get_keywords(project_id)
        )

        # 找出空白
        gaps = competitor_keywords - our_keywords

        return {
            'competitor_keywords': list(competitor_keywords),
            'our_keywords': list(our_keywords),
            'gap_keywords': list(gaps),
            'suggestions': [
                f"建议覆盖空白关键词: {', '.join(list(gaps)[:5])}"
                if gaps else "暂无明显空白,继续保持"
            ]
        }

    def delete_competitor(self, competitor_id: int):
        """删除竞品"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # 级联删除引用记录
            cursor.execute('DELETE FROM geo_competitor_citations WHERE competitor_id = ?', (competitor_id,))
            cursor.execute('DELETE FROM geo_competitors WHERE id = ?', (competitor_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()


# =============================================================================
# 新增：内容抓取和深度分析功能
# =============================================================================

class CitationContentAnalyzer:
    """引用内容深度分析器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    @staticmethod
    def extract_urls_from_citations(citations: List[Dict]) -> List[str]:
        """从citations列表中提取URL"""
        urls = []
        for cite in citations:
            url = cite.get('url', '')
            if url and url.startswith('http'):
                urls.append(url)
        return urls

    @staticmethod
    def fetch_page_content(url: str, page) -> Optional[str]:
        """
        抓取单个页面的内容（需要传入playwright的Page对象）

        注意：这个方法需要在已经有浏览器上下文的环境中调用
        """
        try:
            print(f"    [*] 正在抓取: {url[:60]}...")

            # 导航到页面
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(random.uniform(2, 4))

            # 提取主要内容
            content = page.evaluate("""
                () => {
                    // 尝试多种方式提取主要内容
                    let mainContent = '';

                    // 1. 尝试常见的内容选择器
                    const selectors = [
                        'article',
                        '.article-content',
                        '.content',
                        '.main-content',
                        '#content',
                        'main',
                        '.post-content',
                        '.entry-content'
                    ];

                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const text = el.innerText.trim();
                            if (text.length > 200) {
                                mainContent = text;
                                break;
                            }
                        }
                    }

                    // 2. 如果没找到，尝试找最长的div
                    if (!mainContent) {
                        const allDivs = Array.from(document.querySelectorAll('div'));
                        let longestText = '';
                        let longestEl = null;

                        for (const div of allDivs) {
                            const text = div.innerText.trim();
                            // 排除导航、侧边栏等
                            const className = (div.className || '').toLowerCase();
                            const idName = (div.id || '').toLowerCase();
                            if (className.includes('nav') || className.includes('sidebar') ||
                                className.includes('footer') || className.includes('header') ||
                                idName.includes('nav') || idName.includes('sidebar') ||
                                idName.includes('footer') || idName.includes('header')) {
                                continue;
                            }
                            if (text.length > longestText.length && text.length < 50000) {
                                longestText = text;
                                longestEl = div;
                            }
                        }
                        mainContent = longestText;
                    }

                    // 3. 最后保底：body的text
                    if (!mainContent || mainContent.length < 100) {
                        mainContent = document.body.innerText.trim();
                    }

                    return mainContent;
                }
            """)

            if content and len(content) > 100:
                # 截取前5000字（避免太长）
                return content[:5000]
            return None

        except Exception as e:
            print(f"    [!] 抓取失败: {str(e)[:80]}")
            return None

    @staticmethod
    def analyze_citation_patterns(contents: List[str],
                                   llm_func: Optional[Callable] = None,
                                   config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        分析多个被引用内容的共同点

        返回：
        {
            "common_structures": [...],
            "data_sources": [...],
            "brands_mentioned": [...],
            "tone_style": "...",
            "key_phrases": [...],
            "risk_disclosure": "...",
            "success_factors": [...],
            "recommendations": [...],
            "summary": "..."
        }
        """
        if not contents:
            return {
                "common_structures": ["暂无内容可分析"],
                "data_sources": [],
                "brands_mentioned": [],
                "tone_style": "需要内容分析",
                "key_phrases": [],
                "risk_disclosure": "需要内容分析",
                "success_factors": [],
                "recommendations": ["建议先抓取豆包引用的内容"],
                "summary": "暂无内容可分析"
            }

        if not llm_func or not config:
            # 没有LLM时，做简单分析
            return CitationContentAnalyzer._simple_pattern_analyze(contents)

        # 用LLM做深度分析
        combined_content = "\n\n" + "=" * 60 + "\n\n".join(
            f"【内容 {i+1}】\n{content[:2000]}..."
            for i, content in enumerate(contents[:3])  # 最多分析3篇，避免token太多
        )

        system_prompt = """你是一个专业的GEO分析专家，擅长分析豆包引用的内容，找出它们的共同点。

请分析以下这些被豆包引用的内容，找出它们为什么被采信的原因。

【分析维度】
1. 内容结构：它们用了什么样的结构？（标题层级、表格、列表等）
2. 数据来源：它们引用了哪些权威来源？
3. 品牌处理：它们如何处理品牌？是否中立？
4. 语气风格：它们的语气是怎样的？
5. 风险披露：它们是否披露了风险？
6. 成功要素：它们为什么被豆包采信？

【输出格式】
请用JSON格式输出，不要有其他内容：
{
    "common_structures": ["结构1", "结构2", ...],
    "data_sources": ["来源1", "来源2", ...],
    "brands_mentioned": ["品牌1", "品牌2", ...],
    "tone_style": "描述语气风格",
    "key_phrases": ["关键短语1", "关键短语2", ...],
    "risk_disclosure": "是否披露风险，如何披露",
    "success_factors": ["成功要素1", "成功要素2", ...],
    "recommendations": ["建议1", "建议2", ...],
    "summary": "总结分析结果"
}"""

        user_prompt = f"""请分析以下这些被豆包引用的内容：

{combined_content}

请按照上面的要求输出JSON格式的分析结果。"""

        try:
            result = llm_func(config, f"{system_prompt}\n\n{user_prompt}")
            # 尝试解析JSON
            import json
            # 清理结果（有时候LLM会在前后加其他内容）
            json_start = result.find('{')
            json_end = result.rfind('}')
            if json_start >= 0 and json_end > json_start:
                json_str = result[json_start:json_end+1]
                return json.loads(json_str)
            else:
                # 解析失败，返回简单分析
                return CitationContentAnalyzer._simple_pattern_analyze(contents)
        except Exception as e:
            print(f"    [!] LLM分析失败: {e}")
            return CitationContentAnalyzer._simple_pattern_analyze(contents)

    @staticmethod
    def _simple_pattern_analyze(contents: List[str]) -> Dict[str, Any]:
        """简单的关键词分析（没有LLM时的备选）"""
        all_text = "\n".join(contents)

        # 找常见的结构特征
        has_table = any('|' in c and '---' in c for c in contents)
        has_h1 = any('# ' in c for c in contents)
        has_h2 = any('## ' in c for c in contents)
        has_list = any(line.strip().startswith(('1.', '2.', '3.', '-', '*'))
                       for c in contents for line in c.split('\n'))

        common_structures = []
        if has_table:
            common_structures.append("使用表格展示数据")
        if has_h1 and has_h2:
            common_structures.append("清晰的标题层级（#和##）")
        if has_list:
            common_structures.append("使用列表组织内容")
        if not common_structures:
            common_structures.append("需要更详细分析")

        # 找数据来源关键词
        source_keywords = ["FDA", "NMPA", "卫健委", "WHO", "中科院", "《", "》", "据", "根据"]
        data_sources = [kw for kw in source_keywords if kw in all_text]

        # 找风险披露关键词
        risk_keywords = ["风险", "注意事项", "禁忌", "因人而异", "个体差异"]
        has_risk = any(kw in all_text for kw in risk_keywords)

        return {
            "common_structures": common_structures,
            "data_sources": data_sources or ["未发现明显数据来源"],
            "brands_mentioned": ["需要LLM深度分析"],
            "tone_style": "需要LLM深度分析",
            "key_phrases": ["需要LLM深度分析"],
            "risk_disclosure": "有风险披露" if has_risk else "未发现明显风险披露",
            "success_factors": ["建议使用LLM做深度分析"],
            "recommendations": ["建议使用LLM做深度分析"],
            "summary": f"已分析{len(contents)}篇内容，发现{len(common_structures)}个结构特征"
        }

    @staticmethod
    def generate_analysis_report(analysis_result: Dict[str, Any],
                                  citations: List[Dict]) -> str:
        """生成竞品分析报告（纯文本格式）"""
        lines = []
        lines.append("=" * 60)
        lines.append("豆包引用内容分析报告")
        lines.append("=" * 60)
        lines.append("")

        # 引用来源
        lines.append(f"【引用来源】共 {len(citations)} 个")
        for i, cite in enumerate(citations[:5]):  # 最多显示5个
            title = cite.get('title', '')[:50]
            url = cite.get('url', '')[:60]
            lines.append(f"  {i+1}. {title}...")
            lines.append(f"     {url}...")
        if len(citations) > 5:
            lines.append(f"  ... 还有 {len(citations)-5} 个")
        lines.append("")

        # 分析结果
        lines.append(f"【共同结构】")
        for s in analysis_result.get('common_structures', []):
            lines.append(f"  - {s}")
        lines.append("")

        lines.append(f"【数据来源】")
        sources = analysis_result.get('data_sources', [])
        if sources:
            for s in sources:
                lines.append(f"  - {s}")
        else:
            lines.append(f"  未发现明显数据来源")
        lines.append("")

        lines.append(f"【语气风格】")
        lines.append(f"  {analysis_result.get('tone_style', '需要分析')}")
        lines.append("")

        lines.append(f"【风险披露】")
        lines.append(f"  {analysis_result.get('risk_disclosure', '需要分析')}")
        lines.append("")

        lines.append(f"【成功要素】")
        factors = analysis_result.get('success_factors', [])
        if factors:
            for s in factors:
                lines.append(f"  - {s}")
        lines.append("")

        lines.append(f"【建议】")
        recs = analysis_result.get('recommendations', [])
        if recs:
            for s in recs:
                lines.append(f"  - {s}")
        lines.append("")

        lines.append(f"【总结】")
        lines.append(f"  {analysis_result.get('summary', '')}")
        lines.append("")
        lines.append("=" * 60)

        return '\n'.join(lines)

    @staticmethod
    def generate_html_report(analysis_result: Dict[str, Any],
                              citations: List[Dict]) -> str:
        """生成HTML格式的分析报告（用于前端展示）"""
        html = []
        html.append("<div class='citation-analysis-report'>")

        # 引用来源
        html.append(f"  <div class='section'>")
        html.append(f"    <h3>📚 引用来源（共{len(citations)}个）</h3>")
        html.append(f"    <ul class='citation-list'>")
        for i, cite in enumerate(citations[:5]):
            title = cite.get('title', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            url = cite.get('url', '').replace('&', '&amp;')
            html.append(f"      <li>")
            html.append(f"        <div class='citation-title'>{title[:60]}{'...' if len(title) > 60 else ''}</div>")
            if url:
                html.append(f"        <div class='citation-url'><a href='{url}' target='_blank'>{url[:60]}...</a></div>")
            html.append(f"      </li>")
        if len(citations) > 5:
            html.append(f"      <li class='more'>... 还有 {len(citations)-5} 个来源</li>")
        html.append(f"    </ul>")
        html.append(f"  </div>")

        # 共同结构
        html.append(f"  <div class='section'>")
        html.append(f"    <h3>📐 共同结构特征</h3>")
        html.append(f"    <ul>")
        for s in analysis_result.get('common_structures', []):
            html.append(f"      <li>{s}</li>")
        html.append(f"    </ul>")
        html.append(f"  </div>")

        # 数据来源
        html.append(f"  <div class='section'>")
        html.append(f"    <h3>📊 数据来源</h3>")
        sources = analysis_result.get('data_sources', [])
        if sources:
            html.append(f"    <ul>")
            for s in sources:
                html.append(f"      <li>{s}</li>")
            html.append(f"    </ul>")
        else:
            html.append(f"    <p class='empty'>未发现明显数据来源</p>")
        html.append(f"  </div>")

        # 语气风格
        html.append(f"  <div class='section'>")
        html.append(f"    <h3>💬 语气风格</h3>")
        html.append(f"    <p>{analysis_result.get('tone_style', '')}</p>")
        html.append(f"  </div>")

        # 风险披露
        html.append(f"  <div class='section'>")
        html.append(f"    <h3>⚠️ 风险披露</h3>")
        html.append(f"    <p>{analysis_result.get('risk_disclosure', '')}</p>")
        html.append(f"  </div>")

        # 成功要素
        html.append(f"  <div class='section'>")
        html.append(f"    <h3>✅ 成功要素</h3>")
        factors = analysis_result.get('success_factors', [])
        if factors:
            html.append(f"    <ul>")
            for s in factors:
                html.append(f"      <li>{s}</li>")
            html.append(f"    </ul>")
        html.append(f"  </div>")

        # 建议
        html.append(f"  <div class='section recommendations'>")
        html.append(f"    <h3>💡 优化建议</h3>")
        recs = analysis_result.get('recommendations', [])
        if recs:
            html.append(f"    <ul>")
            for s in recs:
                html.append(f"      <li>{s}</li>")
            html.append(f"    </ul>")
        html.append(f"  </div>")

        # 总结
        html.append(f"  <div class='section summary'>")
        html.append(f"    <h3>📝 总结</h3>")
        html.append(f"    <p>{analysis_result.get('summary', '')}</p>")
        html.append(f"  </div>")

        html.append("</div>")
        return '\n'.join(html)

