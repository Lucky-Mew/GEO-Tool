"""统一配置管理"""

import os
import sys
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any

# 项目根目录
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
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


def get_monitor_data_dir(project_id: Optional[int] = None) -> Path:
    """获取监测数据目录（支持项目隔离）"""
    if project_id:
        dir_path = DATA_DIR / "monitor" / f"project_{project_id}"
    else:
        dir_path = DATA_DIR / "monitor"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_db_path() -> Path:
    """获取数据库文件路径"""
    get_data_dir()
    return DB_PATH


def _migrate_old_config(config: dict) -> dict:
    """迁移旧配置到新格式"""
    if "projects" in config:
        return config

    migrated = {
        "doubao": config.get("doubao", {}),
        "llm_api": config.get("llm_api", {}),
        "global": {
            "default_project": 1
        },
        "projects": []
    }

    old_monitor = config.get("monitor", {})
    old_tasks = old_monitor.get("tasks", [])
    old_schedule = old_monitor.get("schedule_hours", [])

    if old_tasks:
        brand = old_tasks[0].get("brands", ["品牌"])[0] if old_tasks else "品牌"
        migrated["projects"].append({
            "id": 1,
            "name": brand,
            "description": "默认项目",
            "config": {
                "tasks": old_tasks,
                "schedule_hours": old_schedule
            }
        })

    return migrated


def load_config() -> dict:
    """加载配置文件"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        config = _migrate_old_config(config)
        return config
    except Exception:
        return {
            "doubao": {},
            "llm_api": {},
            "global": {},
            "projects": []
        }


def save_config(config: dict):
    """保存配置文件"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def get_project_config(project_id: int) -> Optional[dict]:
    """获取指定项目的配置"""
    config = load_config()
    for project in config.get("projects", []):
        if project.get("id") == project_id:
            return project.get("config", {})
    return None


def save_project_config(project_id: int, project_config: dict):
    """保存项目配置"""
    config = load_config()
    for project in config.get("projects", []):
        if project.get("id") == project_id:
            project["config"] = project_config
            break
    save_config(config)


def get_all_projects() -> List[Dict]:
    """获取所有项目列表"""
    config = load_config()
    return config.get("projects", [])


def create_project(name: str, description: Optional[str] = None) -> int:
    """创建新项目，返回 project_id"""
    config = load_config()
    projects = config.get("projects", [])

    new_id = max([p.get("id", 0) for p in projects], default=0) + 1

    new_project = {
        "id": new_id,
        "name": name,
        "description": description or "",
        "config": {
            "tasks": [],
            "schedule_hours": []
        }
    }

    projects.append(new_project)
    config["projects"] = projects

    if not config.get("global", {}).get("default_project"):
        config["global"] = config.get("global", {})
        config["global"]["default_project"] = new_id

    save_config(config)
    return new_id


def update_project(project_id: int, name: Optional[str] = None, description: Optional[str] = None):
    """更新项目信息"""
    config = load_config()
    for project in config.get("projects", []):
        if project.get("id") == project_id:
            if name is not None:
                project["name"] = name
            if description is not None:
                project["description"] = description
            break
    save_config(config)


def delete_project_config(project_id: int):
    """删除项目配置"""
    config = load_config()
    projects = [p for p in config.get("projects", []) if p.get("id") != project_id]
    config["projects"] = projects

    if config.get("global", {}).get("default_project") == project_id and projects:
        config["global"]["default_project"] = projects[0].get("id")

    save_config(config)


def get_default_project_id() -> Optional[int]:
    """获取默认项目ID"""
    config = load_config()
    return config.get("global", {}).get("default_project")


def set_default_project(project_id: int):
    """设置默认项目"""
    config = load_config()
    config["global"] = config.get("global", {})
    config["global"]["default_project"] = project_id
    save_config(config)
