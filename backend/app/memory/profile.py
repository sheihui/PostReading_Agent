"""用户画像计算"""
import json
import os
import logging
from datetime import datetime, timezone
from collections import Counter

from app.memory.models import UserProfile
from app.memory.insight_store import get_all_user_insights, store_insight

logger = logging.getLogger(__name__)

PROFILES_DIR = "./data/profiles"


def _ensure_profiles_dir():
    os.makedirs(PROFILES_DIR, exist_ok=True)


def _profile_path(user_id: str) -> str:
    return os.path.join(PROFILES_DIR, f"{user_id}.json")


def load_profile(user_id: str) -> UserProfile:
    """加载用户画像，不存在则返回默认。"""
    _ensure_profiles_dir()
    path = _profile_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return UserProfile.from_dict(data)
        except Exception as e:
            logger.warning(f"[profile] 加载失败: {e}")
    return UserProfile(user_id=user_id)


def save_profile(profile: UserProfile):
    """保存用户画像到 JSON 文件。"""
    _ensure_profiles_dir()
    path = _profile_path(profile.user_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"[profile] 画像已保存: {profile.user_id}")
    except Exception as e:
        logger.warning(f"[profile] 保存失败: {e}")


def update_profile(user_id: str) -> UserProfile:
    """全量重算用户画像。每次完成一本书后调用。"""
    insights = get_all_user_insights(user_id)
    active_insights = [i for i in insights if not i.superseded]

    profile = UserProfile(
        user_id=user_id,
        total_books=len(set(i.book_title for i in active_insights)),
        total_insights=len(active_insights),
        last_updated=datetime.now(timezone.utc).isoformat(),
    )

    if active_insights:
        # 反复出现的主题 — 按 dimension_label 中的关键词频率
        all_labels = [i.dimension_label for i in active_insights]
        label_words = []
        for label in all_labels:
            # 简单分词
            label_words.extend([w for w in label if len(w) >= 2])
        word_counts = Counter(label_words)
        profile.recurring_themes = [w for w, _ in word_counts.most_common(5)]

        # 思维风格 — 按 category 分布
        cats = [i.dimension_category for i in active_insights]
        cat_counts = Counter(cats)
        total = len(cats)
        critique_ratio = cat_counts.get("critique", 0) / total if total else 0
        resonance_ratio = cat_counts.get("resonance", 0) / total if total else 0
        action_ratio = cat_counts.get("action", 0) / total if total else 0

        if critique_ratio > 0.3:
            profile.thinking_style = "批判型"
        elif action_ratio > 0.25:
            profile.thinking_style = "实践型"
        elif resonance_ratio > 0.4:
            profile.thinking_style = "共鸣型"
        else:
            profile.thinking_style = "均衡型"

        # 分享偏好 — 检查 content 中工作相关词
        work_keywords = ["工作", "团队", "公司", "项目", "管理", "领导", "客户", "业务"]
        abstract_keywords = ["理论", "逻辑", "框架", "概念", "系统", "认知"]
        work_count = sum(1 for i in active_insights if any(w in i.content for w in work_keywords))
        abstract_count = sum(1 for i in active_insights if any(w in i.content for w in abstract_keywords))

        if work_count > abstract_count * 1.5:
            profile.sharing_preference = "倾向工作经历"
        elif abstract_count > work_count * 1.5:
            profile.sharing_preference = "倾向抽象思辨"
        else:
            profile.sharing_preference = "均衡"

    save_profile(profile)
    return profile
