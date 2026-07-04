# Evaluation

内置评测框架。每次 Agent 运行自动记录评分。

## Delta

全新能力。当前系统无评测机制。

## 第一层：笔记质量

Reflect 和 Review 之间，LLM-as-judge 打分。

### 维度

| 维度 | 1 | 3 | 5 |
|------|---|---|---|
| personalization | 可套在任何读者身上 | 有个人视角但不鲜明 | 强烈体现这个读者的独特经历 |
| depth | 复述书中观点 | 有自己的分析但浅 | 批判性思考或新视角 |
| specificity | 全是抽象表述 | 有例子但不详细 | 丰富的个人例子，细节清晰 |
| evidence | 无引用 | 引用了划线但连接不紧密 | 划线和思考深度整合 |

```
note_score = avg(personalization, depth, specificity, evidence)
```

## 第二层：Reflect 准确性

Reflect 的评估 vs 笔记实际质量：

```
Reflect 判 pass + note_score ≥ 3.0 → TP ✓
Reflect 判 pass + note_score < 3.0 → FP（Reflect 太松）
Reflect 判 revise/replan + note_score ≥ 3.0 → FN（Reflect 太严）
Reflect 判 revise/replan + note_score < 3.0 → TN ✓
```

```
precision = TP / (TP + FP)
recall = TP / (TP + FN)
F1 = 2 × P × R / (P + R)
```

## 第三层：覆盖度

```
覆盖度 = 笔记中覆盖的书籍核心观点数 / Plan 中识别的核心观点总数
```

规则检查，不需要 LLM。

## 评测日志

每次运行输出到 `data/eval/{run_id}.json`：

```json
{
  "run_id": "uuid",
  "timestamp": "ISO8601",
  "book_title": "str",
  "plan": {"dimension_count": 5, "categories_covered": [...]},
  "dimensions": [{
    "id": "d_001",
    "category": "resonance",
    "turns": 3,
    "sufficient": true,
    "note_quality": {"personalization": 3, "depth": 2, "specificity": 2, "evidence": 1, "avg": 2.0}
  }],
  "consolidation": {"issues_found": 1, "new_dimensions_added": 1},
  "reflect": {
    "assessment": "pass",
    "dimension_evaluations": [...]
  },
  "overall_note_score": 3.2,
  "reflect_accuracy": {"precision": 0.8, "recall": 0.75, "f1": 0.77},
  "coverage": 0.75
}
```

## 用途

1. **迭代 Reflect** — 看 F1，调评估 prompt 和阈值
2. **迭代 Plan** — 看覆盖度，调采集策略
3. **迭代 Execute** — 看 turns 和 note_quality 的关系，调追问上限
4. **A/B 对比** — 两版 prompt 跑同一本书，对比 overall_note_score
