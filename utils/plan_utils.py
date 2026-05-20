import os
import autowsgr
from pathlib import Path


def get_backend_plans_dir():
    """获取后端 autowsgr 内置的方案目录路径 (autowsgr/data/plans)"""
    try:
        path = Path(autowsgr.__file__).parent / 'data' / 'plans'
        return path if path.is_dir() else None
    except Exception:
        return None


def list_directory(path, filter_func=None):
    """列出目录内容，可选择过滤。返回条目名称列表。"""
    if not path or not os.path.isdir(str(path)):
        return []
    try:
        items = os.listdir(str(path))
        if filter_func:
            items = [item for item in items if filter_func(str(path / item))]
        return items
    except Exception:
        return []


def merge_lists(*lists):
    """合并多个列表，按出现顺序去重（先出现的优先级更高）。"""
    seen = set()
    result = []
    for lst in lists:
        for item in lst:
            if item not in seen:
                seen.add(item)
                result.append(item)
    return result
