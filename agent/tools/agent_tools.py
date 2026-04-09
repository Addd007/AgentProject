import os
from contextvars import ContextVar, Token
from datetime import datetime
from typing import Optional

import requests
from langchain_core.tools import tool

from rag.rag_service import RagSummarizeService
from utils.config_handler import agent_conf, map_conf
from utils.logger_handler import get_logger
from utils.path_tool import get_abs_path

logger = get_logger(__name__)
rag = RagSummarizeService()
external_data = {}
_CURRENT_USER_ID: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)
_DEFAULT_USER_ID = os.getenv("AGENT_DEFAULT_USER_ID", "1001")


def set_current_user_id(user_id: Optional[str]) -> Token:
    return _CURRENT_USER_ID.set(user_id)


def reset_current_user_id(token: Token) -> None:
    _CURRENT_USER_ID.reset(token)


def peek_current_user_id() -> Optional[str]:
    return _CURRENT_USER_ID.get()


@tool(description="从向量存储中查找参考资料，返回消息形式字符串")
def rag_summarize(query: str) -> str:
    res = rag.rag_summarize(query)
    return res

@tool(description="获取用户所在城市名称，返回纯字符串")
def get_location() -> str:
    """
    方式2：直接使用高德IP定位接口
    自动获取请求端IP对应的城市，无需手动获取IP
    """
    url = "https://restapi.amap.com/v3/ip"
    params = {
        "key": map_conf["MAP_KEY"]
    }

    try:
        res = requests.get(url, params=params, timeout=5).json()

        if res.get("status") == "1":
            province = res.get("province")
            city = res.get("city")
            return f"用户所在城市: {province}{city}"
        else:
            return f"定位失败: {res.get('info', '未知错误')}"

    except Exception as e:
        logger.warning(f"获取用户位置失败: {e}")
        return f"请求异常: {e}"



@tool(description="获取输入城市的当前天气信息，返回纯字符串")
def get_weather(city: str) -> str:
    """
    输入城市名称，返回高德天气信息
    """
    if not city:
        return "请提供城市名称"

    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {
        "key": map_conf["MAP_KEY"],
        "city": city,
        "extensions": "base",  # base=实时天气, all=未来天气预报
        "output": "JSON"
    }

    try:
        res = requests.get(url, params=params, timeout=5).json()

        if res.get("status") != "1":
            return f"天气查询失败: {res.get('info','未知错误')}"

        lives = res.get("lives")
        if not lives:
            return "未查询到天气信息"

        now = lives[0]
        province = now.get("province")
        city_name = now.get("city")
        weather = now.get("weather")
        temp = now.get("temperature")
        wind_dir = now.get("winddirection")
        wind_power = now.get("windpower")
        humidity = now.get("humidity")
        report_time = now.get("reporttime")

        return (
            f"{province}{city_name} 当前天气：{weather}，温度 {temp}°C，"
            f"风向 {wind_dir}，风力 {wind_power}级，湿度 {humidity}% "
            f"(数据时间：{report_time})"
        )

    except Exception as e:
        logger.warning(f"查询天气失败，city={city}: {e}")
        return f"请求异常: {e}"



@tool(description="获取当前用户id，返回纯字符串")
def get_user_id() -> str:
    user_id = peek_current_user_id()
    return user_id or _DEFAULT_USER_ID


@tool(description="获取当前年月份，返回纯字符串")
def get_current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def generate_external_data():
    if not external_data:
        external_data_path = get_abs_path(agent_conf["external_data_path"])

        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"{external_data_path} not exist")

        with open(external_data_path, "r", encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                arr: list[str] = line.strip().split(",")
                user_id: str = arr[0].replace('"', "")
                feature: str = arr[1].replace('"', "")
                efficiency: str = arr[2].replace('"', "")
                consumables: str = arr[3].replace('"', "")
                comparison: str = arr[4].replace('"', "")
                time: str = arr[5].replace('"', "")
                if user_id not in external_data:
                    external_data[user_id] = {}

                external_data[user_id][time] = {
                    "特征": feature,
                    "清洁效率": efficiency,
                    "耗材": consumables,
                    "对比": comparison,
                }


@tool(description="从外部系统中获取指定用户在指定月份中的使用记录，返回纯字符串，如果没有记录则返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str:
    generate_external_data()
    try:
        return external_data[user_id][month]
    except KeyError:
        logger.warning(f"未能检索到用户{user_id}在{month}的使用数据")
        return ""


@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report ·已调用"





if "__main__" == __name__:
    r=get_location()
    print(r)
    res=get_weather("昆明")
    print(res)




