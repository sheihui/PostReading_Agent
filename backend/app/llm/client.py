"""
LLM 客户端 - 基于 MiniMax-M2.5
"""

from langchain_community.chat_models import ChatTongyi
from app.config import DASHSCOPE_API_KEY
from typing import Optional, List, Dict

llm = ChatTongyi(
    model_name="MiniMax-M2.5",
    api_key=DASHSCOPE_API_KEY,
    temperature=0.7,
)

def call_llm(
        promtpt: str,
        system_prompt: Optional[str] = None,
        model_name: str = "MiniMax-M2.5",
        temperature: float = 0.7,
) -> str:
    """调用 LLM 模型"""
    if system_prompt:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": promtpt},
        ]
    else:
        messages = [
            {"role": "user", "content": promtpt},
        ]
    response = llm.invoke(messages)
    return response.content



def chat_with_history(
        promtpt: str,
        system_prompt: Optional[str] = None,
        model_name: str = "MiniMax-M2.5",
        temperature: float = 0.7,
) -> str:
    """调用 LLM 模型，带有历史记录"""
    if system_prompt:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": promtpt},
        ]
    else:
        messages = [
            {"role": "user", "content": promtpt},
        ]
    response = llm.invoke(messages)
    return response.content


