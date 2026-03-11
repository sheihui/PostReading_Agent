from langchain_core.tools import tool
from tavily import TavilyClient
import os

tavily_client = api_key=os.getenv("TAVILY_API_KEY")

@tool
def search_books_perspective(book_title: str) -> str:
    """搜索书籍核心观点"""
    client = TavilyClient(api_key=tavily_client)
    query = f"{book_title} 核心观点"
    response = client.search(query, max_results=3)
    return "\n".join([r["content"] for r in response["results"]])


@tool
def search_books_review(book_title: str) -> str:
    """搜索书籍评论和读后感"""
    client = TavilyClient(api_key=tavily_client)
    query = f"{book_title} 评论 读后感"
    response = client.search(query, max_results=3)
    return "\n".join([r["content"] for r in response["results"]])


@tool
def search_concept(query: str) -> str:
    """搜索专业概念，agent不懂时用"""
    client = TavilyClient(api_key=tavily_client)
    response = client.search(query, max_results=3)
    return "\n".join([r["content"] for r in response["results"]])



