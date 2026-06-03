from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from app.models.state import AgentState
from app.models.nodes import (
    collect_info,
    plan_themes,
    execute_theme,
    reflect,
    generate_notes,
    wait_for_user,
)

graph = StateGraph(AgentState)

graph.add_node("collect_info", collect_info)
graph.add_node("plan_themes", plan_themes)
graph.add_node("execute_theme", execute_theme)
graph.add_node("reflect", reflect)
graph.add_node("generate_notes", generate_notes)
graph.add_node("wait_for_user", wait_for_user)

graph.add_edge("__start__", "collect_info")
graph.add_edge("collect_info", "plan_themes")
graph.add_edge("plan_themes", "execute_theme")
graph.add_edge("execute_theme", END)
graph.add_edge("wait_for_user", "reflect")


def should_continue(state: AgentState) -> str:
    return state.get("next", "execute_theme")


graph.add_conditional_edges(
    "reflect",
    should_continue,
    {
        "execute_theme": "execute_theme",
        "plan_themes": "plan_themes",
        "generate_notes": "generate_notes",
    },
)

graph.add_edge("generate_notes", END)

agent_graph = graph.compile(checkpointer=MemorySaver())