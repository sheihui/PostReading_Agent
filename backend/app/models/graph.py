from cmath import pi
from posthog import page
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

if __name__ == "__main__":
    pass
    # agent_graph.invoke({
    #     "user_id": "user123",
    #     "book_title": "思考致富",
    # })
    # print("hello")
    # this is a test block
    # =========================Test 1=========================
    # result1 = collect_info({
    #     "user_id": "user123",
    #     "book_title": "思考致富",
    # })
    # print(result1)
    # result1 = {'book_intro': '《思考致富》是作者最有代表性和最受欢迎的成功经典，成为无数人前行的灯塔和路标，整整影响了读者近70年。本21世纪修订版由著名哲学博士与演讲家亚瑟?R?培尔完成，在原版的基础上删掉了20世纪30年前后的轶闻，并增加了一些新的事例，包括比尔?盖茨、玛丽·凯、迈克尔·乔丹等。书中归纳阐述了获取财富的13大步骤。你所取得的一切成就，你所获得的一切财富，最初都源于一个想法！如果你已经为接受《思考致富》的秘诀做好了准备，那你就拥有了秘诀的一半，当别一半闪入你的脑海时，你便一眼就能识别出来。', 'perspective': [{'content': '- 欲望：强烈的欲望是实现一切目标的起点，只有拥有强烈的欲望，才能激发无限能量去追求想要的东西'}, {'content': '- 信念：想象成功并坚定地相信目标能够实现'}, {'content': '- 积极思考：每天有意识地用积极的思考灌溉心灵，为未来成功播种'}, {'content': '- 行动：行动是思想与现实的桥梁，将想法转化为实际成果'}], 'review': [{'content': '- 阅读这本书就像一次寻找成功之旅，在路途中我随着故事一起成长，和希尔挖掘成功的秘诀'}, {'content': '- 这本书不是教你投资或做生意的秘诀，而是整理了多位成功人士的价值观和心法'}, {'content': '- 书中提到成功人士或财富拥有者所散发的性魅力非常强烈，这在富一代或官一代身上会非常明显'}, {'content': '- 很多耳熟能详的知名人物也曾受到希尔的指引，诸如美国总统罗斯福等'}, {'content': '- 通过阅读这本书，我认识到成功不仅仅是外在的成就，更是一种由内而外散发的个人魅力和价值观念'}]}
    # =========================Test 2=========================
    # result2 = plan_themes({
    #     "user_id": "user123",
    #     "book_title": "思考致富",
    #     "book_intro": result1["book_intro"],
    #     "perspective": result1["perspective"],
    #     "review": result1["review"],
    # })
    # print(result2)
    # result2 = {'theme': [{'topic': "从'想法'到'财富'的转化路径", 'question': "你说'书中归纳阐述了获取财富的13大步骤'，那么你印象最深的步骤是哪个？这13步在你心中是如何串联成一条从'想法'到'成果'的行动链条的？"}, {'topic': '经典理论与新时代案例的碰撞', 'question': "你说'本21世纪修订版增加了比尔·盖茨、玛丽·凯、迈克尔·乔丹等新事例'，你觉得这些21世纪的新案例和希尔原来采访的经典案例（如罗斯福总统）相比，在成功逻辑上有什么异同？"}, {'topic': '成功的心法vs 投资的秘诀', 'question': "你提到'这本书不是教你投资或做生意的秘诀，而是整理了多位成功人士的价值观和心法'，那么你在实际生活中准备如何运用这些'心法'？有没有具体的应用场景？"}, {'topic': '由内而外的成功魅力', 'question': "你特别提到'成功不仅仅是外在的成就，更是一种由内而外散发的个人魅力'，这种'由内而外的魅力'在你看来具体指什么？你在自己的生活中有没有遇到过这样让你感受到这种魅力的人？"}, {'topic': '欲望、信念与行动的闭环', 'question': "你说'你所取得的一切成就最初都源于一个想法'，但光有想法显然不够。在你看来，欲望、信念、积极思考、行动这四个要素中，哪个对你来说挑战最大？你打算如何突破？"}], 'current_theme_idx': 0}
    # =========================Test 3=========================
    # print(type(result2["current_theme_idx"]))
    # print(result2["theme"][0].get("topic"))
    # result3 = execute_theme({
    #     "user_id": "user123",
    #     "book_title": "思考致富",
    #     "theme": result2["theme"],
    #     "current_theme_idx": result2["current_theme_idx"],
    # })
    # print(result3)
    # result3 = {'messages': [{'role': 'assistant', 'content': "你说'书中归纳阐述了获取财富的13大步骤'，那么你印象最深的步骤是哪个？这13步在你心中是如何串联成一条从'想法'到'成果'的行动链条的？"}], 'insight': [], 'current_theme_idx': 0}
    # ==============Test 4=========================
    # result4 = reflect({
    #     "user_id": "user123",
    #     "book_title": "思考致富",
    #     "theme": result2["theme"],
    #     "current_theme_idx": result2["current_theme_idx"],
    #     "messages": result3["messages"],
    #     "insight": result3["insight"],
    # })
    # print(result4)
    # result4 = {'current_theme_idx': 0}
    # =========================Test 5=========================
    # result5 = generate_notes({
    #     "user_id": "user123",
    #     "book_title": "思考致富",
    #     "theme": result2["theme"],
    #     "current_theme_idx": result4["current_theme_idx"],
    #     "messages": result3["messages"],
    #     "insight": result3["insight"],
    # })
    # print(result5)