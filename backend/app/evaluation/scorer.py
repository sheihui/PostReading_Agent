"""内置评测框架 — 每次运行自动评分。"""
import json
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from app.llm.client import call_llm

logger = logging.getLogger(__name__)

EVAL_DIR = "./data/eval"


def _ensure_eval_dir():
    os.makedirs(EVAL_DIR, exist_ok=True)


# ============ 第一层：笔记质量 ============

def evaluate_note_quality(final_note: str, llm_api_key: str = "") -> dict:
    """LLM-as-judge: 对笔记质量进行四维度评分。"""
    if not final_note:
        return {"personalization": 1, "depth": 1, "specificity": 1, "evidence": 1, "avg": 1.0}

    prompt = f"""你是一个读书笔记质量评估者。请对以下笔记进行四维度评分（每个维度 1-5 分）。

【笔记内容】
{final_note[:4000]}

评分维度：
1. personalization（个性化）: 笔记像「这个读者」的，还是任何人的？
   1=泛泛而谈，5=强烈体现独特个人经历和价值观

2. depth（深度）:
   1=复述书中观点，5=有批判性思考或超越原书的新视角

3. specificity（具体性）:
   1=全是抽象表述，5=丰富的个人例子，细节清晰

4. evidence（佐证）:
   1=无引用，5=划线和思考深度整合，互相佐证

输出 JSON（只输出 JSON）：
{{"personalization": 3, "depth": 2, "specificity": 2, "evidence": 1, "overall_comment": "简短评语（不超过50字）"}}"""

    try:
        result = call_llm(prompt, llm_api_key=llm_api_key)
        # 提取 JSON
        import re
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            scores = json.loads(match.group())
        else:
            scores = {"personalization": 1, "depth": 1, "specificity": 1, "evidence": 1}

        scores["avg"] = round(
            (scores.get("personalization", 1)
             + scores.get("depth", 1)
             + scores.get("specificity", 1)
             + scores.get("evidence", 1)) / 4, 1
        )
        return scores
    except Exception as e:
        logger.warning(f"[eval] 笔记质量评估失败: {e}")
        return {"personalization": 1, "depth": 1, "specificity": 1, "evidence": 1, "avg": 1.0}


# ============ 第二层：Reflect 准确性 ============

def evaluate_reflect_accuracy(
    reflect_result: dict,
    note_scores: dict,
    threshold: float = 3.0,
) -> dict:
    """对比 Reflect 的判定和笔记实际质量。

    Args:
        reflect_result: Reflect 节点的输出 {overall, dimension_evaluations}
        note_scores: evaluate_note_quality 的输出 {avg}
        threshold: 笔记均分多少以上算"好"

    Returns:
        {precision, recall, f1, tp, fp, fn, tn}
    """
    note_avg = note_scores.get("avg", 1.0)
    reflect_pass = reflect_result.get("overall") == "pass"

    tp = fp = fn = tn = 0

    if reflect_pass and note_avg >= threshold:
        tp = 1
    elif reflect_pass and note_avg < threshold:
        fp = 1
    elif not reflect_pass and note_avg >= threshold:
        fn = 1
    else:
        tn = 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "f1": round(f1, 2),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


# ============ 第三层：覆盖度 ============

def evaluate_coverage(collection_plan: list, dimension_sufficiency: dict) -> float:
    """计算采集清单的完成率。

    Returns:
        0.0 ~ 1.0
    """
    if not collection_plan:
        return 0.0

    total = len(collection_plan)
    completed = sum(
        1 for d in collection_plan
        if dimension_sufficiency.get(d.get("id", ""), False)
    )
    return round(completed / total, 2) if total > 0 else 0.0


# ============ 综合评测 ============

def run_full_evaluation(
    final_note: str,
    collection_plan: list,
    dimension_sufficiency: dict,
    reflect_result: dict,
    consolidation_result: Optional[dict] = None,
    llm_api_key: str = "",
) -> dict:
    """运行全部三层评测，生成 run_log。

    Returns:
        完整 run_log dict
    """
    run_id = str(uuid.uuid4())[:8]

    note_scores = evaluate_note_quality(final_note, llm_api_key)
    reflect_acc = evaluate_reflect_accuracy(reflect_result, note_scores)
    coverage = evaluate_coverage(collection_plan, dimension_sufficiency)

    run_log = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note_quality": note_scores,
        "reflect_accuracy": reflect_acc,
        "coverage": coverage,
        "overall_score": note_scores.get("avg", 1.0),
        "consolidation": consolidation_result or {},
    }

    # 保存到文件
    _save_run_log(run_id, run_log)

    return run_log


def _save_run_log(run_id: str, run_log: dict):
    """保存评测日志。"""
    _ensure_eval_dir()
    filepath = os.path.join(EVAL_DIR, f"{run_id}.json")
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(run_log, f, ensure_ascii=False, indent=2)
        logger.info(f"[eval] 日志已保存: {filepath}")
    except Exception as e:
        logger.warning(f"[eval] 日志保存失败: {e}")
