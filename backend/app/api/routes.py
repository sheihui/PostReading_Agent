from fastapi import APIRouter
from pydantic import BaseModel
from app.models.graph import graph

router = APIRouter()

class AgentRequest(BaseModel):
    user_id: str
    book_id: str
    book_title: str


@router.post("/agent/run")
async def run_agent(request: AgentRequest):
    initial_state = {
        "user_id": request.user_id,
        "book_id": request.book_id,
        "book_title": request.book_title,
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
    
    result = graph.invoke(initial_state)
    
    # return {"status": "ok", "final_note": result.get("final_note")}
    return {"status": "test ok"}
