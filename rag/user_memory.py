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
    ) -> None:
        metadata = {"user_id": user_id, "type": memory_type}
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
    ) -> list[MemoryRecord]:
        # 说明：不同 Chroma/LangChain 版本对 filter/where 的 key 支持不完全一致，
        # 这里做最小可用实现：优先尝试过滤；失败则退化为不带过滤的语义检索后再本地筛选。
        if memory_type:
            filter_dict = {"$and": [{"user_id": user_id}, {"type": memory_type}]}
        else:
            filter_dict = {"user_id": user_id}

        try:
            docs = self.vector_store.similarity_search(query, k=k, filter=filter_dict)
        except (TypeError, ValueError):
            docs = self.vector_store.similarity_search(query, k=k)

        records: list[MemoryRecord] = []
        for d in docs:
            md = d.metadata or {}
            if md.get("user_id") != user_id:
                continue
            if memory_type and md.get("type") != memory_type:
                continue
            records.append(MemoryRecord(content=d.page_content, metadata=md))

        # 兜底：若语义检索命中为空，回退到按 user_id 抓取最近记忆，避免“记得我吗”类问题查不到。
        if records:
            return records

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

