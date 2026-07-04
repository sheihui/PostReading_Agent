from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict, total=False):
    # 用户信息
    user_id: str
    book_id: str
    book_title: str
    api_key: str
    llm_api_key: str

    # 收集到的信息（Collect Info）
    book_intro: str                         # 书籍简介
    my_review: List[Dict[str, str]]         # 我的想法
    perspective: List[Dict[str, str]]       # 书中核心观点
    review: List[Dict[str, str]]            # 其他读者的观点

    # 采集清单（Plan）
    collection_plan: List[Dict[str, Any]]   # [{id, category, label, goal, priority, cross_book_hook, suggested_angles}]
    current_dimension_idx: int              # 当前维度索引
    current_dimension_turns: int            # 当前维度已进行轮次
    max_turns_per_dimension: int            # 单维度轮次上限（默认 15）

    # 兼容旧字段（Plan）
    theme: List[Dict]                       # deprecated → 映射到 collection_plan
    current_theme_idx: int                  # deprecated → 映射到 current_dimension_idx

    # 采集结果（Execute + 维度路由）
    messages: List[Dict]                    # 当前维度的对话（切换时清空）
    collected_insights: Dict[str, List[Dict]]  # {dimension_id: [{content, stance, has_example, has_evidence}]}
    dimension_sufficiency: Dict[str, bool]  # {dimension_id: true/false} — 规则判断，非 LLM
    dimension_tracking: Dict[str, Dict]     # {dimension_id: {turns, angles_used, user_stance, ...}}

    # 兼容旧字段（Execute）
    insight: List[str]                      # deprecated → 不再写入新数据
    topic_summaries: Dict[str, str]         # {dimension_label: summary} — 维度归档摘要

    # 长期记忆
    cross_book_hooks: List[Dict]            # Plan 阶段检索到的跨书关联

    # 笔记
    is_complete: bool                       # 是否完成
    final_note: str                         # 最终笔记

    # 评测
    run_log: Dict[str, Any]                 # 自动评测记录

    # === 以下字段在重构后移除 ===
    next: str                               # 下一个节点（旧路由，保留到图改造完成）
    decision_history: List[str]             # deprecated
    topic_insights: Dict[str, List[str]]    # deprecated
    current_topic_turns: int                # deprecated → 迁移到 dimension_tracking
