import os
import sys
import time
import threading
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from langchain.agents.middleware import *
from agent.tools.agent_tools import *
from agent.tools.middlewares import *
from agent.tools.mcp_tools import load_mcp_tools
from model.factory import get_chat_model
from utils.logger_handler import get_logger
from utils.prompt_loader import load_system_prompts


from typing import Optional

from rag.user_memory import UserMemoryService

# ── 长期记忆检索结果缓存 ─────────────────────────────────────────────────────
# key: user_id  value: {"msg": ..., "ts": float}
_MEMORY_CACHE: dict[str, dict] = {}
_MEMORY_CACHE_TTL = 30  # 秒，30s 内同一用户复用缓存，减少 TTFT
_MEMORY_CACHE_LOCK = threading.Lock()


logger = get_logger(__name__)


class ReactAgent:
    def __init__(self, max_turns: int = 6):
        # 滑动窗口短期记忆：保留最近 N 轮（1轮=用户+助手，最多2条消息）
        self.max_messages = max_turns * 2
        self.system_prompt = load_system_prompts()
        chat_model = get_chat_model()
        mcp_tools = load_mcp_tools()
        self.agent = create_agent(
            model=chat_model,
            system_prompt=self.system_prompt,
            tools=[
                get_weather,
                get_location,
                get_user_id,
                get_current_month,
                fetch_external_data,
                fill_context_for_report,
                rag_summarize,
                *mcp_tools,
            ],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
        )
        self.long_term_memory = UserMemoryService()

    def current_user_id(self) -> str:
        current_user_id = peek_current_user_id()
        if current_user_id:
            return str(current_user_id).strip()
        return str(get_user_id.invoke({})).strip()

    def _fetch_memory_msg(self, *, user_id: str, query: str) -> Optional[dict]:
        """从向量库检索并构建记忆消息（无缓存，真正的 IO 操作）。"""
        retrieved_memories = self.long_term_memory.retrieve(
            user_id=user_id,
            query=query,
            k=10,
        )

        # 对“你记得我吗/我之前说过什么”这类查询做语义兜底，提升召回稳定性。
        memory_intent_keywords = ["记得", "之前", "说过", "聊过", "偏好", "习惯", "信息", "档案"]
        if (not retrieved_memories) and any(k in (query or "") for k in memory_intent_keywords):
            retrieved_memories = self.long_term_memory.retrieve(
                user_id=user_id,
                query="用户历史信息 偏好 个人档案 之前对话",
                k=10,
            )

        profile_memories = [m for m in retrieved_memories if m.metadata.get("type") == "profile"][:2]
        preference_memories = [m for m in retrieved_memories if m.metadata.get("type") == "preference"][:2]
        fact_memories = [m for m in retrieved_memories if m.metadata.get("type") == "fact"][:2]
        qa_memories = [m for m in retrieved_memories if m.metadata.get("type") == "qa_summary"][:1]

        if not profile_memories and not preference_memories and not fact_memories and not qa_memories:
            return None

        sections: list[str] = []

        if profile_memories:
            profile_lines = "\n".join(f"- {m.content}" for m in profile_memories)
            sections.append("【用户档案】\n" + profile_lines)

        if preference_memories:
            pref_lines = "\n".join(f"- {m.content}" for m in preference_memories)
            sections.append("【用户偏好】\n" + pref_lines)

        if fact_memories:
            fact_lines = "\n".join(f"- {m.content}" for m in fact_memories)
            sections.append("【历史结论】\n" + fact_lines)

        if qa_memories:
            qa_lines = "\n".join(f"- {m.content}" for m in qa_memories)
            sections.append("【相关上下文】\n" + qa_lines)

        return {
            "role": "system",
            "content": "以下为用户长期记忆（仅供参考，可能存在过期信息）：\n" + "\n\n".join(sections),
        }


    def build_memory_message(self, *, user_id: str, query: str) -> Optional[dict]:
        """带 TTL 缓存的记忆消息构建，减少重复向量检索导致的 TTFT 延迟。"""
        now = time.monotonic()
        with _MEMORY_CACHE_LOCK:
            cached = _MEMORY_CACHE.get(user_id)
            if cached and (now - cached["ts"]) < _MEMORY_CACHE_TTL:
                logger.debug("memory cache hit for user=%s", user_id)
                return cached["msg"]

        msg = self._fetch_memory_msg(user_id=user_id, query=query)

        with _MEMORY_CACHE_LOCK:
            _MEMORY_CACHE[user_id] = {"msg": msg, "ts": time.monotonic()}

        return msg

    def refresh_memory_cache(self, user_id: str) -> None:
        """写入新记忆后异步刷新缓存，使下次请求直接命中最新数据，避免缓存失效导致 TTFT 劣化。"""
        def _do_refresh():
            try:
                msg = self._fetch_memory_msg(user_id=user_id, query="")
                with _MEMORY_CACHE_LOCK:
                    _MEMORY_CACHE[user_id] = {"msg": msg, "ts": time.monotonic()}
                logger.debug("memory cache refreshed for user=%s", user_id)
            except Exception as e:
                logger.warning("memory cache refresh failed for user=%s: %s", user_id, e)
                # 刷新失败则清空缓存，下次请求重新检索
                with _MEMORY_CACHE_LOCK:
                    _MEMORY_CACHE.pop(user_id, None)

        threading.Thread(target=_do_refresh, daemon=True).start()
    def _should_use_direct_chat(self, query: str) -> bool:
        normalized = (query or "").strip().lower()
        if not normalized:
            return False

        tool_keywords = [
            "报告",
            "记录",
            "数据",
            "天气",
            "城市",
            "位置",
            "湿度",
            "降雨",
            "rag",
            "参考资料",
            "故障",
            "选购",
            "保养",
            "维修",
            "月",
            "month",
            "user id",
            "userid",
            "当前位置",
            "当前城市",
            "所在城市",
            "今年",
            "本月",
            "上月",
            "这个月",
            "上个月",
            "我的使用",
            "我的数据",
            "我的报告",
            "个人报告",
            "使用报告",
            "external",
            "fill_context_for_report",
            "fetch_external_data",
            # 网络搜索相关
            "搜索",
            "查一下",
            "网上",
            "最新",
            "新闻",
            "search",
        ]
        if any(keyword in normalized for keyword in tool_keywords):
            return False

        return True

    def _get_static_reply(self, query: str) -> Optional[str]:
        normalized = " ".join((query or "").strip().lower().split())
        if not normalized:
            return None

        greeting_keywords = {"你好", "您好", "hello", "hi", "嗨", "在吗", "在么"}
        if normalized in greeting_keywords:
            return "你好，我是扫地机器人智能客服。你可以直接问我选购、使用、保养或故障处理问题。"

        thanks_keywords = {"谢谢", "多谢", "thanks", "thank you"}
        if normalized in thanks_keywords:
            return "不客气，有需要可以继续问我。"

        identity_keywords = {"你是谁", "你是干什么的", "介绍下你自己", "你能做什么", "能帮我什么"}
        if normalized in identity_keywords:
            return "我是扫地机器人智能客服，可以帮你解答选购建议、使用方法、保养维护和常见故障问题。"

        return None

    def _content_to_text(self, content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""

    def _stream_direct_reply(self, input_messages: list[dict]):
        direct_messages = [SystemMessage(content=self.system_prompt)]
        for message in input_messages:
            role = message.get("role")
            content = message.get("content", "")
            if role == "system":
                direct_messages.append(SystemMessage(content=content))
            elif role == "user":
                direct_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                direct_messages.append(AIMessage(content=content))

        emitted_text = ""
        for chunk in get_chat_model().stream(direct_messages):
            content = self._content_to_text(getattr(chunk, "content", ""))
            if not content or content == emitted_text:
                continue

            if content.startswith(emitted_text):
                delta = content[len(emitted_text):]
            else:
                delta = content

            emitted_text = content
            if delta:
                yield delta

    def execute_stream(self, query: str, history: Optional[list[dict]] = None, user_id: Optional[str] = None):
        all_messages = history if history else [{"role": "user", "content": query}]
        input_messages = all_messages[-self.max_messages :]

        context_user_id = str(user_id).strip() if user_id else self.current_user_id()
        token = set_current_user_id(context_user_id)
        try:
            static_reply = self._get_static_reply(query)
            if static_reply:
                yield static_reply
                return

            memory_msg = self.build_memory_message(user_id=context_user_id, query=query)
            if memory_msg:
                input_messages = [memory_msg] + input_messages

            if self._should_use_direct_chat(query):
                yield from self._stream_direct_reply(input_messages)
                return

            input_dict = {"messages": input_messages}

            emitted_text = ""
            for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
                latest_message = chunk["messages"][-1]
                message_type = getattr(latest_message, "type", None)
                if message_type != "ai":
                    continue

                if getattr(latest_message, "tool_calls", None):
                    continue

                content = getattr(latest_message, "content", None)
                if not isinstance(content, str) or not content:
                    continue

                if content == emitted_text:
                    continue

                if content.startswith(emitted_text):
                    delta = content[len(emitted_text):]
                else:
                    delta = content

                emitted_text = content
                if delta:
                    yield delta
        finally:
            reset_current_user_id(token)

    def save_long_term_memory(self, *, user_id: str, user_query: str, assistant_answer: str) -> None:
        q = (user_query or "").strip()
        a = (assistant_answer or "").strip()
        if not q or not a:
            return

        # 1. 保留完整问答摘要
        qa_text = f"Q: {q}\nA: {a}"
        try:
            self.long_term_memory.add_memory(
                user_id=user_id,
                text=qa_text,
                memory_type="qa_summary",
                extra_metadata={"source": "chat", "version": 2},
            )
        except Exception as e:
            logger.warning(f"Failed to save qa_summary: {e}")
            pass

        # 2. 抽取用户偏好与个人档案
        profile_keywords = [
            "我叫",
            "名字",
            "姓名",
            "我是",
            "我姓",
        ]
        preference_keywords = [
            "喜欢",
            "更看重",
            "预算",
            "宠物",
            "地毯",
            "小户型",
            "静音",
            "拖地",
            "吸力",
            "避障",
            "自动集尘",
            "自动洗拖布",
        ]

        if any(k in q for k in profile_keywords):
            try:
                self.long_term_memory.add_memory(
                    user_id=user_id,
                    text=f"用户档案：{q}",
                    memory_type="profile",
                    extra_metadata={"source": "query", "field": "name"},
                )
            except Exception as e:
                logger.warning(f"Failed to save profile: {e}")
                pass
        else:
            if any(k in q for k in preference_keywords):
                try:
                    self.long_term_memory.add_memory(
                        user_id=user_id,
                        text=f"用户偏好：{q}",
                        memory_type="preference",
                        extra_metadata={"source": "query"},
                    )
                except Exception as e:
                    logger.warning(f"Failed to save preference: {e}")
                    pass

        # 3. 抽取回答中的结论
        first_line = a.split("\n")[0].strip(" -•")
        if first_line:
            try:
                self.long_term_memory.add_memory(
                    user_id=user_id,
                    text=f"结论：{first_line}",
                    memory_type="fact",
                    extra_metadata={"source": "answer"},
                )
            except Exception as e:
                logger.warning(f"Failed to save fact: {e}")
                pass

        # 写入记忆后，异步刷新缓存，下次请求直接命中最新数据
        self.refresh_memory_cache(user_id)


if __name__ == "__main__":
    agent = ReactAgent()
    for chunk in agent.execute_stream("生成我的使用报告"):
        print(chunk, end="", flush=True)