from langgraph.graph import StateGraph, END
from app.models.state import AgentState
from app.models.nodes import (
    collect_info,
    plan_themes,
    execute_theme,
    reflect,
    generate_notes,
)

graph = StateGraph(AgentState)


# 添加节点
graph.add_node("collect_info", collect_info)
graph.add_node("plan_themes", plan_themes)
graph.add_node("execute_theme", execute_theme)
graph.add_node("reflect", reflect)
graph.add_node("generate_notes", generate_notes)


# 添加边
graph.add_edge("__start__", "collect_info")
graph.add_edge("collect_info", "plan_themes")
graph.add_edge("plan_themes", "execute_theme")




# 条件边
def should_continue(state: AgentState) -> str:
    if state.get("is_complete", False):
        return "generate_notes"
    return "execute_theme"

# 条件边：reflect → 回到 execute_theme 或 generate_notes
graph.add_conditional_edges(
    "reflect",
    should_continue,
    {
        "execute_theme": "execute_theme",
        "generate_notes": "generate_notes",
    },
)

graph.add_edge("generate_notes", END)


agent_graph = graph.compile()

