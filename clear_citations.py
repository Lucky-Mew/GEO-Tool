#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清空 doubao_citations 表"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import get_db_path
import sqlite3

conn = sqlite3.connect(get_db_path())
cursor = conn.cursor()

cursor.execute('DELETE FROM doubao_citations')
deleted = cursor.rowcount
conn.commit()
conn.close()

print(f"已删除 {deleted} 条引用记录")
