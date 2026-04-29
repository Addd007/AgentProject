"""
MCP 工具加载模块

通过 langchain-mcp-adapters 将 MCP Server 的工具转换为 LangChain tool，
运行时在后台线程中维护一个专用事件循环，保持 MCP 客户端生命周期。

使用前需配置环境变量：
  BRAVE_API_KEY=your_brave_api_key

Brave Search API Key 申请地址：https://brave.com/search/api/
"""

import asyncio
import os
import threading
from typing import Optional

from utils.logger_handler import get_logger

logger = get_logger(__name__)

_mcp_tools: list = []
_mcp_client = None
_bg_loop: Optional[asyncio.AbstractEventLoop] = None
_ready_event = threading.Event()
_init_error: Optional[str] = None


def _build_mcp_config() -> Optional[dict]:
    brave_key = os.getenv("BRAVE_API_KEY", "").strip()
    if not brave_key:
        logger.warning("未配置 BRAVE_API_KEY，网络搜索工具不可用")
        return None

    return {
        "brave-search": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "transport": "stdio",
            "env": {
                "BRAVE_API_KEY": brave_key,
            },
        }
    }


def _run_background_loop(config: dict) -> None:
    """在后台线程中运行事件循环，维持 MCP 客户端生命周期。"""
    global _mcp_client, _mcp_tools, _bg_loop, _init_error

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _bg_loop = loop

    async def _main():
        global _mcp_client, _mcp_tools, _init_error
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            _mcp_client = MultiServerMCPClient(config)
            await _mcp_client.__aenter__()
            _mcp_tools = _mcp_client.get_tools()
            logger.info("MCP 工具加载成功，共 %d 个工具: %s",
                        len(_mcp_tools), [t.name for t in _mcp_tools])
        except Exception as e:
            _init_error = str(e)
            logger.error("MCP 工具加载失败: %s", e)
        finally:
            _ready_event.set()

        # 保持事件循环运行，维持 MCP 客户端连接
        stop_event = asyncio.Event()
        await stop_event.wait()

    loop.run_until_complete(_main())


def load_mcp_tools(timeout: float = 30.0) -> list:
    """
    加载 MCP 工具列表（同步接口）。
    首次调用时启动后台线程初始化 MCP 客户端，之后复用。

    Returns:
        list: LangChain tool 列表，配置缺失或初始化失败时返回空列表
    """
    if _ready_event.is_set():
        return list(_mcp_tools)

    config = _build_mcp_config()
    if config is None:
        _ready_event.set()
        return []

    t = threading.Thread(target=_run_background_loop, args=(config,), daemon=True)
    t.start()

    if not _ready_event.wait(timeout=timeout):
        logger.error("MCP 工具初始化超时（%ss）", timeout)
        return []

    if _init_error:
        logger.error("MCP 工具不可用: %s", _init_error)
        return []

    return list(_mcp_tools)
