# PostReading Agent 📚

一个 AI 读书助手，帮助你深度阅读和思考书籍内容。

## 功能特性

- **智能书籍解析**：自动获取用户阅读痕迹（微读的划线、想法）以及核心观点、高赞书评
- **主题式讨论**：根据书籍内容规划讨论主题，引导深度思考
- **多轮对话**：与 AI 进行持续对话，逐步深化理解
- **笔记生成**：自动整理对话内容，生成结构化读书笔记

## 技术架构

```
PostReading_Agent/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── llm/           # LLM 客户端
│   │   ├── models/        # 状态与节点定义
│   │   ├── storage/       # 向量存储
│   │   ├── tools/         # 工具函数（RAG、搜索）
│   │   └── utils/         # 工具（微信读书 API）
│   └── data/              # 数据存储
│       ├── books/         # 书籍 JSON 文件
│       ├── notes/         # 生成的笔记
│       └── vector_db/     # 向量数据库
└── frontend/              # 前端（Streamlit）
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端

```bash
cd backend
export PYTHONPATH=$(pwd):$PYTHONPATH
uvicorn app.main:app --reload --port 8000
```

### 3. 启动前端

```bash
# 新终端
cd frontend
streamlit run streamlit_app.py
```

### 4. 使用

1. 打开浏览器 `http://localhost:8501`
2. 侧边栏填写用户 ID 和书名
3. 开始与 AI 讨论书籍

## API 接口

### POST /api/chat

与 AI 进行对话

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "book_title": "思考，快与慢",
    "message": "我想开始聊这本书"
  }'
```

响应：
```json
{
  "message": "你好！我想和你聊聊《思考，快与慢》..."
}
```

## 核心模块说明

### 1. 状态管理 (app/models/state.py)

```python
AgentState:
  - user_id, book_id, book_title      # 基础信息
  - book_intro                        # 书籍简介
  - perspective                       # 核心观点
  - review                            # 读者评价
  - theme                             # 讨论主题
  - messages                          # 对话历史
  - insight                           # 用户的洞察
  - is_complete                       # 是否完成
  - final_note                        # 最终笔记
```

### 2. 节点流程 (app/models/nodes.py)

- **collect_info**：获取书籍信息，初始化 RAG
- **plan_themes**：规划讨论主题
- **execute_theme**：执行主题讨论
- **reflect**：反思，决定是否继续
- **generate_notes**：生成读书笔记

### 3. 工具 (app/tools/)

- **rag.py**：向量检索增强（RAG）
- **search.py**：网络搜索（获取书籍观点）

## 环境变量

在 `backend/` 目录下创建 `.env` 文件：

```bash
# LLM 配置
DASHSCOPE_API_KEY=your_api_key

# 其他配置...
```

## 技术栈

- **后端**：FastAPI + LangGraph
- **LLM**：DashScope (MiniMax-M2.5)
- **向量库**：Chroma
- **前端**：Streamlit
- **数据**：JSON 文件存储

## 版本

- **v1.0.0**：基础功能版本，支持多轮对话和笔记生成

## 未来计划

- [ ] 用户认证
- [ ] 对话历史持久化
- [ ] Flutter 前端
- [ ] 多书籍管理
- [ ] 分享功能

## License

MIT