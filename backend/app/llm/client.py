from langchain_community.chat_models import ChatTongyi
from app.config import DASHSCOPE_API_KEY

llm = ChatTongyi(
    model_name="MiniMax-M2.5",
    api_key=DASHSCOPE_API_KEY,
    temperature=0.7,
)
