"""向量存储 - Chroma + Qwen Embedding"""
import os
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHROMA_CONF



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

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHROMA_CONF["chunk_size"],
            chunk_overlap=CHROMA_CONF["chunk_overlap"],
            separators=CHROMA_CONF["separators"],
            length_function=len,
        )
    
    def get_retriever(self, k=None):
        k = k or CHROMA_CONF["k"]
        return self.vector_store.as_retriever(search_kwargs={"k": k})


    def add_documents(self, documents: list):
        """添加文档到向量存储"""
        self.vector_store.add_documents(documents)

    def split_documents(self, documents: list):
        """将文档切分"""
        return self.splitter.split_documents(documents)
    