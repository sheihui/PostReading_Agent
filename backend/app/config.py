import os 
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
WEREAD_COOKIE = os.getenv("WEREAD_COOKIE")


# Chroma 配置
CHROMA_CONF={
    "collection_name": "books",
    "chunk_size": 1000,
    "chunk_overlap": 100,
    "separators": ["\n\n", "\n", ",", "?", ".", "！", "？", "。", " ", ""],
    "k": 3,
}


books_file_path = "data/books"
notes_file_path = "data/notes"
