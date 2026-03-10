from langchain_core.tools import tool
from app.storage.vector_store import VectorStore
from app.config import CHROMA_CONF




@tool
def rag_retrieve(query: str, collection: str="books") -> str:
    """
    RAG 检索
    
    Args:
        query: 查询内容
        collection: collection 名称(默认 "books")
        top_k: 返回数量(默认 4)
    """
    vector_store = VectorStore(collection)
    retriever = vector_store.get_retriever()
    documents = retriever.invoke(query)
    return documents


@tool
def rag_add_documents(collection: str="books", filepath: str=None):
    """
    RAG 添加文档
    
    Args:
        collection: collection 名称(默认 "books")
        filepath: JSON 文件路径
    """
    vector_store = VectorStore(collection)
    documents = vector_store.load_parse_documents(filepath)
    split_docs = vector_store.split_documents(documents)
    vector_store.add_documents(split_docs)
    return f"已添加 {len(split_docs)} 条内容到 {collection}"
