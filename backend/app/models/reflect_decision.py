"""
[déprecated] Reflect 决策模块

此文件中的路由逻辑已被新的架构替代:
- Per-dimension 充分性判断 → 条件边 route_dimension（nodes.py）
- 笔记整体评估 → reflect 节点（nodes.py）
- 用户结束信号检测 → _check_finish_signals（nodes.py）

保留此文件仅用于:
1. JSON 解析工具函数（parse_decision 在其他地方可能被引用）
2. 向后兼容

待所有引用迁移后可安全删除。
"""
import json
import re
from typing import Optional


def parse_json(raw: str) -> Optional[dict]:
    """从 LLM 原始输出中提取 JSON 对象。通用工具函数。"""
    # 策略1：找第一个完整 JSON 对象
    match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 策略2：处理嵌套大括号
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def parse_json_array(raw: str) -> Optional[list]:
    """从 LLM 原始输出中提取 JSON 数组。"""
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None
