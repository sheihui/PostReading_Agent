# from asyncio import graph
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

    # 调用graph（自动回复状态，继续执行）
    from app.models.state import AgentState
    result = agent_graph.invoke(AgentState(state), config)

    # 保存状态
    conversation_state[thread_id] = result

    # 返回回复
    assistant_message = result["messages"][-1]["content"]
    return {"message": assistant_message, "is_complete": result.get("is_complete", False)}
    
