# Long-Term Memory (Level 3)

跨书用户 insight 存储与语义检索。

## Delta

全新能力。当前系统无持久化跨会话记忆。

## 数据模型

### UserInsight

```json
{
  "id": "str",
  "user_id": "str",
  "book_title": "str",
  "dimension_category": "resonance | critique | connection | action | emotion",
  "dimension_label": "str",
  "content": "用户的核心思考",
  "composite_score": 2.0,
  "scores": {"depth": 2, "specificity": 2, "personalization": 3, "evidence": 1},
  "timestamp": "2026-07-04T10:30:00Z",
  "embedding": "[float,...]"
}
```

### UserProfile

```json
{
  "user_id": "str",
  "recurring_themes": ["决策", "习惯"],
  "thinking_style": "批判型 | 共鸣型 | 实践型 | 均衡型",
  "sharing_preference": "倾向工作经历 | 倾向抽象思辨 | 均衡",
  "total_books": 5,
  "total_insights": 23,
  "last_updated": "ISO8601"
}
```

## 存储

| 数据 | 存储 |
|------|------|
| UserInsight | ChromaDB `user_insights`，embedding 复用 DashScope text-embedding-v4 |
| UserProfile | `data/profiles/{user_id}.json` |

## 接口

### 写入

`store_insight(insight) → str`
- 触发：Reflect sufficient=true
- 容错：失败不阻塞流程

### 检索

`retrieve_relevant_insights(query, user_id, k=5) → list[UserInsight]`
- 触发：Plan 阶段
- 范围：限定 user_id，排除当前书籍，相似度 > 0.5

### 跨书关联

`retrieve_cross_book_connections(book, dimension_label, user_id) → list[CrossBookConnection]`
- 触发：Generate Notes 阶段

### 画像

`update_profile(user_id) → UserProfile`
- 触发：每次 Generate Notes 完成

## 嵌入点

```
Plan:           检索 → cross_book_hooks
Reflect:        写入（sufficient 时）
Generate Notes: 检索 → 跨书关联章节
Generate Notes: 完成 → 更新画像
```

## 新增文件

```
backend/app/memory/
├── __init__.py
├── models.py
├── insight_store.py
└── profile.py
```
