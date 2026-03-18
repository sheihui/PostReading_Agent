  # 📚 PostReading Agent (AI 读书助手)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)[![Framework: FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)[![Frontend: Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)

> **PostReading Agent** 是一个专为“读书后讨论与笔记生成”设计的 AI 智能体。它基于 **LangGraph** 框架，采用 `Plan-and-Execute + Reflection` 双范式，通过引导式的多轮对话，帮助你深度消化书籍内容，并自动沉淀结构化的读书笔记。

## ✨ 核心特性

- **🧠 智能书籍解析与 RAG**：自动结合用户阅读痕迹（如微信读书的划线、想法）、书籍核心观点与高赞书评，构建专属知识库。
- **🗺️ 主题式启发讨论**：根据书籍内容动态规划讨论主题（Plan），循序渐进地引导用户进行深度思考。
- **💬 沉浸式多轮对话**：执行讨论（Execute）并具备反思能力（Reflection），AI 会根据你的回答决定是深入当前话题，还是推进到下一主题。
- **📝 全自动笔记生成**：讨论结束后，自动提炼多轮对话中的思想火花，生成结构化、富有洞察的专属读书笔记。

## 🏗️ 技术架构

本项目采用前后端分离架构，核心逻辑由 LangGraph 驱动：

```mermaid
graph TD
    subgraph 初始化阶段
        A[用户: 开启读书讨论] --> B[collect_info: 收集/检索书籍信息]
        B --> C[plan_themes: 规划讨论主题]
    end

    subgraph 对话与反思循环
        C --> D[execute_theme: 执行当前主题探讨]
        D --> E[reflect: 反思用户输入]
        E -->|需深入/继续当前主题| D
        E -->|已充分/进入下一主题| D
    end

    subgraph 总结阶段
        E -->|所有主题讨论完毕| F[generate_notes: 提炼并生成读书笔记]
    end

    B -.->|RAG 检索| B1[(向量数据库)]
    C -.-> C1((LLM: 提纲规划))
    D -.-> D1((LLM: 启发式问答))
    E -.-> E1((LLM: 意图识别与状态流转))
    F -.-> F1((LLM: 总结归纳))
````

## 📁 项目目录结构

Plaintext

```
PostReading_Agent/
├── backend/                 # 核心后端服务 (FastAPI)
│   ├── app/
│   │   ├── api/             # RESTful API 路由
│   │   ├── llm/             # LLM 模型接口封装
│   │   ├── models/          # LangGraph 状态图与节点定义
│   │   ├── storage/         # 向量数据库集成 (Chroma)
│   │   ├── tools/           # 外部工具 (RAG 检索、网络搜索等)
│   │   └── utils/           # 辅助工具 (如微信读书 API 适配)
│   └── data/                # 本地数据存储
│       ├── books/           # 书籍基础元数据 (JSON)
│       ├── notes/           # 最终生成的读书笔记
│       └── vector_db/       # Chroma 向量数据持久化目录
└── frontend/                # 交互前端 (Streamlit)
    └── streamlit_app.py     # 前端主入口
```

## 🚀 快速开始

## 1. 环境准备

确保你已安装 Python 3.8+。克隆本项目到本地：

Bash

```
git clone [https://github.com/sheihui/PostReading_Agent.git](https://github.com/sheihui/PostReading_Agent.git)
cd PostReading_Agent
```

## 2. 配置环境变量

在 `backend/` 目录下创建 `.env` 文件，并填入你的大模型 API 密钥（目前默认支持基于 DashScope 或兼容接口的模型）：

代码段

```
# LLM 鉴权配置
DASHSCOPE_API_KEY=your_api_key_here
# 可选：其他 API Keys 或配置
```

## 3. 启动后端服务

Bash

```
cd backend
pip install -r requirements.txt
# 将当前目录加入环境变量以确保包导入正常
export PYTHONPATH=$(pwd):$PYTHONPATH
# 启动 FastAPI 服务
uvicorn app.main:app --reload --port 8000
```

## 4. 启动前端页面

打开一个新的终端窗口：

Bash

```
cd frontend
pip install -r requirements.txt # (如果有单独的前端依赖)
streamlit run streamlit_app.py
```

访问 `http://localhost:8501`，在侧边栏输入你的用户 ID 和书名，即可开始与 AI 的思想碰撞！

## 接口文档 (API Reference)

后端启动后，你可以访问 `http://localhost:8000/docs` 查看完整的 Swagger 交互式 API 文档。

**核心接口示例：** `POST /api/chat` - 发送消息并推进讨论状态

Bash

```
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "book_title": "思考，快与慢",
    "message": "我准备好开始聊这本书了"
  }'
```

## 🛠️ 技术栈

- **Agent 框架**: [LangGraph](https://python.langchain.com/docs/langgraph)
    
- **后端服务**: [FastAPI](https://fastapi.tiangolo.com/)
    
- **前端交互**: [Streamlit](https://streamlit.io/)
    
- **向量数据库**: [ChromaDB](https://www.trychroma.com/)
    
- **大语言模型**: DashScope (如 MiniMax-M2.5 或其他兼容模型)
    

    

## 📄 许可证

本项目基于 [MIT License](https://www-d-google-d-com-s-gmn.v.tuangouai.com/search?q=LICENSE) 开源。