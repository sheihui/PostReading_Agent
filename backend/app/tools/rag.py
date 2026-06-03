from langchain_core.tools import tool
from langchain_core.documents import Document
from app.storage.vector_store import VectorStore
from app.config import books_file_path
import json, os


@tool
def rag_retrieve(query: str, collection: str = "books", k: int = 4) -> str:
    """
    RAG 检索
    Args:
        query: 查询内容
        collection: collection 名称(默认 "books")
        k: 返回数量(默认 4)
    """
    vector_store = VectorStore(collection)
    retriever = vector_store.get_retriever(k=k)
    documents = retriever.invoke(query)
    return documents


@tool
def rag_add_book_documents(title: str, collection: str = "books"):
    """
    从网关缓存 JSON 提取划线和想法，嵌入入库
    Args:
        title: 书籍标题
        collection: collection 名称(默认 "books")
    """
    filepath = f"{books_file_path}/{title}.json"
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    vector_store = VectorStore(collection)
    book_id = data["info"]["bookId"]
    documents = []

    for h in data.get("highlights", {}).get("updated", []):
        documents.append(Document(
            page_content=h["markText"],
            metadata={"book_id": book_id, "type": "highlight"},
        ))

    for r in data.get("reviews", {}).get("reviews", []):
        review = r["review"]
        abstract = review.get("abstract", "")
        content = review.get("content", "")
        parts = []
        if abstract:
            parts.append(f"原文: {abstract}")
        if content:
            parts.append(f"想法: {content}")
        if parts:
            documents.append(Document(
                page_content="\n".join(parts),
                metadata={"book_id": book_id, "type": "review"},
            ))

    if not documents:
        return f"未找到划线和想法: {title}"

    split_docs = vector_store.split_documents(documents)
    vector_store.add_documents(split_docs)
    return f"已添加 {len(split_docs)} 条内容到 {collection}"
