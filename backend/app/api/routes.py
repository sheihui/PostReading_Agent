from fastapi import APIRouter
# from pydantic import BaseModel
from app.models.graph import agent_graph


router = APIRouter()

# 存states
conversation_state = {}

@router.post("/chat")
async def chat(request: dict):
    user_id = request.get("user_id")
    # book_id = request.get("book_id")
    book_title = request.get("book_title")
    message = request.get("message")

    thread_id = f"{user_id}"
    config = {"configurable": {"thread_id": thread_id}}

    if thread_id not in conversation_state:
        conversation_state[thread_id] = {
            "user_id": user_id,
            "book_id": "",
            "book_title": book_title,
            "book_intro": "",
            "my_review": [],
            "perspective": [],
            "review": [],
            "theme": [],
            "current_theme_idx": 0,
            "messages": [],
            "insight": [],
            "is_complete": False,
            "final_note": ""
        }

    # 添加用户消息
    state = conversation_state[thread_id]
    state["messages"].append({"role": "user", "content": message})

    print()
    print(thread_id)
    print(f"===== 当前会话 state['theme']：{state['theme']} =====")
    print(f"===== theme 是否为空：{not state['theme']} =====")
    print()
    
    from app.models.state import AgentState
    try:
        if state["theme"]:  # 已经有 theme 了，想跳过前面
            # 先把当前 state 写进 checkpoint（确保线程存在）
            agent_graph.update_state(
                config,
                AgentState(state),           # 你的完整 state
                as_node="wait_for_user"        # 或者 "wait_for_user"，只要是 reflect 的前一个节点
            )
            # 然后从 reflect 开始继续执行（不传入新 input）
            result = agent_graph.invoke(
                None,                        # ← 重要：None 表示「从当前 checkpoint 继续」
                config
            )
        else:
            # 正常从头开始
            result = agent_graph.invoke(AgentState(state), config)
    except Exception as e:
        print(f"调用失败: {e}")  # 这里换成FastAPI的异常返回
        return {"message": "抱歉，处理失败", "is_complete": False}

    # # 调用graph（自动回复状态，继续执行）
    # result = agent_graph.invoke(AgentState(state), config)

    # 保存状态
    conversation_state[thread_id] = result
    state = conversation_state[thread_id]

    print(f"===== 当前会话 state['theme']：{state['theme']} =====")


    # 返回回复
    assistant_message = result["messages"][-1]["content"]
    return {"message": assistant_message, "is_complete": result.get("is_complete", False)}
    
