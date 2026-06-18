"""JSON 数据导入数据库"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.config import get_monitor_data_dir
from src.db import models


def extract_brand_mentions(response_text: str, target_brand: str) -> Dict[str, Any]:
    """从回复中提取品牌提及信息"""
    result = {
        "target_mentioned": False,
        "position": None,
        "sentiment": "neutral",
        "brands_found": {}
    }

    if not response_text or len(response_text) < 10:
        return result

    # 简单检测目标品牌是否提及
    if target_brand in response_text:
        result["target_mentioned"] = True

        # 简单检测位置（开头/中间/结尾）
        first_index = response_text.find(target_brand)
        text_length = len(response_text)
        if first_index < text_length * 0.3:
            result["position"] = "first"
        elif first_index > text_length * 0.7:
            result["position"] = "last"
        else:
            result["position"] = "middle"

    # 简单提取其他品牌（根据常见模式）
    common_patterns = [
        r'(?:^|\n)([\w一-龥]{2,8})(?:\s*[—-]|\s*[:：])',
        r'(?:^|\n)(\d+[.、]\s*)([\w一-龥]{2,8})',
    ]

    found = set()
    for pattern in common_patterns:
        matches = re.findall(pattern, response_text)
        for match in matches:
            if isinstance(match, tuple):
                match = match[-1]
            if len(match) >= 2 and match not in ["搜索", "参考", "资料", "优先", "背景", "技术", "效果", "安全", "适合", "注意"]:
                found.add(match)

    result["brands_found"] = {b: 1 for b in list(found)[:10]}
    return result


def import_json_to_db(json_path: Path, brand: str, question: str) -> bool:
    """导入单个 JSON 文件到数据库"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        date_str = json_path.parent.name
        hour = data.get('hour', 0)
        timestamp = data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M'))
        questions = data.get('questions', [])
        responses = []
        for resp in data.get('responses', []):
            if isinstance(resp, dict):
                responses.append(resp.get('answer') or resp.get('content') or json.dumps(resp, ensure_ascii=False))
            else:
                responses.append(resp or "")

        # 插入任务
        task_id = models.insert_monitor_task(date_str, hour, timestamp, brand, question)

        # 插入问题
        question_ids = models.insert_questions(task_id, questions, responses)

        # 简单提取品牌提及
        total_mentions = 0
        for qid, resp in zip(question_ids, responses):
            mentions = extract_brand_mentions(resp, brand)
            if mentions["target_mentioned"]:
                total_mentions += 1
                models.insert_brand_mention(
                    qid,
                    brand_name=brand,
                    mention_position=mentions["position"],
                    sentiment=mentions["sentiment"]
                )

            # 记录其他品牌
            for bname in mentions["brands_found"].keys():
                if bname != brand:
                    models.insert_brand_mention(qid, brand_name=bname)

        # 保存摘要
        summary_data = {
            "date_str": date_str,
            "hour": hour,
            "total_questions": len(questions),
            "mention_count": total_mentions
        }

        return True
    except Exception as e:
        print(f"导入 {json_path} 失败: {e}")
        return False


def import_all_existing_data(brand: str = "完形康躰", question: str = "康躰脂雕哪家好"):
    """导入所有现有的 JSON 数据"""
    monitor_dir = get_monitor_data_dir()

    if not monitor_dir.exists():
        print("监测数据目录不存在")
        return

    imported_count = 0
    for date_dir in sorted(monitor_dir.iterdir()):
        if not date_dir.is_dir() or not date_dir.name.isdigit():
            continue

        for json_file in date_dir.glob("timepoint_*.json"):
            if import_json_to_db(json_file, brand, question):
                imported_count += 1

    print(f"共导入 {imported_count} 个数据文件")


if __name__ == "__main__":
    import_all_existing_data()
