"""长期记忆数据模型"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class UserInsight:
    """用户对某个维度的个人思考"""
    user_id: str
    book_title: str
    dimension_category: str          # resonance | critique | connection | action | emotion
    dimension_label: str
    content: str                     # 核心思考内容
    composite_score: float           # 1.0-5.0
    scores: dict                     # {depth, specificity, personalization, evidence}
    id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    embedding: Optional[list[float]] = None
    superseded: bool = False

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "book_title": self.book_title,
            "dimension_category": self.dimension_category,
            "dimension_label": self.dimension_label,
            "content": self.content,
            "composite_score": self.composite_score,
            "scores": self.scores,
            "timestamp": self.timestamp,
            "superseded": self.superseded,
        }

    @classmethod
    def from_dict(cls, d: dict, id: Optional[str] = None) -> "UserInsight":
        return cls(
            user_id=d["user_id"],
            book_title=d["book_title"],
            dimension_category=d["dimension_category"],
            dimension_label=d["dimension_label"],
            content=d["content"],
            composite_score=d["composite_score"],
            scores=d.get("scores", {}),
            id=id,
            timestamp=d.get("timestamp", ""),
            superseded=d.get("superseded", False),
        )


@dataclass
class UserProfile:
    """跨书的用户阅读画像"""
    user_id: str
    recurring_themes: list[str] = field(default_factory=list)
    thinking_style: str = "均衡型"    # 批判型 | 共鸣型 | 实践型 | 均衡型
    sharing_preference: str = "均衡"  # 倾向工作经历 | 倾向抽象思辨 | 均衡
    total_books: int = 0
    total_insights: int = 0
    last_updated: str = ""

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "recurring_themes": self.recurring_themes,
            "thinking_style": self.thinking_style,
            "sharing_preference": self.sharing_preference,
            "total_books": self.total_books,
            "total_insights": self.total_insights,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        return cls(
            user_id=d["user_id"],
            recurring_themes=d.get("recurring_themes", []),
            thinking_style=d.get("thinking_style", "均衡型"),
            sharing_preference=d.get("sharing_preference", "均衡"),
            total_books=d.get("total_books", 0),
            total_insights=d.get("total_insights", 0),
            last_updated=d.get("last_updated", ""),
        )


@dataclass
class CrossBookConnection:
    """跨书关联"""
    source_book: str
    source_dimension_label: str
    source_content: str
    target_book: str
    target_dimension_label: str
    target_content: str
    relationship: str                # 呼应 | 对比 | 深化 | 补充
    similarity_score: float
