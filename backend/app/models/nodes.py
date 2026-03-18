"""
Agent节点实现
"""
from typing import Dict, List
from app.models.state import AgentState
from app.llm.client import call_llm
from app.tools.rag import rag_add_book_documents, rag_retrieve
from app.tools.search import search_books_perspective, search_books_review
from app.utils.get_book_to_json import get_book_info, save_json_file
from app.config import notes_file_path


# ============ 节点实现 ============

def wait_for_user(state: AgentState) -> AgentState:
    """空节点：等待用户输入"""
    return {}
    

def collect_info(state: AgentState) -> AgentState:
    """
    节点1: 收集书籍信息
    - 获取划线 → RAG
    - 获取笔记 → RAG
    - 搜索书籍核心观点 → state
    - 搜索读者观点 → state
    """
    book_title = state["book_title"]
    # book_id = state["book_id"]
    
    # ===== 步骤 1-2: 获取划线+笔记，存入 RAG =====
    # 获取书籍信息
    book_info, is_exist = get_book_info(book_title)
    if is_exist:
        print(f"节点1[collect_info]书籍信息已存在: data/books/{book_title}.json")
    else:
        # 保存书籍信息到 JSON 文件
        save_json_file(book_info, book_title)
        # 添加书籍文档到 RAG 系统
        rag_add_book_documents.invoke({"title": book_title})
    
    # 提取书籍简介
    book_intro = book_info["book_info"].get("intro", "").strip()

    print(f"节点1[collect_info]获取划线+笔记，存入 RAG成功，书籍标题：{book_title}")
    print("="*50)
    print(f"书籍简介：{book_intro}")
    print("="*50)
    
    # ===== 步骤 3: 搜索书籍核心观点 → state =====
    # perspective_raw = search_books_perspective.invoke({"book_title": book_title})
    perspective_raw = ""
    # 用 LLM 提取关键观点
    perspective_prompt = f"""从以下内容中提取《{book_title}》的3-5个核心观点，简短描述每条观点。

内容：
{perspective_raw}

输出格式（每行一个观点）：
- 观点1
- 观点2
- ..."""
    perspective_text = call_llm(perspective_prompt)
    # 转换为列表存 state
    perspective = [{"content": line.strip()} for line in perspective_text.strip().split("\n") if line.strip()]
    
    # ===== 步骤 4: 搜索读者观点 → state =====
    review_raw = search_books_review.invoke({"book_title": book_title})
    # 用 LLM 提取精选评论
    review_prompt = f"""从以下内容中提取3-5条有价值的读者评论或读后感。

内容：
{review_raw}

输出格式（每行一条评论）：
- 评论1
- 评论2
- ..."""
    review_text = call_llm(review_prompt)
    # 转换为列表存 state
    review = [{"content": line.strip()} for line in review_text.strip().split("\n") if line.strip()]
    
    # 更新 state
    return {
        "book_intro": book_intro,
        "perspective": perspective,
        "review": review
    }


def plan_themes(state: AgentState) -> AgentState:
    """
    节点2: 规划讨论主题
    - RAG 检索用户划线（个性化关键）
    - 分析书籍核心问题 + 用户划线重点 + 读者观点
    - 输出：主题列表 + 每个主题的问题
    """
    book_title = state["book_title"]
    book_intro = state.get("book_intro", "")
    perspective = state.get("perspective", [])
    review = state.get("review", [])
    themes = state.get("theme", [])
    print(f"节点2[plan_themes]开始")
    
    # ===== 检索用户划线（个性化核心）=====
    # 基于书籍标题检索用户的划线内容
    highlights_retrieved = rag_retrieve.invoke({
        "query": f"{book_title} 划线",
        "k": 20
    })
    
    # 构建 prompt
    perspective_str = "\n".join([p.get("content", "") for p in perspective])
    review_str = "\n".join([r.get("content", "") for r in review])

    previous_topics = ", ".join([t.get("topic", "") for t in themes])
    recent_msgs = state.get("messages", [])[-6:] if len(state.get("messages", [])) > 6 else state.get("messages", [])
    recent_history = "\n".join([f"{m.get('role','')}: {m.get('content','')}" for m in recent_msgs])

    
    prompt = f"""你是一本读书会的引导者。用户正在讨论一本已读过书。

请根据以下信息，以及当前的讨论历史，规划1-2个新的讨论主题：

【书籍】
{book_title}

【之前的讨论主题】（参考，不要重复）
{previous_topics}

【当前对话历史】（决定接下来聊什么）
{recent_history}

【用户的划线内容】
{highlights_retrieved}

请为每个主题设计开放式问题。问题要基于当前对话自然过渡。

输出格式（JSON数组）：
[
  {{"topic": "主题名称", "question": "引导问题", "reason": "为什么选这个主题"}},
  ...
]

注意：reason 会用于判断是否要切换主题，请用一句话说明这个主题的价值和讨论意义。"""


    result = call_llm(prompt)
    print()
    print("\n"+"="*50)
    print(f"节点2[plan_themes]原始输出：{result}")
    print("="*50 + "\n")
    
    # 解析 JSON
    import json
    try:
        # 尝试提取 JSON 部分
        import re
        match = re.search(r'\[.*\]', result, re.DOTALL)
        if match:
            themes = json.loads(match.group())
        else:
            themes = []
    except:
        themes = []
    
    print(f"节点2[plan_themes]规划讨论主题成功，书籍标题：{book_title}")
    print("="*50)
    print(f"讨论主题：{themes}")
    print("="*50)
    
    return {
        "theme": themes,
        "current_theme_idx": 0
    }


def execute_theme(state: AgentState) -> AgentState:
    """节点3: 执行讨论主题 - 只生成回复"""
    print(f"节点3[execute_theme]开始执行，书籍标题：{state['book_title']}")
    print("="*50)
    current_theme_idx = state["current_theme_idx"]
    themes = state["theme"]
    messages = state.get("messages", [])
    insight = state.get("insight", [])

    if current_theme_idx >= len(themes):
        return {"messages": messages, "insight": insight}

    current_theme = themes[current_theme_idx]
    topic = current_theme.get("topic", "")
    question = current_theme.get("question", "")

    # 构建历史
    history_str = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        history_str += f"{role}: {content}\n"

    # ===== 生成回复 =====
    if not messages:
        # 第一轮：直接用设计好的问题
        reply_content = question
    else:
        # 后续轮：生成追问
        followup_prompt = f"""用户正在讨论《{state['book_title']}》的主题「{topic}」。

对话历史：
{history_str}

请继续追问，引导用户更深入地思考。"""
        reply_content = call_llm(followup_prompt)

    # ===== 提取洞察 =====
    if messages:
        last_user_msg = messages[-1].get("content", "")
        if last_user_msg:
            insight_prompt = f"""从用户的回答中提取一个关键洞察（不超过20字）：
用户说：{last_user_msg}"""
            new_insight = call_llm(insight_prompt).strip()
            if new_insight:
                insight.append(new_insight)

    # 更新 messages
    print(f"节点3[execute_theme]生成回复成功，书籍标题：{state['book_title']}")
    print("="*50)
    print(f"回复内容：{reply_content}")
    print("="*50)
    messages.append({"role": "assistant", "content": reply_content})

    return {
        "messages": messages,
        "insight": insight
    }


def reflect(state: AgentState) -> AgentState:
    """节点4: 反思讨论状态 - 决策"""
    print(f"节点4[reflect]开始执行，书籍标题：{state['book_title']}")
    print("="*50)
    themes = state["theme"]
    current_theme_idx = state["current_theme_idx"]
    messages = state.get("messages", [])
    insight = state.get("insight", [])

    # 所有主题都完成了
    if current_theme_idx >= len(themes):
        return {"next": "generate_notes"}

    current_theme = themes[current_theme_idx]
    topic = current_theme.get("topic", "")
    reason = current_theme.get("reason", "")

    # 构建对话历史
    history_str = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        history_str += f"{role}: {content}\n"

    insight_str = ", ".join(insight) if insight else "暂无"

    # ===== 决策 =====
    decision_prompt = f"""作为读书会引导者，评估当前讨论状态。

                    【当前主题】
                    {topic}

                    【选择这个主题的理由】
                    {reason}

                    【已获得的洞察】
                    {insight_str}

                    【对话历史】
                    {history_str}

                    请判断：

                    1. user_interest: 用户对当前主题是否感兴趣？（high/medium/low）
                    - high: 用户在积极思考和分享，回应深入
                    - medium: 用户有回应但比较表面
                    - low: 用户表现出不耐烦或想换话题

                    2. topic_complete: 当前主题是否已经讨论充分？（true/false）

                    3. user_wants_new: 用户是否想聊新话题或对当前主题不感兴趣？（true/false）

                    决策：
                    - continue: 用户对主题感兴趣且话题未完成，继续讨论
                    - next_theme: 主题已讨论充分，进入下一主题
                    - plan_themes: 用户对当前主题不感兴趣或想聊新话题，重新规划主题
                    - finish: 用户主动想要结束讨论。例如：“我们今天就聊到这吧”。

                    输出格式：
                    user_interest: high/medium/low
                    topic_complete: true/false
                    user_wants_new: true/false
                    decision: continue/next_theme/plan_themes/finish
                    reason: 简短说明
                    """

    result = call_llm(decision_prompt)

    # 解析决策
    decision = "continue"
    for line in result.split("\n"):
        if line.startswith("decision:"):
            decision = line.split(":")[1].strip()
    print(f"reflect 决策：{decision}")

    # ===== 返回决策结果 =====
    if decision == "finish":
        return {"next": "generate_notes", "is_complete": True}
    elif decision == "next_theme":
        return {"next": "execute_theme", "current_theme_idx": current_theme_idx + 1}
    elif decision == "plan_themes":
        return {"next": "plan_themes"}
    else:  # continue
        return {"next": "execute_theme"}

def generate_notes(state: AgentState) -> AgentState:
    """
    节点5: 生成读书笔记
    - 整合所有对话、洞察、主题
    - 输出结构化笔记并保存到文件
    """
    print(f"节点5[generate_notes]开始执行")
    print("="*50)

    import os
    
    book_title = state["book_title"]
    book_intro = state.get("book_intro", "")
    perspective = state.get("perspective", [])
    review = state.get("review", [])
    themes = state.get("theme", [])
    messages = state.get("messages", [])
    insight = state.get("insight", [])
    
    # 构建对话摘要
    dialogue_summary = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        dialogue_summary += f"{role}: {content}\n"
    
    # 主题和洞察
    themes_str = "\n".join([f"- {t.get('topic', '')}: {t.get('question', '')}" for t in themes])
    insight_str = "\n".join([f"- {i}" for i in insight])
    perspective_str = "\n".join([f"- {p.get('content', '')}" for p in perspective])
    review_str = "\n".join([f"- {r.get('content', '')}" for r in review])
    
    # ===== LLM 生成笔记 =====
    note_prompt = f"""请为用户生成一份结构化的读书笔记。

【书籍】
{book_title}

【书籍简介】
{book_intro}

【核心观点】
{perspective_str}

【读者观点】
{review_str}

【讨论的主题】
{themes_str}

【用户洞察】
{insight_str}

【对话记录】
{dialogue_summary}

请生成一份完整的读书笔记，包含：
1. 书名和简介
2. 核心观点总结
3. 用户的独特思考（基于洞察）
4. 与其他读者的共鸣/差异
5. 最终总结

输出格式：Markdown"""

    final_note = call_llm(note_prompt)
    
    # ===== 保存到文件 =====
    notes_dir = notes_file_path
    os.makedirs(notes_dir, exist_ok=True)
    
    # 清理文件名
    safe_title = "".join(c for c in book_title if c not in r'<>:"/\|?*')
    file_path = os.path.join(notes_dir, f"{safe_title}.txt")
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_note)
    
    print(f"节点5[generate_notes]执行完成，笔记已保存到：{file_path}")
    print("="*50)
    
    return {
        "final_note": final_note
    }




