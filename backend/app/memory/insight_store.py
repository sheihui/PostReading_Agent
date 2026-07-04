"""UserInsight 的 ChromaDB 存储与语义检索"""
import uuid
import logging
from typing import Optional

from langchain_chroma import Chroma
from app.storage.vector_store import embedding_model
from app.memory.models import UserInsight, CrossBookConnection

logger = logging.getLogger(__name__)

COLLECTION_NAME = "user_insights"
SIMILARITY_THRESHOLD = 0.5

# 单例
_insight_store: Optional[Chroma] = None


def _get_store() -> Chroma:
    global _insight_store
    if _insight_store is None:
        _insight_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embedding_model,
            persist_directory="./data/chroma",
        )
    return _insight_store


def store_insight(insight: UserInsight) -> str:
    """写入一条 insight，返回 id。容错：失败不抛异常。"""
    try:
        store = _get_store()
        doc_id = insight.id or str(uuid.uuid4())
        metadata = insight.to_dict()

        store.add_texts(
            texts=[insight.content],
            metadatas=[metadata],
            ids=[doc_id],
        )
        logger.info(f"[memory] insight 写入成功: {doc_id[:8]}... ({insight.book_title})")
        return doc_id
    except Exception as e:
        logger.warning(f"[memory] insight 写入失败: {e}")
        return ""


def retrieve_relevant_insights(
    query: str,
    user_id: str,
    k: int = 5,
    exclude_book: Optional[str] = None,
) -> list[UserInsight]:
    """语义检索相关历史 insight。容错：失败返回空列表。"""
    try:
        store = _get_store()
        results = store.similarity_search_with_score(query, k=k)

        insights = []
        for doc, score in results:
            # 相似度阈值
            similarity = 1.0 - score
            if similarity < SIMILARITY_THRESHOLD:
                continue
            # 限定用户
            if doc.metadata.get("user_id") != user_id:
                continue
            # 排除当前书籍
            if exclude_book and doc.metadata.get("book_title") == exclude_book:
                continue

            insight = UserInsight.from_dict(doc.metadata, id=doc.metadata.get("id"))
            insights.append(insight)

        return insights
    except Exception as e:
        logger.warning(f"[memory] 检索失败: {e}")
        return []


def retrieve_cross_book_connections(
    current_book: str,
    dimension_label: str,
    user_id: str,
    k: int = 5,
) -> list[CrossBookConnection]:
    """检索其他书中与当前维度相关的 insight，生成跨书关联。"""
    insights = retrieve_relevant_insights(
        query=dimension_label,
        user_id=user_id,
        k=k,
        exclude_book=current_book,
    )

    connections = []
    for ins in insights:
        rel = _classify_relationship(ins)
        connections.append(CrossBookConnection(
            source_book=current_book,
            source_dimension_label=dimension_label,
            source_content="",
            target_book=ins.book_title,
            target_dimension_label=ins.dimension_label,
            target_content=ins.content,
            relationship=rel,
            similarity_score=ins.composite_score,
        ))
    return connections


def _classify_relationship(insight: UserInsight) -> str:
    """根据 category 简单分类跨书关系"""
    mapping = {
        "resonance": "呼应",
        "critique": "对比",
        "connection": "呼应",
        "action": "补充",
        "emotion": "深化",
    }
    return mapping.get(insight.dimension_category, "呼应")


def get_all_user_insights(user_id: str) -> list[UserInsight]:
    """获取某用户的所有 insight（用于画像计算）。"""
    try:
        store = _get_store()
        # ChromaDB 没有 filter query，使用相似度搜索 + 大 k 再过滤
        results = store.similarity_search_with_score(user_id, k=200)

        insights = []
        seen = set()
        for doc, _score in results:
            if doc.metadata.get("user_id") != user_id:
                continue
            cid = doc.metadata.get("id", "")
            if cid in seen:
                continue
            seen.add(cid)
            insights.append(UserInsight.from_dict(doc.metadata, id=cid))

        return insights
    except Exception as e:
        logger.warning(f"[memory] 获取用户 insight 失败: {e}")
        return []


def mark_superseded(insight_id: str) -> bool:
    """标记一条 insight 为 superseded。"""
    try:
        store = _get_store()
        results = store.get(ids=[insight_id])
        if results and results["metadatas"]:
            meta = results["metadatas"][0]
            meta["superseded"] = True
            store.update_ids(ids=[insight_id], metadatas=[meta])
            return True
        return False
    except Exception as e:
        logger.warning(f"[memory] 标记 superseded 失败: {e}")
        return False
