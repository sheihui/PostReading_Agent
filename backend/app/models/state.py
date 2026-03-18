from typing import TypedDict, List, Dict

class AgentState(TypedDict):
    # 用户信息
    user_id: str
    book_id: str
    book_title: str
    
    # 收集到的信息
    book_intro: str                         # 书籍简介
    my_review: List[Dict[str, str]]         # 我的想法

    perspective: List[Dict[str, str]]       # 书中核心观点
    review: List[Dict[str, str]]            # 其他读者的观点

    # Plan
    theme: list[Dict]                       # 主题
    current_theme_idx: int                  # 当前主题索引

    # Execute
    messages: list[Dict]                    # 对话历史
    insight: list[str]                      # 本轮洞察

    # Reflect
    is_complete: bool                       # 是否完成
    final_note: str                         # 最终笔记
    next: str                               # 下一个节点

    is_complete: bool                       # 是否完成

