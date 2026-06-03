"""上下文管理工具 — 滑动窗口 + 摘要压缩"""

from app.llm.client import call_llm

MAX_ROUNDS = 10          # 主题内最大轮数，超过触发压缩
MAX_RECENT = 6           # 压缩后保留最近 N 条原文


def _format(messages: list) -> str:
    return "\n".join([f"{m.get('role','')}: {m.get('content','')}" for m in messages])


def compress_within_topic(messages: list, llm_api_key: str = "") -> str:
    if not messages:
        return "暂无对话历史"

    if len(messages) <= MAX_ROUNDS * 2:
        return _format(messages)

    early = messages[:-(MAX_RECENT)]
    recent = messages[-(MAX_RECENT):]

    prompt = f"""将以下对话历史压缩为一段简短摘要（不超过100字），保留讨论脉络和用户的主要观点：

{_format(early)}

摘要："""

    summary = call_llm(prompt, llm_api_key=llm_api_key).strip()
    return f"【讨论摘要】\n{summary}\n\n【最近对话】\n{_format(recent)}"


def summarize_topic(topic: str, messages: list, llm_api_key: str = "") -> str:
    if not messages:
        return ""

    prompt = f"""将以下关于主题「{topic}」的讨论，用一段话（不超过150字）总结用户的核心观点：

{_format(messages)}

示例：
  用户认为欲望是财富的起点，但对"如何将欲望转化为行动"感到困惑。AI 引导他认识到，
  明确目标和切断退路是欲望落地的关键。用户最终将书中观点与自己的职业规划做了关联。

摘要："""

    return call_llm(prompt, llm_api_key=llm_api_key).strip()
