from langchain.agents.middleware import wrap_tool_call,before_model, dynamic_prompt,ModelRequest
from langchain.agents import AgentState
from langgraph.runtime import Runtime
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from utils.logger_handler import get_logger
from typing import Callable, Union

from utils.prompt_loader import load_system_prompts, load_report_prompts


logger = get_logger(__name__)


@wrap_tool_call
def monitor_tool(
        #请求数据封装
        request: ToolCallRequest,
        #执行函数
        handler:Callable[[ToolCallRequest], Union[ToolMessage, Command]],
)-> Union[ToolMessage, Command]:

    logger.info(f"[Monitoring tool]:{request.tool_call['name']}")
    logger.info(f"[Monitoring tool]: 传入参数：{request.tool_call['args']}")
    try:
        res=handler(request)
        logger.info(f"[Monitoring tool]:{request.tool_call['name']} 工具调用成功")
        if request.tool_call['name']=="fill_context_for_report":
            request.runtime.context["report"]=True

        return res
    except Exception as e:
        logger.error(f"[Monitoring tool]:{request.tool_call['name']} 工具调用失败,原因：{str(e)}")
        raise e



@before_model
def log_before_model(
        state:AgentState, #agent智能体中的状态记录
        runtime:Runtime,#执行过程中的上下文信息
):
    logger.info(f"[Before model]:带有{len(state['messages'])}条消息")
    logger.debug(f"[Before model]:{type(state['messages'][-1]).__name__} |{ state['messages'][-1].content.strip()}")

    return None


@dynamic_prompt      #每一次提示词生成之前，调用此函数
def report_prompt_switch(request:ModelRequest): #动态切换提示词

    is_report=request.runtime.context.get("report",False)
    if is_report:  #是报告生成场景，返回报告生成提示词内容
        return load_report_prompts()

    return load_system_prompts()


