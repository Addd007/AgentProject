from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

from model.factory import get_embedding_model
from utils.path_tool import get_abs_path


@dataclass(frozen=True)
class MemoryRecord:
    content: str
    metadata: dict


class UserMemoryService:
    """
    长期记忆（Long-term Memory）
    - 存储：Chroma（LangChain 组件）
    - 读取：Retriever（向量召回），按 user_id 做过滤（若底层支持）
    """

    def __init__(
        self,
        collection_name: str = "user_memory",
        persist_directory: str = "chroma_db",
    ) -> None:
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=get_embedding_model(),
            persist_directory=get_abs_path(persist_directory),
        )

    def add_memory(
        self,
        *,
        user_id: str,
        text: str,
        memory_type: str = "summary",
        extra_metadata: Optional[dict] = None,
        similarity_threshold: float = 0.95,
    ) -> None:
        """
        写入长期记忆前查重，profile/preference 字段只保留最新
        """
        from datetime import datetime
        import numpy as np
        try:
            embedding_model = get_embedding_model()
            new_emb = np.array(embedding_model.embed_query(text)).reshape(1, -1)
        except Exception:
            new_emb = None

        # 1. 查重：同 user_id/type 下相似内容跳过写入
        try:
            similar_docs = self.vector_store.similarity_search(
                text, k=3, filter={"user_id": user_id, "type": memory_type}
            )
            for doc in similar_docs:
                doc_emb = getattr(doc, "embedding", None)
                if new_emb is not None and doc_emb is not None:
                    doc_emb = np.array(doc_emb).reshape(1, -1)
                    from sklearn.metrics.pairwise import cosine_similarity
                    sim = cosine_similarity(new_emb, doc_emb)[0][0]
                    if sim > similarity_threshold:
                        return  # 跳过写入
        except Exception:
            pass

        # 2. profile/preference 字段只保留最新，先删旧
        if memory_type in ("profile", "preference"):
            try:
                self.vector_store.delete(where={"user_id": user_id, "type": memory_type})
            except Exception:
                pass

        # 3. 写入，带 created_at 字段
        metadata = {"user_id": user_id, "type": memory_type, "created_at": datetime.utcnow().isoformat()}
        if extra_metadata:
            metadata.update(extra_metadata)
        doc = Document(page_content=text, metadata=metadata)
        self.vector_store.add_documents([doc])

    def retrieve(
        self,
        *,
        user_id: str,
        query: str,
        k: int = 3,
        memory_type: Optional[str] = None,
        days: int = 90,
    ) -> list[MemoryRecord]:
        """
        两阶段召回：先向量检索，再关键词检索（如有 BM25），合并去重，时间窗过滤，返回 top-k
        """
        from datetime import datetime, timedelta
        # 1. 构造过滤条件
        if memory_type:
            filter_dict = {"$and": [{"user_id": user_id}, {"type": memory_type}]}
        else:
            filter_dict = {"user_id": user_id}

        # 2. 阶段一：向量检索
        try:
            semantic_docs = self.vector_store.similarity_search(query, k=20, filter=filter_dict)
        except (TypeError, ValueError):
            semantic_docs = self.vector_store.similarity_search(query, k=20)

        # 3. 阶段二：关键词检索（如有 BM25）
        keyword_docs = []
        if hasattr(self.vector_store, "bm25_search"):
            try:
                keyword_docs = self.vector_store.bm25_search(query, k=10, filter=filter_dict)
            except Exception:
                pass

        # 4. 合并去重（按内容去重）
        all_docs = {}
        for d in (semantic_docs or []):
            all_docs[d.page_content] = d
        for d in (keyword_docs or []):
            all_docs[d.page_content] = d

        # 5. 时间窗过滤
        cutoff = datetime.utcnow() - timedelta(days=days)
        records: list[MemoryRecord] = []
        for d in all_docs.values():
            md = d.metadata or {}
            if md.get("user_id") != user_id:
                continue
            if memory_type and md.get("type") != memory_type:
                continue
            created_at = md.get("created_at")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at)
                    if dt < cutoff:
                        continue
                except Exception:
                    pass
            records.append(MemoryRecord(content=d.page_content, metadata=md))
            if len(records) >= k:
                break


        # 结果重排：时间衰减+可信度+关键词命中
        from datetime import datetime
        import numpy as np
        def rerank_score(record: MemoryRecord, lambda_=0.01):
            md = record.metadata or {}
            # 时间衰减分
            created_at = md.get("created_at")
            if created_at:
                try:
                    delta_days = (datetime.utcnow() - datetime.fromisoformat(created_at)).days
                except Exception:
                    delta_days = 0
            else:
                delta_days = 0
            time_score = np.exp(-lambda_ * delta_days)
            # 可信度分
            confidence = float(md.get("confidence_score", 1.0))
            # 关键词命中分
            query_terms = set(query.lower().split())
            content = (record.content or "").lower()
            keyword_hit = int(any(term in content for term in query_terms))
            # 综合分：时间衰减 * 可信度 * (1+关键词命中)
            return time_score * confidence * (1 + keyword_hit)

        if records:
            records = sorted(records, key=rerank_score, reverse=True)
            return records[:k]

        return self._retrieve_recent_by_user(user_id=user_id, k=k, memory_type=memory_type)

    def _retrieve_recent_by_user(
        self,
        *,
        user_id: str,
        k: int,
        memory_type: Optional[str] = None,
    ) -> list[MemoryRecord]:
        where: dict = {"user_id": user_id}
        if memory_type:
            where = {"$and": [{"user_id": user_id}, {"type": memory_type}]}

        try:
            raw = self.vector_store.get(
                where=where,
                include=["documents", "metadatas"],
                limit=max(k, 12),
            )
        except Exception:
            return []

        docs = raw.get("documents") or []
        mds = raw.get("metadatas") or []
        if not docs:
            return []

        # Chroma 返回顺序通常为插入顺序，取末尾更接近最近写入。
        pairs = list(zip(docs, mds))[-max(k, 12):]
        pairs.reverse()

        records: list[MemoryRecord] = []
        for content, md in pairs:
            metadata = md or {}
            if metadata.get("user_id") != user_id:
                continue
            if memory_type and metadata.get("type") != memory_type:
                continue
            records.append(MemoryRecord(content=content, metadata=metadata))
            if len(records) >= k:
                break
        return records

