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

def collect_info(state: AgentState) -> AgentState:
    """
    节点1: 收集书籍信息
    - 获取划线 → RAG
    - 获取笔记 → RAG
    - 搜索书籍核心观点 → state
    - 搜索读者观点 → state
    """
    book_title = state["book_title"]
    book_id = state["book_id"]
    
    # ===== 步骤 1-2: 获取划线+笔记，存入 RAG =====
    # 获取书籍信息
    book_info = get_book_info(book_id)
    # 保存书籍信息到 JSON 文件
    save_json_file(book_info, book_title)
    # 添加书籍文档到 RAG 系统
    rag_add_book_documents(book_title)
    
    # 提取书籍简介
    book_intro = book_info.get("intro", "")
    
    # ===== 步骤 3: 搜索书籍核心观点 → state =====
    perspective_raw = search_books_perspective.invoke({"book_title": book_title})
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
    
    # ===== 检索用户划线（个性化核心）=====
    # 基于书籍标题检索用户的划线内容
    highlights_retrieved = rag_retrieve.invoke({
        "query": f"{book_title} 划线",
        "k": 20
    })
    
    # 构建 prompt
    perspective_str = "\n".join([p.get("content", "") for p in perspective])
    review_str = "\n".join([r.get("content", "") for r in review])
    
    prompt = f"""你是一本读书会的引导者。用户刚读完《{book_title}》，想深入讨论。

请根据以下信息，规划3-5个讨论主题（要结合用户的划线重点）：

【书籍简介】
{book_intro}

【用户的划线内容】（个性化参考）
{highlights_retrieved}

【核心观点】
{perspective_str}

【读者观点】
{review_str}

请为每个主题设计1-2个开放式问题，引导用户思考和表达。问题要基于用户的划线内容，越个性化越好。

输出格式（JSON数组）：
[
  {{"topic": "主题1名称", "question": "引导问题"}},
  {{"topic": "主题2名称", "question": "引导问题"}},
  ...
]"""

    result = call_llm(prompt)
    
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
    
    return {
        "theme": themes,
        "current_theme_idx": 0
    }


def execute_theme(state: AgentState) -> AgentState:
    """
    节点3: 执行讨论主题
    - 从 state 中获取当前主题
    - 用 LLM 生成主题的回答
    - 更新 state 中的回答
    """
    current_theme_idx = state["current_theme_idx"]
    themes = state["theme"]
    
    if current_theme_idx >= len(themes):
        return state  # 所有主题已处理
    
    current_theme = themes[current_theme_idx]
    topic = current_theme.get("topic", "")
    question = current_theme.get("question", "")
    
    messages = state.get("messages", [])
    insight = state.get("insight", [])
    
    # 构建对话历史
    history_str = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        history_str += f"{role}: {content}\n"
    
    # ===== ReAct 判断：需要做什么？=====
    react_prompt = f"""你是一本读书会的引导者。现在要讨论主题「{topic}」。

【主题问题】
{question}

【对话历史】
{history_str}

请判断接下来应该做什么（只选一个）：

A. "ask" - 用户还没回答清楚，需要继续追问
B. "elaborate" - 需要补充背景知识或引用书中的内容
C. "summarize" - 用户回答得不错，可以先小结一下这个观点
D. "next" - 这个主题已经讨论充分，可以进入下一个

同时判断这个问题之前是否讨论过类似的。

输出格式：
action: A/B/C/D
reason: 简短说明原因
already_discussed: true/false"""

    react_result = call_llm(react_prompt)
    
    # 解析 ReAct 结果
    action = "ask"
    already_discussed = False
    for line in react_result.split("\n"):
        if line.startswith("action:"):
            action = line.split(":")[1].strip()
        if line.startswith("already_discussed:"):
            already_discussed = line.split(":")[1].strip() == "true"
    
    # ===== 根据 action 决定回复 =====
    reply_content = ""
    
    if action == "elaborate":
        # 需要补充背景 → RAG 检索
        retrieved = rag_retrieve.invoke({
            "query": f"{topic} {question}",
            "k": 5
        })
        elaborate_prompt = f"""用户正在讨论《{state['book_title']}》的主题「{topic}」。

【用户说的】
{history_str}

【参考内容】
{retrieved}

请基于参考内容，补充背景信息或引用书中的观点，引导用户深入思考。"""

        reply_content = call_llm(elaborate_prompt)
    
    elif action == "summarize":
        # 小结当前观点
        summarize_prompt = f"""请简洁小结用户关于「{topic}」的观点，并自然地过渡到下一个问题。"""
        reply_content = call_llm(summarize_prompt)
    
    elif action == "next" or already_discussed:
        # 跳过或进入下一主题
        current_theme_idx += 1
        if current_theme_idx < len(themes):
            next_topic = themes[current_theme_idx].get("topic", "")
            reply_content = f"好的，那我们来聊聊「{next_topic}」吧。"
        else:
            reply_content = "这个话题先聊到这里。"
    
    else:
        # ask - 继续追问
        # 如果是第一次问这个问题，直接用设计好的问题
        if not messages:
            reply_content = question
        else:
            # 继续深入问
            followup_prompt = f"""用户关于「{topic}」的讨论：
{history_str}

请继续追问，引导用户更深入地思考。"""
            reply_content = call_llm(followup_prompt)
    
    # ===== 提取洞察 =====
    if messages:
        last_user_msg = messages[-1].get("content", "") if messages else ""
        insight_prompt = f"""从用户的回答中提取一个关键洞察（不超过20字）：
        
用户说：{last_user_msg}"""
        new_insight = call_llm(insight_prompt).strip()
        if new_insight:
            insight.append(new_insight)
    
    # ===== 更新 state =====
    messages.append({"role": "assistant", "content": reply_content})
    
    return {
        "messages": messages,
        "insight": insight,
        "current_theme_idx": current_theme_idx
    }



def reflect(state: AgentState) -> AgentState:
    """
    节点4: 反思
    - 判断当前主题是否完成
    - 决定：继续当前主题 / 下一主题 / 生成笔记
    """
    themes = state.get("theme", [])
    current_theme_idx = state.get("current_theme_idx", 0)
    insight = state.get("insight", [])
    messages = state.get("messages", [])
    
    # 对话轮数（assistant 回复次数）
    assistant_turns = sum(1 for m in messages if m.get("role") == "assistant")
    
    # 构建上下文
    current_theme = themes[current_theme_idx] if current_theme_idx < len(themes) else {}
    topic = current_theme.get("topic", "")
    
    # ===== LLM 判断：是否完成？=====
    reflect_prompt = f"""判断用户关于主题「{topic}」的讨论是否已经充分。

【对话轮数】
{assistant_turns} 轮

【已提取的洞察】
{insight}

请判断：
A. "continue" - 还需要继续讨论
B. "next" - 可以进入下一主题
C. "finish" - 所有主题完成，可以生成笔记

输出格式：
decision: A/B/C
reason: 简短说明"""

    result = call_llm(reflect_prompt)
    
    # 解析决策
    decision = "continue"
    for line in result.split("\n"):
        if line.startswith("decision:"):
            decision = line.split(":")[1].strip()
    
    # ===== 根据决策路由 =====
    if decision == "finish":
        # 全部主题完成 → 生成笔记
        return {
            "is_complete": True
        }
    elif decision == "next":
        # 进入下一主题
        current_theme_idx += 1
        if current_theme_idx >= len(themes):
            # 没有更多主题 → 生成笔记
            return {"is_complete": True}
        else:
            # 重置当前主题的对话，继续
            return {"current_theme_idx": current_theme_idx}
    else:
        # 继续当前主题
        return {"current_theme_idx": current_theme_idx}


def generate_notes(state: AgentState) -> AgentState:
    """
    节点5: 生成读书笔记
    - 整合所有对话、洞察、主题
    - 输出结构化笔记并保存到文件
    """
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
    
    return {
        "final_note": final_note
    }




