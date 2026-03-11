from langchain_core import documents
"""
向量存储 - Chroma + Qwen Embedding
"""
import os
import json
# from langchain_community.vectorstores import Chroma
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from backend.app.config import CHROMA_CONF



# 初始化 DashScopeEmbeddings
embedding_model = DashScopeEmbeddings(
    model="text-embedding-v4",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
)


class VectorStore:
    def __init__(self, collection: str="books"):
        self.vector_store = Chroma(
            collection_name=collection,
            embedding_function=embedding_model,
            persist_directory="./data/chroma"
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=CHROMA_CONF["chunk_size"],
            chunk_overlap=CHROMA_CONF["chunk_overlap"],
            separators=CHROMA_CONF["separators"],
            length_function=len,
        )
    
    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": CHROMA_CONF["k"]})


    def add_documents(self, documents: list):
        """添加文档到向量存储"""
        self.vector_store.add_documents(documents)


    def load_parse_documents(self, filepath: str) -> list[Document]:
        """
        加载并解析 JSON 文件为 Document 对象
        document = Document(
            page_content="Hello, world!", metadata={"source": "https://example.com"}
        )
        metadata{
            "book_id": str,
            "title": str,
            "type": ["intro", "mark_text", "review"],
            "chapter_uid": int,
            "chapter_title": str
        }

        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        documents = []
        book_id = data.get("book_info", {}).get("bookId", "")
        title = data.get("book_info", {}).get("title", "")
        chapters = data.get("chapters", [])
        
        intro = Document(
            page_content=data.get("book_info", {}).get("intro", ""),
            metadata={
                "book_id": book_id,
                "title": title,
                "type": "intro",
                "chapter_uid": 0,
                "chapter_title": "Introduction"
            }
        )
        documents.append(intro)


        for highlights in data.get("highlights", []):
            mark_text = Document(
                page_content=highlights.get("mark_text", ""),
                metadata={
                    "book_id": book_id,
                    "title": title,
                    "type": "mark_text",
                    "chapter_uid": highlights.get("chapteruid", -1),
                    "chapter_title": chapters[highlights.get("chapteruid", -1) - 1]["title"]
                }
            )
            documents.append(mark_text)
        
        for review in data.get("reviews", []):
            review_text = Document(
                page_content=review.get("content", ""),
                metadata={
                    "book_id": book_id,
                    "title": title,
                    "type": "review",
                    "chapter_uid": review.get("chapter_uid", -1),
                    "chapter_title": review.get("chapter_title", "")
                }
            )
            documents.append(review_text)
        
        return documents

    
    def split_documents(self, documents: list):
        """将文档切分"""
        return self.spliter.split_documents(documents)
    