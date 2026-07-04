# Knowledge Collection

Plan + Execute + 维度路由。

## Plan

### 职责

分析书籍 + 长期记忆 → 生成知识采集清单。

### 输入

| 字段 | 来源 |
|------|------|
| `book_intro` | Collect Info |
| `perspective` | Collect Info |
| `review` | Collect Info |
| `cross_book_insights` | 长期记忆语义检索 |

### 输出

```json
{
  "dimensions": [{
    "id": "d_001",
    "category": "resonance | critique | connection | action | emotion",
    "label": "简短标题",
    "goal": "该维度要采集什么 — 具体到本书内容",
    "priority": "high | normal",
    "cross_book_hook": "跨书关联提示 | null",
    "suggested_angles": ["角度1", "角度2"]
  }]
}
```

### Category

| Category | 采集目标 | 笔记章节 |
|----------|---------|---------|
| `resonance` | 认同的观点及原因 | 3.1 |
| `critique` | 不认同或存疑的观点 | 3.2 |
| `connection` | 与个人经历/其他书的关联 | 3.3 |
| `action` | 打算做出的改变 | 3.4 |
| `emotion` | 情感触动 | 3.5 |

### 规则

1. 每个 category 至少 1 个维度，总数 1-8 个
2. 维度具体到本书内容
3. priority=high 的维度必须完成
4. 有长期记忆时，cross_book_hook 引用具体历史 insight
5. 按 priority 排序

### 长期记忆集成

Plan 开始时语义检索历史 insight → 嵌入 cross_book_hook。

### 可被触发 replan

Reflect 判定整体不行，或 Consolidate 发现缺口/新发现 → 回 Plan。

## Execute

### 职责

围绕当前维度自然引导用户。**每次一轮对话。**

### 引导策略

从 suggested_angles 中选未用过的角度（不重复）：
1. 从书籍内容切入
2. 从用户划线切入
3. 从跨书关联切入
4. 从个人经历切入

### 维度追踪

每轮记录：turns, angles_used, user_stance, has_personal_example, has_evidence_quote, raw_insights。

### 原则

心中有清单，口中无清单。用户不感觉被审问。

## 维度路由（条件边，非 LLM）

```
Execute 后:

  用户发 finish 信号？ → Collect Info（换书）

  当前维度:
    turns ≥ 15？          → 标记 insufficient → 下一维度或 Consolidate
    用户本轮回应有实质内容？ → 够了 → 下一维度或 Consolidate
    用户本轮回应浅？       → turns < 3？→ Execute（换角度追问）
                           → turns ≥ 3？→ 标记 insufficient → 下一维度

  还有维度？ → Execute（dimension_idx++）
  全完成？   → Consolidate
```

**这是纯规则，不调用 LLM。**
