from fastapi import APIRouter
from fastapi.responses import FileResponse
import os
from app.models.graph import agent_graph
from app.models.state import AgentState
from app.config import notes_file_path

router = APIRouter()


@router.get("/notes/{book_title}")
async def download_note(book_title: str):
    """下载读书笔记文件"""
    safe_title = "".join(c for c in book_title if c not in r'<>:"/\|?*')
    file_path = os.path.join(notes_file_path, f"{safe_title}.md")
    if not os.path.exists(file_path):
        return {"error": "文件不存在"}
    return FileResponse(file_path, filename=f"{safe_title}.md", media_type="text/markdown")


# 存 states（与 LangGraph checkpoint 配合使用）
conversation_state = {}


@router.post("/chat")
async def chat(request: dict):
    user_id = request.get("user_id")
    book_title = request.get("book_title")
    message = request.get("message")
    api_key = request.get("api_key", "")
    llm_api_key = request.get("llm_api_key", "")

    thread_id = f"{user_id}_{book_title}"
    config = {"configurable": {"thread_id": thread_id}}

    # 新建或恢复会话
    if thread_id not in conversation_state:
        conversation_state[thread_id] = {
            "user_id": user_id,
            "book_id": "",
            "book_title": book_title,
            "api_key": api_key,
            "llm_api_key": llm_api_key,
            "book_intro": "",
            "my_review": [],
            "perspective": [],
            "review": [],
            "collection_plan": [],
            "current_dimension_idx": 0,
            "current_dimension_turns": 0,
            "messages": [],
            "collected_insights": {},
            "dimension_sufficiency": {},
            "dimension_tracking": {},
            "topic_summaries": {},
            "cross_book_hooks": [],
            "insight": [],
            "is_complete": False,
            "final_note": "",
            "run_log": {},
            # 兼容旧字段
            "theme": [],
            "current_theme_idx": 0,
            "decision_history": [],
            "topic_insights": {},
            "current_topic_turns": 0,
            "next": "",
        }

    state = conversation_state[thread_id]
    state["messages"].append({"role": "user", "content": message})

    # 前端主动请求生成笔记
    generate_now = request.get("generate_now", False)

    print(f"\n===== [{thread_id}] =====")
    print(f"collection_plan 维度数: {len(state.get('collection_plan', []))}")
    print(f"current_dimension_idx: {state.get('current_dimension_idx', 0)}")
    print(f"generate_now: {generate_now}")

    try:
        if generate_now and state.get("collection_plan"):
            # 跳过剩余维度，直接走 consolidate
            state["next"] = "consolidate"
            # 归档当前维度
            from app.models.nodes import _safe_summarize
            msgs = state.get("messages", [])
            plan = state.get("collection_plan", [])
            idx = state.get("current_dimension_idx", 0)
            if idx < len(plan) and msgs:
                label = plan[idx].get("label", "")
                llm_k = state.get("llm_api_key", "")
                state["topic_summaries"][label] = _safe_summarize(label, msgs, llm_k)
            agent_graph.update_state(
                config,
                AgentState(state),
                as_node="route_dimension",
            )
            result = agent_graph.invoke(None, config)
        elif state.get("collection_plan"):
            # 已有采集清单 → 从 wait_for_user 继续
            agent_graph.update_state(
                config,
                AgentState(state),
                as_node="wait_for_user",
            )
            result = agent_graph.invoke(None, config)
        else:
            # 首次 → 从头开始
            result = agent_graph.invoke(AgentState(state), config)
    except Exception as e:
        print(f"调用失败: {e}")
        return {"message": "抱歉，处理失败", "is_complete": False}

    # 保存状态
    conversation_state[thread_id] = result
    state = conversation_state[thread_id]

    # 提取本轮新增的 assistant 消息
    all_msgs = result.get("messages", [])
    new_messages = []
    for m in reversed(all_msgs):
        if m.get("role") == "user":
            break
        new_messages.append(m.get("content", ""))
    new_messages.reverse()

    # 构建响应
    collection_plan = result.get("collection_plan", [])
    dim_idx = result.get("current_dimension_idx", 0)
    is_complete = result.get("is_complete", False)
    final_note = result.get("final_note", "")

    # 当前维度信息
    current_dimension = None
    if dim_idx < len(collection_plan):
        d = collection_plan[dim_idx]
        current_dimension = {
            "id": d.get("id"),
            "category": d.get("category"),
            "label": d.get("label"),
            "goal": d.get("goal"),
        }

    # 采集进度
    dim_sufficiency = result.get("dimension_sufficiency", {})
    completed = sum(1 for v in dim_sufficiency.values() if v)
    total = len(collection_plan)

    safe_title = "".join(c for c in book_title if c not in r'<>:"/\|?*')

    return {
        "message": new_messages[-1] if new_messages else "",
        "new_messages": new_messages,
        "is_complete": is_complete,
        "current_dimension": current_dimension,
        "collection_progress": {
            "total": total,
            "completed": completed,
            "sufficient": [k for k, v in dim_sufficiency.items() if v],
            "insufficient": [k for k, v in dim_sufficiency.items() if not v],
        },
        "topic_summaries": result.get("topic_summaries", {}),
        "note_file": f"/api/notes/{safe_title}" if is_complete else None,
        "final_note": final_note if is_complete else None,
        "run_id": result.get("run_log", {}).get("run_id", ""),
    }
