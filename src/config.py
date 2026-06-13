"""统一配置管理"""

import os
import sys
import yaml
from pathlib import Path

# 项目根目录
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
MONITOR_DATA_DIR = DATA_DIR / "monitor"
DB_PATH = DATA_DIR / "geo_monitor.db"

# 配置文件路径
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def get_project_root() -> Path:
    """获取项目根目录"""
    return PROJECT_ROOT


def get_data_dir() -> Path:
    """获取数据目录"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def get_monitor_data_dir() -> Path:
    """获取监测数据目录"""
    MONITOR_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return MONITOR_DATA_DIR


def get_db_path() -> Path:
    """获取数据库文件路径"""
    get_data_dir()
    return DB_PATH


def load_config() -> dict:
    """加载配置文件"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def save_config(config: dict):
    """保存配置文件"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
