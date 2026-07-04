from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from app.models.state import AgentState
from app.models.nodes import (
    collect_info,
    plan,
    execute,
    route_dimension,
    consolidate,
    generate_notes,
    reflect,
    review,
    wait_for_user,
    route_after_consolidate,
    route_after_reflect,
    route_after_review,
)


def _route_dimension_edges(state: AgentState) -> str:
    """route_dimension 的条件边映射。"""
    next_node = state.get("next", "__end__")
    if next_node == "next_dimension":
        return "execute"      # 切维度，execute 生成过渡语
    elif next_node == "consolidate":
        return "consolidate"
    else:  # continue_dimension 或默认
        return "__end__"      # 等待用户回复


graph = StateGraph(AgentState)

# ===== 节点 =====
graph.add_node("collect_info", collect_info)
graph.add_node("plan", plan)
graph.add_node("execute", execute)
graph.add_node("route_dimension", route_dimension)
graph.add_node("consolidate", consolidate)
graph.add_node("generate_notes", generate_notes)
graph.add_node("reflect", reflect)
graph.add_node("review", review)
graph.add_node("wait_for_user", wait_for_user)

# ===== 入口 =====
graph.add_edge("__start__", "collect_info")

# ===== 首次流程: collect_info → plan → execute → route_dimension =====
graph.add_edge("collect_info", "plan")
graph.add_edge("plan", "execute")
graph.add_edge("execute", "route_dimension")

# ===== route_dimension 之后 =====
graph.add_conditional_edges(
    "route_dimension",
    _route_dimension_edges,
    {
        "execute": "execute",
        "consolidate": "consolidate",
        "__end__": END,
    },
)

# ===== 后续轮次: wait_for_user → execute → route_dimension =====
graph.add_edge("wait_for_user", "execute")

# ===== Consolidate 之后 =====
graph.add_conditional_edges(
    "consolidate",
    route_after_consolidate,
    {
        "generate_notes": "generate_notes",
        "execute": "execute",
        "plan": "plan",
    },
)

# Generate Notes → Reflect
graph.add_edge("generate_notes", "reflect")

# ===== Reflect 之后 =====
graph.add_conditional_edges(
    "reflect",
    route_after_reflect,
    {
        "review": "review",
        "execute": "execute",
        "plan": "plan",
    },
)

# ===== Review 之后 =====
graph.add_conditional_edges(
    "review",
    route_after_review,
    {
        "approved": END,
        "revise": "execute",
    },
)


agent_graph = graph.compile(checkpointer=MemorySaver())
