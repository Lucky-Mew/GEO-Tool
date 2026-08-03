#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单测试"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing import...")
try:
    from src.geo import DocumentProcessor
    print("OK: DocumentProcessor imported")

    dp = DocumentProcessor()
    docs = dp.get_documents(4)
    print(f"OK: Got {len(docs)} documents")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
