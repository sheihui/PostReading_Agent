import streamlit as st
import requests

# API 地址
API_URL = "http://localhost:8000/api/chat"

st.set_page_config(page_title="PostReading Agent", page_icon="📚")

st.title("📚 PostReading Agent")
st.write("和 AI 一起深度聊聊你读过的书")

# 初始化 session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "book_title" not in st.session_state:
    st.session_state.book_title = ""

# 侧边栏：设置
with st.sidebar:
    st.header("📖 书籍信息")
    user_id = st.text_input("用户 ID", value=st.session_state.user_id)
    book_title = st.text_input("书名", value=st.session_state.book_title)
    
    if st.button("🚀 开始新会话"):
        # 清空对话历史
        st.session_state.messages = []
        st.session_state.user_id = user_id
        st.session_state.book_title = book_title
        st.rerun()

# 显示对话历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入
if user_id and book_title:
    if prompt := st.chat_input("写下你的想法..."):
        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 调用 API
        with st.spinner("AI 正在思考..."):
            try:
                response = requests.post(
                    API_URL,
                    json={
                        "user_id": user_id,
                        "book_title": book_title,
                        "message": prompt
                    }
                )
                result = response.json()
                
                # 添加 AI 消息
                ai_message = result.get("message", "抱歉，出错了...")
                st.session_state.messages.append({"role": "assistant", "content": ai_message})
                
                with st.chat_message("assistant"):
                    st.markdown(ai_message)
                    
            except Exception as e:
                st.error(f"调用失败: {e}")
else:
    st.info("👈 请在侧边栏填写用户 ID 和书名，然后开始聊天")

    