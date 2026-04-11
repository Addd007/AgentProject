from abc import ABC, abstractmethod

from langchain_core.embeddings import Embeddings
from langchain_community.chat_models.tongyi import BaseChatModel
from typing import Optional, Union
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from utils.config_handler import rag_conf


_chat_model: Optional[BaseChatModel] = None
_embedding_model: Optional[Embeddings] = None

class BaseModelFactory(ABC):

    @abstractmethod
    def generator(self) -> Optional[Union[Embeddings, BaseChatModel]]:
        pass

class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Union[Embeddings, BaseChatModel]]:
        return ChatTongyi(model=rag_conf["chat_model_name"])

class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Union[Embeddings, BaseChatModel]]:
        return DashScopeEmbeddings(model=rag_conf["embedding_model_name"])


def get_chat_model() -> BaseChatModel:
    global _chat_model
    if _chat_model is None:
        _chat_model = ChatModelFactory().generator()
    return _chat_model


def get_embedding_model() -> Embeddings:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingsFactory().generator()
    return _embedding_model