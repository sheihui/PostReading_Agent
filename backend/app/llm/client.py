from langchain_community.chat_models import ChatTongyi
from app.config import DASHSCOPE_API_KEY

_default_llm = ChatTongyi(
    model_name="deepseek-v4-flash",
    api_key=DASHSCOPE_API_KEY,
    temperature=0.7,
)
_llm_cache = {}

def _get_llm(api_key: str = ""):
    if not api_key:
        return _default_llm
    if api_key not in _llm_cache:
        _llm_cache[api_key] = ChatTongyi(
            model_name="deepseek-v4-flash",
            api_key=api_key,
            temperature=0.7,
        )
    return _llm_cache[api_key]

def call_llm(prompt: str, system_prompt: str = "", llm_api_key: str = "") -> str:
    llm = _get_llm(llm_api_key)
    if system_prompt:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
    else:
        messages = [
            {"role": "user", "content": prompt},
        ]
    response = llm.invoke(messages)
    return response.content
