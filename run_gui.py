"""启动 GUI 应用"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.collector.gui import main

if __name__ == "__main__":
    main()
