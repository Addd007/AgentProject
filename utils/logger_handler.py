
import logging
import os
import sys
from datetime import datetime

from utils.path_tool import get_abs_path
#日志保存的根目录
LOG_ROOT=get_abs_path("logs")
ROOT_LOGGER_NAME="agent"
DEFAULT_LOG_FILE=os.path.join(
    LOG_ROOT,
    f"{ROOT_LOGGER_NAME}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.log",
)

#确保日志的目录存在
os.makedirs(LOG_ROOT,exist_ok=True)

#日志的格式配置
DEFAULT_LOG_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)


def _normalize_logger_name(name:str)->str:
    normalized=(name or ROOT_LOGGER_NAME).strip()
    if not normalized or normalized==ROOT_LOGGER_NAME:
        return ROOT_LOGGER_NAME
    if normalized.startswith(f"{ROOT_LOGGER_NAME}."):
        return normalized
    return f"{ROOT_LOGGER_NAME}.{normalized}"


def _configure_root_logger(
        console_level:int=logging.INFO,
        log_file:str=DEFAULT_LOG_FILE,
)->logging.Logger:
    root_logger=logging.getLogger(ROOT_LOGGER_NAME)
    if getattr(root_logger,"_agent_logger_configured",False):
        return root_logger

    root_logger.setLevel(logging.DEBUG)
    root_logger.propagate = False

    console_handler=logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(DEFAULT_LOG_FORMAT)
    root_logger.addHandler(console_handler)

    file_handler=logging.FileHandler(log_file,encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(DEFAULT_LOG_FORMAT)
    root_logger.addHandler(file_handler)

    root_logger._agent_logger_configured = True
    return root_logger

def get_logger(
        name:str=ROOT_LOGGER_NAME,
        console_level:int=logging.INFO,
        log_file=None,

)->logging.Logger:
    root_logger = _configure_root_logger(
        console_level=console_level,
        log_file=log_file or DEFAULT_LOG_FILE,
    )
    logger_name = _normalize_logger_name(name)
    if logger_name == ROOT_LOGGER_NAME:
        return root_logger

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    return logger


#快捷获取日志管理器
logger=get_logger()


if __name__=='__main__':
    logger.info('信息日志')
    logger.error('错误日志')
    logger.warning('警告日志')
    logger.debug("调试日志")
