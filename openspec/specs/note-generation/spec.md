# Note Generation & Review

Generate Notes + Review 节点：生成结构化笔记，支持用户审核迭代。

## Generate Notes

### 职责

整合所有采集维度 + 跨书关联 → 结构化 Markdown 笔记。

### 输入

| 字段 | 来源 |
|------|------|
| `collection_plan` | Plan |
| `collected_insights` | Execute + Reflect |
| `dimension_sufficiency` | Reflect |
| `topic_summaries` | Reflect 归档 |
| `book_intro`, `perspective`, `review` | Collect Info |
| `cross_book_connections` | 长期记忆检索 |

### 笔记结构

```markdown
# 《书名》读书笔记

## 1. 书籍简介
{book_intro}

## 2. 核心观点总结
- {perspective items}

## 3. 你的独特思考
### 3.1 你认同的...
{resonance 维度 insight + 划线佐证}

### 3.2 你不太认同的...
{critique 维度 insight + 划线佐证}

### 3.3 让你联想到...
{connection 维度 insight}

### 3.4 你打算做出的改变
{action 维度 insight}

### 3.5 阅读中的情感触动
{emotion 维度 insight}

> 💡 以上引用你的划线原文作为佐证

## 4. 与其他读者的共鸣与差异
- 其他读者认为：{review}
- 你的视角：...

## 5. 总结

## 6. 你的阅读旅程 ★新增
- 在《书A》中，你曾思考过 {insight}
- 本书与之前形成了 {呼应/对比/深化}

> [未充分讨论]：{insufficient 维度列表} ★新增
```

### 规则

1. 每个 sufficient 维度至少一段内容
2. insufficient 维度标注 `[未充分讨论]`
3. 用户引用划线时，笔记引用原文
4. 第 6 节仅在有跨书关联时出现
5. 保存到 `data/notes/{书名}.md`

---

## Review

### 职责

Human-in-the-loop。展示笔记给用户，支持反馈后迭代。

### 流程

```
Generate Notes
    │
    ▼
展示笔记给用户（Markdown 预览）
    │
    ├── 用户满意 → 笔记发布，存档
    │
    └── 用户有反馈:
          "这部分不够准确"
          "这里我想补充..."
          "这个观点其实不是我的意思"
            │
            └── 提取反馈 → Execute（针对反馈做补充采集）
                          → Generate Notes（修订稿）
```

### 使用 LangGraph interrupt

```python
# Review 节点中
await interrupt({
    "message": "笔记已生成，请查看。",
    "note_preview": final_note,
    "actions": ["approve", "revise"]
})
# 等待用户响应
```

### 行为

```
Given 笔记生成完毕
When  展示给用户
And   用户标注「第3.2节不够准确」
Then  系统提取标注内容
And   回到 Execute 针对该维度追加对话
And   重新生成笔记

Given 用户点击「满意」
When  Review 收到 approve
Then  笔记存档
And   更新用户画像
And   流程结束
```
