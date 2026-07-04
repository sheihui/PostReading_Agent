# Consolidation

所有维度采集完毕后，跨维度综合检查。发现矛盾、缺口、或新方向时，可触发追加采集或重规划。

## Delta

全新节点。当前系统不存在此功能。

## 职责

跨维度审视采集结果，确保知识的**内部一致性**和**覆盖完整性**。

## 输入

| 字段 | 来源 |
|------|------|
| `collection_plan` | Plan |
| `collected_insights` | Execute + Reflect（所有维度） |
| `dimension_sufficiency` | Reflect |
| `book_intro`, `perspective` | Collect Info |

## 检查项

### 1. 矛盾检测

```
D1 (resonance): "用户认同系统1的直觉判断理论"
D2 (critique):  "用户认为系统1在金融决策中是灾难，应该被压制"

→ 矛盾！用户到底信任系统1还是不信任？
→ 输出: {type: "contradiction", dims: ["d_001", "d_002"], 
         question: "你提到直觉在急诊室有用、但在投资中不可靠，你觉得区别在哪？"}
```

### 2. 缺口检测

```
书籍核心观点: ["系统1/系统2", "锚定效应", "损失厌恶", "过度自信"]
已采集维度: 仅覆盖了系统1/系统2
未覆盖: 锚定效应、损失厌恶、过度自信

→ 输出: {type: "gap", topics: ["锚定效应", "损失厌恶", "过度自信"]}
```

### 3. 新发现

```
用户在最后一个维度中提到了一个清单外的深刻内容：
"这本书让我重新思考了我爸的投资失败 — 他完全是被损失厌恶害了"

→ 这是高质量的个人连接，不在清单里
→ 输出: {type: "discovery", suggestion: "用户对'损失厌恶'有强烈的个人连接，建议新增维度"}
```

## 输出

```json
{
  "issues": [
    {
      "type": "contradiction | gap | discovery",
      "severity": "high | normal",
      "description": "...",
      "suggested_action": "add_followup | add_dimension | replan"
    }
  ],
  "overall": "proceed | revise"
}
```

## 条件边

```
Consolidate → 无问题 → Generate Notes
            → 有矛盾/缺口 → 追加追问 → Execute
            → 有新发现 → 新增维度 → Plan (replan)
```

## 行为

```
Given D1 和 D2 存在明显矛盾
When  Consolidate 检测到
Then  生成一个追问维度
And   回到 Execute 让用户澄清

Given 书籍有 4 个核心观点，仅覆盖 1 个
When  Consolidate 检测到
Then  标记缺口
And   回到 Plan 生成新维度
```

## 评测

```
Consolidate 发现的矛盾/缺口是否合理？
  → 人工抽查或 LLM judge 评估

Consolidate 触发的新维度是否产生有价值的内容？
  → 查看新维度的 note_quality_score
```
