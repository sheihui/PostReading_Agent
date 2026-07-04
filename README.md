# PostReading Agent

<div align="center">

[![LangGraph](https://img.shields.io/badge/LangGraph-Agent-FF6F00?logo=langgraph&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek_V4_Flash-4B8BF5)](https://www.deepseek.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Plan--Execute_+_Reflect-b8754a)](https://arxiv.org/abs/2303.17651)

</div>

读完一本书，AI 通过引导式对话帮你梳理思考，生成一份**真正属于你**的结构化读书笔记。

PostReading Agent 采用 **Plan-and-Execute + Reflection** 架构，连接微信读书数据，以结构化笔记为目标，系统性地采集你的个人思考。

| 登录页 | 对话界面 |
| ------ | -------- |
| ![登录页](frontend/image/login%20page.png) | ![对话界面](frontend/image/chat%20page.png) |

## 核心特性

- **知识采集清单** — LLM 分析书籍内容，自动规划采集维度（共鸣、批判、连接、行动、情感），而非随意聊天
- **引导式对话** — 围绕每个维度自然引导你表达思考，心中有清单、口中无清单
- **Reflection 质量把关** — 笔记生成后，AI 对照采集清单自我评估，不达标自动补充
- **Human-in-the-loop** — 笔记交到你手上审核，不满意可标注反馈、继续迭代
- **Level 3 长期记忆** — 跨书记住你的思考，三本书后能发现你的思维模式和阅读偏好
- **内置评测框架** — 每次运行自动评分（笔记质量 / Reflect 准确性 / 覆盖度），可量化迭代
- **微信读书数据接入** — 拉取划线、想法、热门标注和书评，笔记引用原文佐证

## 架构

Agent 采用真正的 **Plan-and-Execute + Reflection** 三阶段：

- **Plan**：分析书籍内容 → 生成知识采集清单（5 个类别 × 1-2 个维度）
- **Execute**：围绕当前维度引导对话 → 维度路由（纯规则判断采集充分性）
- **Reflect**：笔记生成后对照清单评估质量 → pass / revise / replan
- **Consolidate**：跨维度综合检查矛盾与缺口
- **Review**：用户审核笔记，支持反馈迭代

```
                  ┌─────────────┐
                  │ Collect Info │  微信读书数据
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
             ┌────│    Plan     │  生成采集清单 + 长期记忆注入
             │    └──────┬──────┘
             │           │
             │    ┌──────▼──────┐
             │    │   Execute   │  按维度引导对话（每轮一句）
             │    └──────┬──────┘
             │           │
             │    ┌──────▼──────┐
             │    │   路由判定   │  够了？→ 下一维度/Consolidate
             │    │  (纯规则)   │  不够？→ 换角度继续
             │    └──┬───┬───┬──┘
             │       │   │   │
             │  继续 │   │够 │全完成
             │       │   │   │
             │       ▼   ▼   ▼
             │   (循环)  │  ┌──────────────┐
             │           │  │ Consolidate  │  跨维度矛盾/缺口检测
             │           │  └──────┬───────┘
             │           │         │
             │           │  ┌──────▼───────┐
             │           │  │Generate Notes│  结构化 Markdown
             │           │  └──────┬───────┘
             │           │         │
             │           │  ┌──────▼───────┐
             │           │  │   Reflect    │  对照清单评估笔记
             │           │  └──┬───┬───┬───┘
             │           │     │   │   │
             │    revise │◄────┘   │   └── replan → Plan
             │           │    pass│
             │           │        ▼
             │           │  ┌──────────┐
             │           │  │  Review  │  Human-in-the-loop
             │           │  └────┬─────┘
             │           │       │
             │ 用户反馈   │◄──────┘
             │           │
             └───────────┘
```

## 目录结构

```
PostReading_Agent/
├── frontend/
│   └── index.html              # 单文件前端（登录 + 聊天 UI）
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── config.py           # 全局配置
│   │   ├── api/
│   │   │   └── routes.py       # POST /api/chat
│   │   ├── models/
│   │   │   ├── state.py        # AgentState 定义
│   │   │   ├── nodes.py        # 8 个节点（Plan, Execute, Route, Consolidate, Notes, Reflect, Review, Wait）
│   │   │   ├── graph.py        # StateGraph 构建 + 条件边
│   │   │   └── reflect_decision.py  # [deprecated] JSON 解析工具
│   │   ├── memory/             # ★ Level 3 长期记忆
│   │   │   ├── models.py       # UserInsight, UserProfile
│   │   │   ├── insight_store.py # ChromaDB CRUD + 语义检索
│   │   │   └── profile.py      # 用户画像计算
│   │   ├── evaluation/         # ★ 内置评测框架
│   │   │   └── scorer.py       # 三层评分（笔记质量 / Reflect准确性 / 覆盖度）
│   │   ├── llm/
│   │   │   └── client.py       # LLM 客户端（DashScope → DeepSeek）
│   │   ├── storage/
│   │   │   └── vector_store.py # ChromaDB 向量存储
│   │   ├── tools/
│   │   │   └── rag.py          # RAG 检索与文档摄入
│   │   └── utils/
│   │       ├── context.py      # 上下文压缩与主题归档
│   │       └── get_book_to_json.py  # Weread Gateway
│   ├── data/
│   │   ├── books/              # 书籍缓存 (JSON)
│   │   ├── notes/              # 生成笔记 (.md)
│   │   ├── chroma/             # 向量数据
│   │   ├── eval/               # 评测日志
│   │   └── profiles/           # 用户画像
│   ├── requirement.txt
│   └── .env
├── openspec/
│   └── specs/                  # 系统规格（6 个 domain）
└── README.md
```

## 快速开始

### 1. 环境准备

Python 3.10+，克隆项目：

```bash
git clone https://github.com/sheihui/PostReading_Agent.git
cd PostReading_Agent/backend
pip install -r requirement.txt
```

### 2. 获取 API Key

- **百炼 API Key**：前往 [阿里云百炼控制台](https://bailian.console.aliyun.com/) 获取 DashScope API Key
- **微信读书 Key**：访问 [weread.qq.com/r/weread-skills](https://weread.qq.com/r/weread-skills) 扫码获取

两个 Key 在打开前端页面时填入即可，无需写入 `.env`。

### 3. 启动后端

```bash
cd backend
export PYTHONPATH=$(pwd):$PYTHONPATH
uvicorn app.main:app --reload --port 8000
```

### 4. 打开前端

直接用浏览器打开 `frontend/index.html`：

```bash
open frontend/index.html
```

在登录页填入两个 Key，点击「进入 PostReading」即可使用。

## API

后端启动后访问 `http://localhost:8000/docs` 查看 Swagger 文档。

**POST /api/chat**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user",
    "book_title": "思考，快与慢",
    "message": "你好",
    "api_key": "wrk-xxxxx",
    "llm_api_key": "sk-xxxxx"
  }'
```

响应：

```json
{
  "message": "嗨，欢迎来到读书会。今天我们一起聊聊《思考，快与慢》吧。",
  "new_messages": [
    "嗨，欢迎来到读书会。今天我们一起聊聊《思考，快与慢》吧。",
    "我们先聊聊「系统1和系统2」——你觉得日常决策中，哪个系统在主导？"
  ],
  "is_complete": false,
  "current_dimension": {
    "id": "d_001",
    "category": "resonance",
    "label": "对'系统1与系统2'框架的共鸣",
    "goal": "了解用户是否认同作者关于双系统的核心论断"
  },
  "collection_progress": { "total": 5, "completed": 0 },
  "topic_summaries": {},
  "note_file": null
}
```

**GET /api/notes/{book_title}** — 下载生成的读书笔记文件（Markdown）。

## 技术栈

- **Agent 框架**：LangGraph（Plan-and-Execute + Reflection）
- **后端**：FastAPI
- **前端**：原生 HTML/CSS/JS
- **向量数据库**：ChromaDB + DashScope text-embedding-v4
- **LLM**：DeepSeek V4 Flash via 阿里云百炼 (DashScope)
- **数据源**：微信读书 Agent Gateway

## License

MIT
