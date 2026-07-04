# Reflection

Reflect 放在笔记生成**之后**。对照采集清单，整体评估笔记质量。这是真正的 Plan-Execute-**Reflect**。

## Delta

全新定位。旧 Reflect 是 per-dimension 路由器，已废弃。

## 职责

```
输入:  生成的笔记 + 原始采集清单 + 采集到的 insight
任务:  笔记是否达成了采集目标？
输出:  通过 / 某维度薄弱需补充 / 整体不行需重规划
```

不做 per-dimension 评估。不做路由。

## 输入

| 字段 | 说明 |
|------|------|
| `final_note` | 刚生成的笔记全文 |
| `collection_plan` | 原始采集清单（每个维度的 goal） |
| `collected_insights` | 采集阶段得到的 insight |
| `dimension_sufficiency` | 采集阶段每个维度是否完成 |

## 评估

Reflect 把笔记和清单对照：

```json
{
  "overall_assessment": "pass | revise_dimension | replan",
  "dimension_evaluations": [
    {
      "dimension_id": "d_001",
      "category": "resonance",
      "in_note": true,
      "quality": "good | thin | missing",
      "issue": "如果 quality 不是 good，说明问题"
    }
  ],
  "summary": "整体评估说明"
}
```

### 评估逻辑

```
对每个维度:
  - 笔记中是否有该维度对应的内容？ → in_note
  - 内容是深度个人思考还是泛泛而谈？ → quality
  - 是否引用了用户的划线？ → 加分

整体:
  - 所有 high-priority 维度 quality=good → pass
  - 个别维度 thin/missing → revise_dimension（指回 Execute 补充）
  - 多个 high 维度 thin/missing，或整体方向偏了 → replan（回 Plan）
```

## 条件边

```
Reflect → pass → Review
        → revise_dimension → Execute（补充指定维度）
        → replan → Plan（重新生成清单）
```

## 行为

```
Given 笔记中所有 high-priority 维度都有深度内容
And   整体结构完整
When  Reflect 评估
Then  overall=pass
And   进入 Review

Given 笔记中 d_002 内容只有一句话，quality=thin
And   其他维度 quality=good
When  Reflect 评估
Then  overall=revise_dimension
And   回 Execute，指定补充 d_002

Given 笔记整体都是复述书中观点，无个人思考
When  Reflect 评估
Then  overall=replan
And   回 Plan，重新设计采集策略
```

## 评测

```
Reflect 的评估 vs 笔记实际质量（LLM-as-judge 评分）

Reflect 判 pass + 笔记评分 ≥ 3.0 → TP ✓
Reflect 判 pass + 笔记评分 < 3.0 → FP（Reflect 太松）
Reflect 判 revise/replan + 笔记评分 ≥ 3.0 → FN（Reflect 太严）
Reflect 判 revise/replan + 笔记评分 < 3.0 → TN ✓

precision = TP / (TP + FP)
recall = TP / (TP + FN)
```
