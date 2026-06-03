"""
Agent节点实现
"""
from typing import Dict, List
from app.models.state import AgentState
from app.llm.client import call_llm
from app.tools.rag import rag_add_book_documents, rag_retrieve
from app.utils.get_book_to_json import get_book_info, save_json_file
from app.utils.context import compress_within_topic, summarize_topic
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
    book_data, is_exist = get_book_info(book_title, state.get("api_key", ""))
    if is_exist:
        print(f"节点1[collect_info]书籍信息已存在: data/books/{book_title}.json")
    else:
        save_json_file(book_data, book_title)
        rag_add_book_documents.invoke({"title": book_title})

    book_intro = book_data["info"].get("intro", "").strip()

    print(f"节点1[collect_info]获取划线+笔记，存入 RAG成功，书籍标题：{book_title}")
    print("="*50)
    print(f"书籍简介：{book_intro}")
    print("="*50)
    
    # ===== 步骤 3: 热门划线 → 核心观点 =====
    bestbookmarks = book_data.get("bestbookmarks", {})
    perspective = []
    for item in bestbookmarks.get("items", [])[:5]:
        mark_text = item.get("markText", "").strip()
        if mark_text:
            perspective.append({"content": f"- {mark_text}"})

    print(f"节点1[collect_info]热门划线提取观点: {len(perspective)} 条")

    # ===== 步骤 4: 公开点评 → 读者观点 =====
    public_reviews = book_data.get("publicReviews", {})
    review = []
    for r in public_reviews.get("reviews", [])[:5]:
        content = r.get("review", {}).get("review", {}).get("content", "").strip()
        if content:
            review.append({"content": f"- {content[:200]}"})

    print(f"节点1[collect_info]公开点评提取评论: {len(review)} 条")
    
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
    llm_key = state.get("llm_api_key", "")
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
    recent_history = compress_within_topic(state.get("messages", []), llm_key)

    
    prompt = f"""你是一本读书会的引导者。用户正在讨论一本已读过书。

请根据以下信息，以及当前的讨论历史，规划1-2个新的讨论主题：

【书籍】
{book_title}

【书籍简介】
{book_intro}

【核心观点（本书热门划线）】
{perspective_str}

【读者评价】
{review_str}

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


    result = call_llm(prompt, llm_api_key=llm_key)
    print()
    print("\n"+"="*50)
    print(f"节点2[plan_themes]原始输出：{result}")
    print("="*50 + "\n")
    
    # 解析 JSON
    import json, re
    try:
        match = re.search(r'\[.*\]', result, re.DOTALL)
        if match:
            themes = json.loads(match.group())
        else:
            themes = []
    except:
        themes = []

    if not themes:
        themes = [{
            "topic": f"聊聊《{book_title}》",
            "question": f"读完《{book_title}》，你印象最深的是什么？",
            "reason": "默认主题（JSON 解析失败时兜底）"
        }]
    
    print(f"节点2[plan_themes]规划讨论主题成功，书籍标题：{book_title}")
    print("="*50)
    print(f"讨论主题：{themes}")
    print("="*50)
    
    return {
        "theme": themes,
        "current_theme_idx": 0
    }


def execute_theme(state: AgentState) -> AgentState:
    """节点3: 执行讨论主题 — 生成回复并更新上下文"""
    print(f"节点3[execute_theme]开始执行，书籍标题：{state['book_title']}")
    print("="*50)
    llm_key = state.get("llm_api_key", "")
    current_theme_idx = state["current_theme_idx"]
    themes = state["theme"]
    messages = state.get("messages", [])
    insight = state.get("insight", [])

    if current_theme_idx >= len(themes):
        return {"messages": messages, "insight": insight}

    current_theme = themes[current_theme_idx]
    topic = current_theme.get("topic", "")
    question = current_theme.get("question", "")

    # ===== 生成回复 =====
    user_messages = [m for m in messages if m.get("role") == "user"]
    if len(user_messages) <= 1:
        import random
        openers = [
            f"嗨，欢迎来到读书会。今天我们一起聊聊《{state['book_title']}》吧。",
            f"你好呀，很高兴能和你一起读《{state['book_title']}》。",
            f"又见面了。这次我们读的是《{state['book_title']}》，准备好了吗？",
            f"欢迎回来。今天要聊的是《{state['book_title']}》，先从哪说起呢？",
            f"很高兴见到你。《{state['book_title']}》这本书很有意思，我们慢慢聊。",
        ]
        reply_content = random.choice(openers)
    else:
        history_str = compress_within_topic(messages, llm_key)
        followup_prompt = f"""用户正在讨论《{state['book_title']}》的主题「{topic}」。

对话历史：
{history_str}

请继续追问，引导用户更深入地思考。"""
        reply_content = call_llm(followup_prompt, llm_api_key=llm_key)

    # ===== 提取洞察 =====
    if messages:
        last_user_msg = messages[-1].get("content", "")
        if last_user_msg:
            insight_prompt = f"""从用户的回答中提取一个关键洞察（不超过20字）：
用户说：{last_user_msg}"""
            new_insight = call_llm(insight_prompt, llm_api_key=llm_key).strip()
            if new_insight:
                insight.append(new_insight)

    print(f"节点3[execute_theme]生成回复成功，书籍标题：{state['book_title']}")
    print("="*50)
    print(f"回复内容：{reply_content}")
    print("="*50)
    messages.append({"role": "assistant", "content": reply_content})

    return {
        "messages": messages,
        "insight": insight,
    }


def reflect(state: AgentState) -> AgentState:
    """节点4: 反思讨论状态 — 决策 + 主题归档"""
    print(f"节点4[reflect]开始执行，书籍标题：{state['book_title']}")
    print("="*50)
    llm_key = state.get("llm_api_key", "")
    themes = state["theme"]
    current_theme_idx = state["current_theme_idx"]
    messages = state.get("messages", [])
    insight = state.get("insight", [])
    topic_summaries = state.get("topic_summaries", {})

    if current_theme_idx >= len(themes):
        return {"next": "generate_notes"}

    current_theme = themes[current_theme_idx]
    topic = current_theme.get("topic", "")
    reason = current_theme.get("reason", "")

    history_str = compress_within_topic(messages, llm_key)
    insight_str = ", ".join(insight) if insight else "暂无"

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
                    - finish: 用户主动想要结束讨论。例如："我们今天就聊到这吧"。

                    输出格式：
                    user_interest: high/medium/low
                    topic_complete: true/false
                    user_wants_new: true/false
                    decision: continue/next_theme/plan_themes/finish
                    reason: 简短说明
                    """

    result = call_llm(decision_prompt, llm_api_key=llm_key)

    decision = "continue"
    for line in result.split("\n"):
        if line.startswith("decision:"):
            decision = line.split(":")[1].strip()
    print(f"reflect 决策：{decision}")

    # ===== 主题归档 =====
    if decision in ("next_theme", "plan_themes", "finish"):
        if messages:
            topic_summaries[topic] = summarize_topic(topic, messages, llm_key)
            print(f"reflect 归档主题「{topic}」")

    # ===== 返回决策结果 =====
    if decision == "finish":
        return {"next": "generate_notes", "is_complete": True, "topic_summaries": topic_summaries}
    elif decision == "next_theme":
        return {
            "next": "execute_theme",
            "current_theme_idx": current_theme_idx + 1,
            "topic_summaries": topic_summaries,
            "messages": [],
        }
    elif decision == "plan_themes":
        return {
            "next": "plan_themes",
            "topic_summaries": topic_summaries,
            "messages": [],
        }
    else:  # continue
        return {"next": "execute_theme"}

def generate_notes(state: AgentState) -> AgentState:
    """
    节点5: 生成读书笔记
    - 整合所有主题摘要 + 当前对话 + 洞察
    - 输出结构化笔记并保存到文件
    """
    print(f"节点5[generate_notes]开始执行")
    print("="*50)

    import os

    llm_key = state.get("llm_api_key", "")
    book_title = state["book_title"]
    book_intro = state.get("book_intro", "")
    perspective = state.get("perspective", [])
    review = state.get("review", [])
    themes = state.get("theme", [])
    messages = state.get("messages", [])
    insight = state.get("insight", [])
    topic_summaries = state.get("topic_summaries", {})

    # 各主题摘要
    summaries_lines = []
    for topic_name, summary in topic_summaries.items():
        summaries_lines.append(f"- {topic_name}: {summary}")
    topic_text = "\n".join(summaries_lines) if summaries_lines else "暂无"

    # 当前主题对话
    current_dialogue = "\n".join(
        [f"{m.get('role','')}: {m.get('content','')}" for m in messages]
    )

    insight_str = "\n".join([f"- {i}" for i in insight])
    perspective_str = "\n".join([f"- {p.get('content', '')}" for p in perspective])
    review_str = "\n".join([f"- {r.get('content', '')}" for r in review])

    note_prompt = f"""请为用户生成一份结构化的读书笔记。

【书籍】
{book_title}

【书籍简介】
{book_intro}

【核心观点】
{perspective_str}

【读者观点】
{review_str}

【各主题讨论摘要及用户核心观点】
{topic_text}

【当前对话】
{current_dialogue}

【用户洞察】
{insight_str}

请生成一份完整的读书笔记，包含：
1. 书名和简介
2. 核心观点总结
3. 用户的独特思考（基于各主题讨论）
4. 与其他读者的共鸣/差异
5. 最终总结

输出格式：Markdown"""

    final_note = call_llm(note_prompt, llm_api_key=llm_key)

    notes_dir = notes_file_path
    os.makedirs(notes_dir, exist_ok=True)

    safe_title = "".join(c for c in book_title if c not in r'<>:"/\|?*')
    file_path = os.path.join(notes_dir, f"{safe_title}.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_note)

    print(f"节点5[generate_notes]执行完成，笔记已保存到：{file_path}")
    print("="*50)

    return {"final_note": final_note}




