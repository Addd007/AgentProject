import os
import re
from typing import Any

from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from utils.logger_handler import get_logger
from utils.config_handler import chroma_conf
from utils.file_handler import txt_loader, pdf_loader, listdir_with_allowed_type, get_file_md5_hex
from utils.path_tool import get_abs_path
from model.factory import get_embedding_model
from langchain_text_splitters import RecursiveCharacterTextSplitter


logger = get_logger(__name__)

class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=get_embedding_model(),
            persist_directory=get_abs_path(chroma_conf["persist_directory"]),
        )
        self.spliter=RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separator"],
            length_function=len,
        )
        self._keyword_retriever: BM25Retriever | None = None
        self._keyword_doc_count = -1

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k":chroma_conf["k"]})

    def _doc_key(self, doc: Document) -> str:
        source = str(doc.metadata.get("source", ""))
        page = str(doc.metadata.get("page", ""))
        return f"{source}|{page}|{doc.page_content}"

    def _normalize_text(self, text: str) -> list[str]:
        return re.findall(r"[\w\u4e00-\u9fff]+", (text or "").lower())

    def _ensure_keyword_retriever(self) -> BM25Retriever:
        stored = self.vector_store.get(include=["documents", "metadatas"])
        documents = stored.get("documents", []) or []
        metadatas = stored.get("metadatas", []) or []

        if self._keyword_retriever is not None and self._keyword_doc_count == len(documents):
            return self._keyword_retriever

        keyword_docs = [
            Document(page_content=content, metadata=metadata or {})
            for content, metadata in zip(documents, metadatas)
            if content
        ]
        retriever = BM25Retriever.from_documents(keyword_docs)
        retriever.k = chroma_conf.get("keyword_k", chroma_conf["k"])
        self._keyword_retriever = retriever
        self._keyword_doc_count = len(keyword_docs)
        return retriever

    def hybrid_search(self, query: str) -> list[Document]:
        vector_k = chroma_conf.get("vector_k", chroma_conf["k"])
        keyword_k = chroma_conf.get("keyword_k", chroma_conf["k"])
        final_top_k = chroma_conf.get("final_top_k", chroma_conf["k"])
        vector_weight = float(chroma_conf.get("vector_weight", 0.6))
        keyword_weight = float(chroma_conf.get("keyword_weight", 0.3))
        overlap_weight = float(chroma_conf.get("overlap_weight", 0.1))

        query_tokens = set(self._normalize_text(query))
        merged: dict[str, dict[str, Any]] = {}

        vector_results = self.vector_store.similarity_search_with_relevance_scores(query, k=vector_k)
        for rank, (doc, relevance_score) in enumerate(vector_results, start=1):
            key = self._doc_key(doc)
            merged[key] = {
                "doc": doc,
                "vector_score": max(float(relevance_score), 0.0),
                "keyword_score": 0.0,
                "overlap_score": 0.0,
                "vector_rank": rank,
                "keyword_rank": None,
            }

        keyword_retriever = self._ensure_keyword_retriever()
        keyword_retriever.k = keyword_k
        keyword_results = keyword_retriever.invoke(query)
        for rank, doc in enumerate(keyword_results, start=1):
            key = self._doc_key(doc)
            item = merged.setdefault(
                key,
                {
                    "doc": doc,
                    "vector_score": 0.0,
                    "keyword_score": 0.0,
                    "overlap_score": 0.0,
                    "vector_rank": None,
                    "keyword_rank": rank,
                },
            )
            item["keyword_score"] = max(item["keyword_score"], 1.0 / rank)
            item["keyword_rank"] = rank

        for item in merged.values():
            doc_tokens = set(self._normalize_text(item["doc"].page_content))
            overlap = len(query_tokens & doc_tokens) / max(len(query_tokens), 1)
            item["overlap_score"] = overlap
            item["hybrid_score"] = (
                vector_weight * item["vector_score"]
                + keyword_weight * item["keyword_score"]
                + overlap_weight * item["overlap_score"]
            )

        ranked = sorted(
            merged.values(),
            key=lambda item: item["hybrid_score"],
            reverse=True,
        )[:final_top_k]

        logger.debug(
            "Hybrid retrieval query=%s vector_hits=%s keyword_hits=%s final_hits=%s",
            query,
            len(vector_results),
            len(keyword_results),
            len(ranked),
        )
        return [item["doc"] for item in ranked]

    def load_document(self):
        #读取文件 md5 去重
        def check_md5_hex(md5_for_check:str):
            if not os.path.exists(get_abs_path(chroma_conf["md5_hex_store"])):
                open(get_abs_path(chroma_conf["md5_hex_store"]), "w",encoding="utf-8").close()
                return False #md5没处理过

            with open(get_abs_path(chroma_conf["md5_hex_store"]),"r",encoding="utf-8") as f:
                for line in f.readlines():
                    line=line.strip()
                    if line==md5_for_check:
                        return True

                return False


        def save_md5_hex(md5_for_check:str):
            with open(get_abs_path(chroma_conf["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_for_check+"\n")

        def get_file_documents(read_path:str):
            if read_path.endswith(".txt"):
                return txt_loader(read_path)

            if read_path.endswith(".pdf"):
                return pdf_loader(read_path)

            return []
        allowed_file_path:list[str]=listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_file_path:
            #获取文件的md5
            md5_hex=get_file_md5_hex(path)
            if check_md5_hex(md5_hex):

                logger.info(f"加载知识库，{path}已经存在知识库内跳过")
                continue
            try:
                documents:list[Document]=get_file_documents(path)
                if not documents:
                    logger.warning(f"加载知识库，{path}内没有有效内容跳过")
                    continue
                split_document:list[Document]=self.spliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"加载知识库，{path}没有有效内容跳过")
                    continue
                self.vector_store.add_documents(split_document)
                self._keyword_retriever = None
                self._keyword_doc_count = -1
                save_md5_hex(md5_hex)
                logger.info(f"加载知识库，{path}内容加载成功")
            except Exception as e:
                logger.error(f"加载知识库，{path}加载失败：{str(e)}",exc_info=True)
                continue


if __name__=="__main__":
    vs=VectorStoreService()
    vs.load_document()
    retriever=vs.get_retriever()
    res=retriever.invoke("密码")
    for r in res:
        print(r.page_content)
