"""
Agent节点实现 — PostReading Agent v2
Plan-Execute-Reflect 架构，以结构化读书笔记为目标的引导式知识采集。
"""
import json
import re
import os
import random
from typing import Dict, List, Any

from app.models.state import AgentState
from app.llm.client import call_llm
from app.tools.rag import rag_add_book_documents, rag_retrieve
from app.utils.get_book_to_json import get_book_info, save_json_file
from app.utils.context import compress_within_topic, summarize_topic
from app.config import notes_file_path
from app.memory.insight_store import (
    store_insight,
    retrieve_relevant_insights,
    retrieve_cross_book_connections,
)
from app.memory.profile import update_profile
from app.memory.models import UserInsight

# ============ 常量 ============

FIVE_CATEGORIES = ["resonance", "critique", "connection", "action", "emotion"]

CATEGORY_LABELS = {
    "resonance": "你认同的",
    "critique": "你不太认同的",
    "connection": "让你联想到",
    "action": "你打算做出的改变",
    "emotion": "阅读中的情感触动",
}

FINISH_PATTERNS = [
    re.compile(r"今天就[先到聊]?[到这此]|先聊到[这此]|下次再聊|结束吧|不聊了|就[这此]样吧"),
    re.compile(r"(我想|我要|我们|先)?(结束|停止|到此为止)(对话|讨论|聊天|吧)?"),
    re.compile(r"(bye|goodbye|see you)", re.IGNORECASE),
    re.compile(r"谢谢.*(再见|拜拜|下次)"),
    re.compile(r"我(已经)?(累了|困了|要睡了|要去|要走了|先下了)"),
]

MAX_DIMENSION_TURNS = 15


# ============ 节点实现 ============

def wait_for_user(state: AgentState) -> AgentState:
    """空节点：等待用户输入。保留给图结构使用。"""
    return {}


def collect_info(state: AgentState) -> AgentState:
    """节点1: 收集书籍信息 — 拉取微信读书数据、RAG入库、提取观点。"""
    book_title = state["book_title"]

    book_data, is_exist = get_book_info(book_title, state.get("api_key", ""))
    if is_exist:
        print(f"[collect_info] 书籍缓存已存在: data/books/{book_title}.json")
    else:
        save_json_file(book_data, book_title)
        rag_add_book_documents.invoke({"title": book_title})

    book_intro = book_data["info"].get("intro", "").strip()
    print(f"[collect_info] 拉取完成，简介长度: {len(book_intro)}")

    # 热门划线 → 核心观点
    bestbookmarks = book_data.get("bestbookmarks", {})
    perspective = []
    for item in bestbookmarks.get("items", [])[:5]:
        mark_text = item.get("markText", "").strip()
        if mark_text:
            perspective.append({"content": f"- {mark_text}"})
    print(f"[collect_info] 核心观点: {len(perspective)} 条")

    # 公开点评 → 读者观点
    public_reviews = book_data.get("publicReviews", {})
    review = []
    for r in public_reviews.get("reviews", [])[:5]:
        content = r.get("review", {}).get("review", {}).get("content", "").strip()
        if content:
            review.append({"content": f"- {content[:200]}"})
    print(f"[collect_info] 读者观点: {len(review)} 条")

    return {
        "book_intro": book_intro,
        "perspective": perspective,
        "review": review,
    }


# ============ Plan ============

def plan(state: AgentState) -> AgentState:
    """节点2: 生成知识采集清单。分析书籍 + 长期记忆 → 结构化维度列表。"""
    book_title = state["book_title"]
    book_intro = state.get("book_intro", "")
    perspective = state.get("perspective", [])
    review = state.get("review", [])
    llm_key = state.get("llm_api_key", "")
    user_id = state.get("user_id", "")

    print(f"[plan] 开始规划采集清单: {book_title}")

    # ===== 长期记忆检索 =====
    cross_book_hooks = []
    if user_id:
        try:
            query = f"{book_title} {book_intro[:100]}"
            for p in perspective[:3]:
                query += f" {p.get('content', '')[:50]}"
            history_insights = retrieve_relevant_insights(query, user_id, k=5, exclude_book=book_title)
            if history_insights:
                print(f"[plan] 检索到 {len(history_insights)} 条相关历史 insight")
                for ins in history_insights:
                    cross_book_hooks.append({
                        "book": ins.book_title,
                        "dimension": ins.dimension_label,
                        "content": ins.content[:150],
                        "category": ins.dimension_category,
                    })
        except Exception as e:
            print(f"[plan] 长期记忆检索失败: {e}，降级继续")

    # ===== 检索用户划线 =====
    highlights_retrieved = rag_retrieve.invoke({"query": f"{book_title} 划线", "k": 10})

    # ===== 构建 prompt =====
    perspective_str = "\n".join([p.get("content", "") for p in perspective])
    review_str = "\n".join([r.get("content", "") for r in review])
    hooks_str = ""
    if cross_book_hooks:
        hooks_str = "\n【用户在其他书中的相关思考】\n"
        for h in cross_book_hooks:
            hooks_str += f"- 《{h['book']}》- {h['dimension']}: {h['content'][:100]}\n"

    prompt = f"""你是一个深度阅读引导者。用户刚读完《{book_title}》，你要为TA制定一份「知识采集清单」。

目标是：通过对话采集用户对这本书的独特个人思考，最终生成一份真正属于TA的结构化读书笔记。

【书籍简介】
{book_intro[:500]}

【核心观点】
{perspective_str}

【读者评价】
{review_str}

{hooks_str}

【用户的划线】
{highlights_retrieved}

你需要为以下五个类别各设计 1-2 个采集维度（总计 5-8 个）：

1. resonance（共鸣）: 用户认同的观点及原因
2. critique（批判）: 用户不认同或存疑的观点
3. connection（连接）: 与个人经历或其他书的关联
4. action（行动）: 用户打算做出的改变
5. emotion（情感）: 阅读过程中的情感触动

每个维度要求：
- label: 简短标题（展示给用户看的）
- goal: 具体描述要采集什么（必须关联到本书具体内容）
- priority: "high" 或 "normal"
- suggested_angles: 2-3个引导角度

输出 JSON 数组（不要其他内容）：
[
  {{
    "id": "d_001",
    "category": "resonance",
    "label": "对XX观点的共鸣",
    "goal": "了解用户是否认同作者关于XX的论断，是否有亲身经历佐证",
    "priority": "high",
    "cross_book_hook": {json.dumps(hooks_str[:1] if hooks_str else "")},
    "suggested_angles": ["从书籍内容切入...", "从个人经历切入..."]
  }},
  ...
]"""

    # ===== 调用 LLM =====
    result = call_llm(prompt, llm_api_key=llm_key)
    print(f"[plan] LLM 原始输出（前200字）: {result[:200]}")

    try:
        match = re.search(r'\[.*\]', result, re.DOTALL)
        if match:
            collection_plan = json.loads(match.group())
        else:
            collection_plan = []
    except Exception:
        collection_plan = []

    # ===== 兜底 =====
    if not collection_plan:
        collection_plan = [{
            "id": "d_default",
            "category": "connection",
            "label": f"聊聊《{book_title}》",
            "goal": f"了解用户对《{book_title}》的整体感受和个人思考",
            "priority": "high",
            "cross_book_hook": "",
            "suggested_angles": [
                f"读完《{book_title}》，你印象最深的是什么？",
                "这本书和你的生活有什么关联？",
            ],
        }]

    print(f"[plan] 生成 {len(collection_plan)} 个采集维度")
    for d in collection_plan:
        print(f"  [{d.get('category')}] {d.get('label')} (priority={d.get('priority')})")

    return {
        "collection_plan": collection_plan,
        "current_dimension_idx": 0,
        "current_dimension_turns": 0,
        "cross_book_hooks": cross_book_hooks,
        # 兼容
        "theme": collection_plan,
        "current_theme_idx": 0,
    }


# ============ Execute ============

def execute(state: AgentState) -> AgentState:
    """节点3: 围绕当前维度引导用户 — 每次一轮对话。"""
    book_title = state["book_title"]
    llm_key = state.get("llm_api_key", "")

    collection_plan = state.get("collection_plan", [])
    dim_idx = state.get("current_dimension_idx", 0)
    messages = state.get("messages", [])
    topic_summaries = state.get("topic_summaries", {})
    dimension_tracking = state.get("dimension_tracking", {})
    collected_insights = state.get("collected_insights", {})

    if dim_idx >= len(collection_plan):
        return {"messages": messages}

    current_dim = collection_plan[dim_idx]
    dim_id = current_dim.get("id", f"d_{dim_idx}")
    category = current_dim.get("category", "connection")
    label = current_dim.get("label", "")
    goal = current_dim.get("goal", "")
    suggested_angles = current_dim.get("suggested_angles", [])

    # 初始化维度追踪
    if dim_id not in dimension_tracking:
        dimension_tracking[dim_id] = {"turns": 0, "angles_used": [], "user_stance": "", "raw_insights": []}
    tracking = dimension_tracking[dim_id]
    turns = tracking.get("turns", 0)

    print(f"[execute] 维度 [{dim_id}] {label}，第 {turns + 1} 轮")

    # ===== RAG 检索相关划线 =====
    user_messages = [m for m in messages if m.get("role") == "user"]
    last_user_msg = user_messages[-1].get("content", "") if user_messages else ""
    rag_query = f"{label} {last_user_msg}" if last_user_msg else label
    relevant_highlights = rag_retrieve.invoke({"query": rag_query, "k": 5})
    highlights_context = f"\n【用户相关划线】\n{relevant_highlights}" if relevant_highlights else ""

    # 未用过的引导角度（提前声明，避免 UnboundLocalError）
    available_angles = [a for a in suggested_angles if a not in tracking.get("angles_used", [])]

    # ===== 生成回复 =====
    if turns == 0 and not topic_summaries:
        # 首次对话：打招呼 + 引出第一个维度
        openers = [
            f"嗨，欢迎来到读书会。今天我们一起聊聊《{book_title}》吧。",
            f"你好呀，很高兴能和你一起读《{book_title}》。",
            f"又见面了。这次我们读的是《{book_title}》，准备好了吗？",
            f"欢迎回来。今天要聊的是《{book_title}》，我们先从这本书的核心观点说起。",
            f"很高兴见到你。《{book_title}》这本书很有意思，我们慢慢聊。",
        ]
        greeting = random.choice(openers)
        messages.append({"role": "assistant", "content": greeting})

        intro_prompt = f"""你们刚开始聊《{book_title}》，第一个话题是「{label}」。

采集目标：{goal}
{highlights_context}

请用2-3句话自然引出这个话题，像朋友聊天一样，邀请对方分享想法。不要打招呼（已打过招呼），直接切入。"""
        theme_intro = call_llm(intro_prompt, llm_api_key=llm_key)
        messages.append({"role": "assistant", "content": theme_intro})
        reply_content = theme_intro

    elif turns == 0 and topic_summaries:
        # 切换维度：自然过渡
        prev_topics = "、".join(topic_summaries.keys())
        transition_prompt = f"""你们刚聊完《{book_title}》的「{prev_topics}」，现在切换到新话题「{label}」。

采集目标：{goal}
{highlights_context}

请用2-3句话自然过渡到新话题。简短回顾一下刚才聊的，再引出新话题。不要打招呼。"""
        reply_content = call_llm(transition_prompt, llm_api_key=llm_key)
        messages.append({"role": "assistant", "content": reply_content})

    else:
        # 继续当前维度：回应 + 追问
        angle_hint = ""
        if available_angles:
            angle_hint = f"\n尝试从以下角度引导（但不要硬套，自然即可）：{available_angles[0]}"

        history_str = compress_within_topic(messages, llm_key)
        followup_prompt = f"""你和用户正在聊《{book_title}》，当前话题是「{label}」。采集目标是：{goal}

对话历史：
{history_str}
{highlights_context}
{angle_hint}

像朋友聊书一样自然回应，2-4句话。先回应ta说的，再顺着追问一句。如果用户划线中有相关原文，直接引用（"我看到你划了这句——「...原文...」"），不要含糊地说"你划线的这句"而不引用内容。不要长篇大论。"""
        reply_content = call_llm(followup_prompt, llm_api_key=llm_key)
        messages.append({"role": "assistant", "content": reply_content})

    # ===== 提取 insight =====
    if last_user_msg:
        insight_prompt = f"""从用户的回答中提取一个关键洞察（不超过30字）。如果用户只是附和或没有实质内容，输出"无实质洞察"。

用户说：{last_user_msg}"""
        new_insight = call_llm(insight_prompt, llm_api_key=llm_key).strip()
        if new_insight and new_insight != "无实质洞察":
            tracking["raw_insights"].append(new_insight)
            if dim_id not in collected_insights:
                collected_insights[dim_id] = []
            collected_insights[dim_id].append({
                "content": new_insight,
                "turn": turns + 1,
            })

    # 追踪角度使用
    if available_angles:
        tracking["angles_used"].append(available_angles[0])
    tracking["turns"] = turns + 1
    dimension_tracking[dim_id] = tracking

    return {
        "messages": messages,
        "current_dimension_turns": turns + 1,
        "dimension_tracking": dimension_tracking,
        "collected_insights": collected_insights,
    }


# ============ 维度路由函数 ============

def route_after_execute(state: AgentState) -> str:
    """Execute 之后的条件边：纯规则，非 LLM。"""
    # 检查 finish 信号
    messages = state.get("messages", [])
    user_messages = [m for m in messages if m.get("role") == "user"]
    if user_messages:
        last_msg = user_messages[-1].get("content", "")
        if _check_finish_signals(last_msg):
            print(f"[router] 检测到 finish 信号 → consolidate")
            return "consolidate"

    # 获取当前维度状态
    collection_plan = state.get("collection_plan", [])
    dim_idx = state.get("current_dimension_idx", 0)
    turns = state.get("current_dimension_turns", 0)
    dimension_tracking = state.get("dimension_tracking", {})
    dim_sufficiency = state.get("dimension_sufficiency", {})

    if dim_idx >= len(collection_plan):
        return "consolidate"

    current_dim = collection_plan[dim_idx]
    dim_id = current_dim.get("id", f"d_{dim_idx}")

    # 轮次上限
    if turns >= MAX_DIMENSION_TURNS:
        print(f"[router] {dim_id} 达到轮次上限 → 标记 insufficient")
        dim_sufficiency[dim_id] = False
        if dim_idx + 1 < len(collection_plan):
            return "next_dimension"
        return "consolidate"

    # 简单判断：用户本轮是否有实质内容
    tracking = dimension_tracking.get(dim_id, {})
    raw_insights = tracking.get("raw_insights", [])

    if raw_insights and turns < 3:
        # 有实质内容且追问次数少 → 再问一轮
        return "continue_dimension"
    elif raw_insights:
        # 有实质内容且追问够了 → 够了
        print(f"[router] {dim_id} 有 {len(raw_insights)} 条 insight，判定 sufficient")
        dim_sufficiency[dim_id] = True
        if dim_idx + 1 < len(collection_plan):
            return "next_dimension"
        return "consolidate"
    elif turns < 3:
        # 无实质内容但追问少 → 换角度继续
        return "continue_dimension"
    else:
        # 无实质内容且追问够了 → 标记 insufficient
        print(f"[router] {dim_id} 无实质 insight 且已达 {turns} 轮 → insufficient")
        dim_sufficiency[dim_id] = False
        if dim_idx + 1 < len(collection_plan):
            return "next_dimension"
        return "consolidate"


def _check_finish_signals(text: str) -> bool:
    """检测用户显式结束意图。"""
    if not text:
        return False
    for pattern in FINISH_PATTERNS:
        if pattern.search(text):
            return True
    return False


# ============ 维度路由节点 ============

def route_dimension(state: AgentState) -> AgentState:
    """路由节点：Execute 之后，决定继续/换维度/进入 Consolidate。纯规则，不调用 LLM。"""
    collection_plan = state.get("collection_plan", [])
    dim_idx = state.get("current_dimension_idx", 0)
    turns = state.get("current_dimension_turns", 0)
    dimension_tracking = state.get("dimension_tracking", {})
    dim_sufficiency = state.get("dimension_sufficiency", {})
    messages = state.get("messages", [])
    topic_summaries = state.get("topic_summaries", {})
    llm_key = state.get("llm_api_key", "")

    if dim_idx >= len(collection_plan):
        print("[route_dimension] 无更多维度 → consolidate")
        return {"next": "consolidate"}

    current_dim = collection_plan[dim_idx]
    dim_id = current_dim.get("id", f"d_{dim_idx}")
    label = current_dim.get("label", "")

    # 检查 finish 信号
    user_messages = [m for m in messages if m.get("role") == "user"]
    if user_messages and _check_finish_signals(user_messages[-1].get("content", "")):
        print(f"[route_dimension] finish 信号 → consolidate")
        if messages:
            topic_summaries[label] = _safe_summarize(label, messages, llm_key)
        return {"next": "consolidate", "topic_summaries": topic_summaries}

    # 轮次上限
    if turns >= MAX_DIMENSION_TURNS:
        print(f"[route_dimension] {dim_id} 轮次上限 → 下一维度")
        dim_sufficiency[dim_id] = False
        if messages:
            topic_summaries[label] = _safe_summarize(label, messages, llm_key)
        if dim_idx + 1 < len(collection_plan):
            return {
                "next": "next_dimension",
                "current_dimension_idx": dim_idx + 1,
                "current_dimension_turns": 0,
                "messages": [],
                "dimension_sufficiency": dim_sufficiency,
                "topic_summaries": topic_summaries,
            }
        return {"next": "consolidate", "dimension_sufficiency": dim_sufficiency, "topic_summaries": topic_summaries}

    # 判断 insight 质量
    tracking = dimension_tracking.get(dim_id, {})
    raw_insights = tracking.get("raw_insights", [])

    if raw_insights and turns >= 2:
        # 有实质内容 → sufficient
        print(f"[route_dimension] {dim_id} sufficient（{len(raw_insights)} insights）")
        dim_sufficiency[dim_id] = True
        if messages:
            topic_summaries[label] = _safe_summarize(label, messages, llm_key)
        if dim_idx + 1 < len(collection_plan):
            return {
                "next": "next_dimension",
                "current_dimension_idx": dim_idx + 1,
                "current_dimension_turns": 0,
                "messages": [],
                "dimension_sufficiency": dim_sufficiency,
                "topic_summaries": topic_summaries,
            }
        return {"next": "consolidate", "dimension_sufficiency": dim_sufficiency, "topic_summaries": topic_summaries}
    elif not raw_insights and turns >= 3:
        # 追问多次仍无内容 → insufficient
        print(f"[route_dimension] {dim_id} insufficient")
        dim_sufficiency[dim_id] = False
        if messages:
            topic_summaries[label] = _safe_summarize(label, messages, llm_key)
        if dim_idx + 1 < len(collection_plan):
            return {
                "next": "next_dimension",
                "current_dimension_idx": dim_idx + 1,
                "current_dimension_turns": 0,
                "messages": [],
                "dimension_sufficiency": dim_sufficiency,
                "topic_summaries": topic_summaries,
            }
        return {"next": "consolidate", "dimension_sufficiency": dim_sufficiency, "topic_summaries": topic_summaries}
    else:
        # 继续当前维度
        print(f"[route_dimension] {dim_id} continue（turns={turns}）")
        return {"next": "__end__"}


def _safe_summarize(label: str, messages: list, llm_key: str) -> str:
    """安全归档 — summarize_topic 的 wrapper。"""
    try:
        return summarize_topic(label, messages, llm_key)
    except Exception as e:
        print(f"[router] 归档失败: {e}")
        return f"[归档失败] {len(messages)} 条消息"


# ============ Consolidate ============

def consolidate(state: AgentState) -> AgentState:
    """节点4: 跨维度综合检查 — 矛盾、缺口、新发现。"""
    print("[consolidate] 开始跨维度综合检查")

    llm_key = state.get("llm_api_key", "")
    book_title = state.get("book_title", "")
    book_intro = state.get("book_intro", "")
    perspective = state.get("perspective", [])
    collection_plan = state.get("collection_plan", [])
    collected_insights = state.get("collected_insights", {})
    dimension_sufficiency = state.get("dimension_sufficiency", {})
    topic_summaries = state.get("topic_summaries", {})

    # 构建维度完成情况
    dims_status = []
    for d in collection_plan:
        dim_id = d.get("id", "")
        dims_status.append({
            "id": dim_id,
            "category": d.get("category", ""),
            "label": d.get("label", ""),
            "goal": d.get("goal", ""),
            "sufficient": dimension_sufficiency.get(dim_id, False),
            "insights": collected_insights.get(dim_id, []),
        })

    perspective_str = "\n".join([p.get("content", "") for p in perspective])
    summaries_str = "\n".join([f"- {k}: {v}" for k, v in topic_summaries.items()])

    prompt = f"""你已经完成了《{book_title}》的知识采集对话，现在做一次跨维度综合检查。

【书籍简介】
{book_intro[:300]}

【书籍核心观点】
{perspective_str}

【各维度采集状态】
{json.dumps(dims_status, ensure_ascii=False, indent=2)}

【各维度对话摘要】
{summaries_str}

请检查以下三项，输出 JSON：

1. 矛盾检测：不同维度的 insight 是否存在逻辑矛盾？
   例如：D1 说用户认同直觉判断，D2 说用户认为直觉在投资中是灾难
   如果有矛盾，生成一个追问来澄清

2. 缺口检测：书籍的核心观点是否都被覆盖了？
   有没有重要的观点完全没被讨论？

3. 新发现：对话中用户是否提到了采集清单之外、但值得深入的内容？

输出 JSON（只输出 JSON）：
{{
  "issues": [
    {{
      "type": "contradiction | gap | discovery",
      "severity": "high | normal",
      "description": "...",
      "suggested_action": "add_followup | add_dimension | replan",
      "followup_question": "如果需要追加追问，请给出具体的引导问题"
    }}
  ],
  "overall": "proceed | revise"
}}"""

    result = call_llm(prompt, llm_api_key=llm_key)
    print(f"[consolidate] LLM 输出（前200字）: {result[:200]}")

    try:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            consolidation_result = json.loads(match.group())
        else:
            consolidation_result = {"issues": [], "overall": "proceed"}
    except Exception:
        consolidation_result = {"issues": [], "overall": "proceed"}

    issues = consolidation_result.get("issues", [])
    print(f"[consolidate] 发现 {len(issues)} 个问题: {[i.get('type') for i in issues]}")

    return {
        "dimension_sufficiency": dimension_sufficiency,
        "run_log": state.get("run_log", {}) | {"consolidation": consolidation_result},
    }


def route_after_consolidate(state: AgentState) -> str:
    """Consolidate 之后的条件边。"""
    run_log = state.get("run_log", {})
    consolidation = run_log.get("consolidation", {})
    overall = consolidation.get("overall", "proceed")
    issues = consolidation.get("issues", [])

    if overall == "proceed" and not issues:
        return "generate_notes"

    # 有 issues — 检查是否有需要追加的
    has_followup = any(i.get("suggested_action") == "add_followup" for i in issues)
    has_new_dimension = any(i.get("suggested_action") in ("add_dimension", "replan") for i in issues)

    if has_new_dimension:
        return "plan"
    elif has_followup:
        return "execute"
    else:
        return "generate_notes"


# ============ Generate Notes ============

def generate_notes(state: AgentState) -> AgentState:
    """节点5: 生成结构化读书笔记 — 按采集清单 category 组织。"""
    print("[generate_notes] 开始生成笔记")

    llm_key = state.get("llm_api_key", "")
    user_id = state.get("user_id", "")
    book_title = state["book_title"]
    book_intro = state.get("book_intro", "")
    perspective = state.get("perspective", [])
    review = state.get("review", [])
    collection_plan = state.get("collection_plan", [])
    messages = state.get("messages", [])
    collected_insights = state.get("collected_insights", {})
    dimension_sufficiency = state.get("dimension_sufficiency", {})
    topic_summaries = state.get("topic_summaries", {})

    # ===== 按 category 组织内容 =====
    sections = {}
    insufficient_labels = []
    for d in collection_plan:
        dim_id = d.get("id", "")
        category = d.get("category", "connection")
        label = d.get("label", "")
        sufficient = dimension_sufficiency.get(dim_id, False)
        insights = collected_insights.get(dim_id, [])
        summary = topic_summaries.get(label, "")

        if category not in sections:
            sections[category] = []
        sections[category].append({
            "label": label,
            "sufficient": sufficient,
            "insights": [i.get("content", "") for i in insights],
            "summary": summary,
        })
        if not sufficient:
            insufficient_labels.append(label)

    # 组织各 category 文本
    def _section_text(cat: str) -> str:
        items = sections.get(cat, [])
        parts = []
        for item in items:
            parts.append(f"**{item['label']}**")
            if item["summary"]:
                parts.append(f"讨论摘要: {item['summary']}")
            if item["insights"]:
                parts.append(f"用户思考: {'; '.join(item['insights'])}")
            if not item["sufficient"]:
                parts.append("[未充分讨论]")
        return "\n\n".join(parts) if parts else "暂无"

    # ===== RAG 检索划线 =====
    topic_names = " ".join(topic_summaries.keys()) if topic_summaries else ""
    notes_rag_query = f"{book_title} {topic_names}"
    notes_highlights = rag_retrieve.invoke({"query": notes_rag_query, "k": 15})

    # ===== 长期记忆跨书关联 =====
    cross_book_section = ""
    if user_id:
        try:
            all_dim_labels = " ".join([d.get("label", "") for d in collection_plan])
            connections = retrieve_cross_book_connections(book_title, all_dim_labels, user_id, k=5)
            if connections:
                cross_book_lines = []
                for c in connections:
                    cross_book_lines.append(
                        f"- 在《{c.target_book}》中，你曾思考过「{c.target_dimension_label}」"
                        f"：{c.target_content[:100]} — **{c.relationship}**"
                    )
                cross_book_section = (
                    "## 6. 你的阅读旅程\n\n"
                    + "\n".join(cross_book_lines)
                )
        except Exception as e:
            print(f"[generate_notes] 跨书关联检索失败: {e}")

    # ===== prompt =====
    perspective_str = "\n".join([p.get("content", "") for p in perspective])
    review_str = "\n".join([r.get("content", "") for r in review])
    insufficient_note = "\n> [未充分讨论]：" + "、".join(insufficient_labels) if insufficient_labels else ""

    note_prompt = f"""请为用户生成一份结构化的读书笔记。

【书籍】
{book_title}

【书籍简介】
{book_intro}

【核心观点】
{perspective_str}

【读者观点】
{review_str}

【用户在各维度的思考】
## 你认同的...
{_section_text("resonance")}

## 你不太认同的...
{_section_text("critique")}

## 让你联想到...
{_section_text("connection")}

## 你打算做出的改变
{_section_text("action")}

## 阅读中的情感触动
{_section_text("emotion")}

【用户划线原文】
{notes_highlights}

请生成一份完整的读书笔记（Markdown 格式），包含：
1. 书名和简介
2. 核心观点总结
3. 用户的独特思考（按5个类别组织，引用其划线原文佐证）
4. 与其他读者的共鸣/差异
5. 最终总结

每部分要体现「这个读者」的独特视角，不是泛泛而谈的书评。有划线佐证的地方必须引用原文。
{insufficient_note}"""

    final_note = call_llm(note_prompt, llm_api_key=llm_key)

    if cross_book_section:
        final_note += f"\n\n{cross_book_section}"

    # ===== 保存 =====
    os.makedirs(notes_file_path, exist_ok=True)
    safe_title = "".join(c for c in book_title if c not in r'<>:"/\|?*')
    file_path = os.path.join(notes_file_path, f"{safe_title}.md")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_note)

    print(f"[generate_notes] 笔记已保存: {file_path}")

    return {
        "final_note": final_note,
        "is_complete": True,
    }


# ============ Reflect ============

def reflect(state: AgentState) -> AgentState:
    """节点6: 对照采集清单，整体评估笔记质量。放在 Generate Notes 之后。"""
    print("[reflect] 开始评估笔记质量")

    llm_key = state.get("llm_api_key", "")
    final_note = state.get("final_note", "")
    collection_plan = state.get("collection_plan", [])
    collected_insights = state.get("collected_insights", {})

    if not final_note:
        return {"is_complete": True}

    # 构建对照表
    dims_checklist = []
    for d in collection_plan:
        dim_id = d.get("id", "")
        dims_checklist.append({
            "id": dim_id,
            "category": d.get("category", ""),
            "label": d.get("label", ""),
            "goal": d.get("goal", ""),
            "priority": d.get("priority", "normal"),
            "insights_collected": len(collected_insights.get(dim_id, [])),
        })

    prompt = f"""你是一个读书笔记质量评估者。请对照采集清单，评估这份笔记是否达到了采集目标。

【采集清单及目标】
{json.dumps(dims_checklist, ensure_ascii=False, indent=2)}

【生成的笔记】
{final_note[:3000]}

请逐维度评估，然后给出整体判断。输出 JSON（只输出 JSON）：

{{
  "dimension_evaluations": [
    {{
      "dimension_id": "d_001",
      "in_note": true,
      "quality": "good | thin | missing",
      "issue": "如果 quality 不是 good，说明问题"
    }}
  ],
  "overall": "pass | revise_dimension | replan",
  "weak_dimensions": ["需要补充的维度 id 列表"],
  "summary": "整体评估说明（不超过100字）"
}}

判断标准：
- good: 笔记中该维度有深度的个人思考 + 具体例子
- thin: 有涉及但内容太浅，只有一两句话
- missing: 完全没有覆盖
- overall pass: 所有 high priority 维度 quality=good
- overall revise_dimension: 个别维度 thin/missing，需要补充
- overall replan: 多个 high 维度有问题，采集方向需要调整"""

    result = call_llm(prompt, llm_api_key=llm_key)
    print(f"[reflect] LLM 输出（前200字）: {result[:200]}")

    try:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            reflect_result = json.loads(match.group())
        else:
            reflect_result = {"overall": "pass", "dimension_evaluations": [], "weak_dimensions": []}
    except Exception:
        reflect_result = {"overall": "pass", "dimension_evaluations": [], "weak_dimensions": []}

    overall = reflect_result.get("overall", "pass")
    print(f"[reflect] 评估结果: {overall}")

    # ===== 写入长期记忆 + 评测（仅 pass 时） =====
    run_log = state.get("run_log", {})
    if overall == "pass":
        _write_insights_to_memory(state)
        # 运行内置评测
        try:
            from app.evaluation.scorer import run_full_evaluation
            collection_plan = state.get("collection_plan", [])
            dim_sufficiency = state.get("dimension_sufficiency", {})
            consolidation = run_log.get("consolidation", {})
            eval_log = run_full_evaluation(
                final_note=final_note,
                collection_plan=collection_plan,
                dimension_sufficiency=dim_sufficiency,
                reflect_result=reflect_result,
                consolidation_result=consolidation,
                llm_api_key=llm_key,
            )
            run_log = run_log | eval_log
            print(f"[reflect] 评测完成: overall_score={eval_log.get('overall_score')}")
        except Exception as e:
            print(f"[reflect] 评测失败: {e}")

    return {
        "is_complete": overall == "pass",
        "run_log": run_log | {"reflect": reflect_result},
    }


def route_after_reflect(state: AgentState) -> str:
    """Reflect 之后的条件边。"""
    run_log = state.get("run_log", {})
    reflect_result = run_log.get("reflect", {})
    overall = reflect_result.get("overall", "pass")

    if overall == "pass":
        return "review"
    elif overall == "revise_dimension":
        return "execute"
    else:  # replan
        return "plan"


def _write_insights_to_memory(state: AgentState):
    """将 sufficient 维度的 insight 写入长期记忆。"""
    user_id = state.get("user_id", "")
    book_title = state.get("book_title", "")
    collection_plan = state.get("collection_plan", [])
    collected_insights = state.get("collected_insights", {})
    dimension_sufficiency = state.get("dimension_sufficiency", {})

    if not user_id:
        return

    for d in collection_plan:
        dim_id = d.get("id", "")
        if not dimension_sufficiency.get(dim_id, False):
            continue
        insights = collected_insights.get(dim_id, [])
        if not insights:
            continue

        # 合并所有 insight 内容
        content = "；".join([i.get("content", "") for i in insights])
        if not content.strip():
            continue

        insight = UserInsight(
            user_id=user_id,
            book_title=book_title,
            dimension_category=d.get("category", ""),
            dimension_label=d.get("label", ""),
            content=content,
            composite_score=3.0,  # sufficient 的维度默认 3.0
            scores={"depth": 2, "specificity": 2, "personalization": 2, "evidence": 1},
        )
        store_insight(insight)


# ============ Review ============

def review(state: AgentState) -> AgentState:
    """节点7: Human-in-the-loop — 展示笔记，等待用户反馈。"""
    # 更新用户画像
    user_id = state.get("user_id", "")
    if user_id:
        try:
            update_profile(user_id)
            print(f"[review] 用户画像已更新: {user_id}")
        except Exception as e:
            print(f"[review] 画像更新失败: {e}")

    # 标记完成 — 等待用户 approve/revise
    return {"is_complete": True}


def route_after_review(state: AgentState) -> str:
    """Review 之后的条件边。用户通过前端按钮选择 approve 或 revise。"""
    # 用户的反馈存在 state 中，由 routes.py 在 invoke 时传入
    is_complete = state.get("is_complete", True)
    if is_complete:
        return "approved"
    return "revise"
