#!/usr/bin/env python3
"""
工具函数模块
"""

import json
from pathlib import Path
from typing import Any, Dict


def save_json(data: Any, filepath: str):
    """保存JSON文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(filepath: str) -> Any:
    """加载JSON文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def format_percent(value: float, decimals: int = 2) -> str:
    """格式化百分比"""
    return f"{value:.{decimals}f}%"


def format_money(value: float) -> str:
    """格式化金额"""
    return f"¥{value:,.2f}"


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).resolve().parent.parent
