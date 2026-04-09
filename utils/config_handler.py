
#yaml 格式配置文件
import yaml
from utils.logger_handler import get_logger
from utils.path_tool import get_abs_path


logger = get_logger(__name__)


def _load_yaml(config_path:str,encoding:str="utf-8"):
    try:
        with open(config_path,"r",encoding=encoding) as f:
            return yaml.load(f,Loader=yaml.FullLoader)
    except Exception as exc:
        logger.error(f"加载配置文件失败: {config_path}, error={exc}")
        raise


def load_rag_config(config_path:str=get_abs_path("config/rag.yaml"),encoding="utf-8"):
    return _load_yaml(config_path,encoding)#全量加载


def load_chroma_config(config_path: str = get_abs_path("config/chroma.yaml"), encoding="utf-8"):
    return _load_yaml(config_path, encoding)  # 全量加载


def load_prompts_config(config_path: str = get_abs_path("config/prompts.yaml"), encoding="utf-8"):
    return _load_yaml(config_path, encoding)  # 全量加载


def load_agent_config(config_path: str = get_abs_path("config/agent.yaml"), encoding="utf-8"):
    return _load_yaml(config_path, encoding)  # 全量加载

def load_map_config(config_path:str=get_abs_path("config/map.yaml"),encoding="utf-8"):
    return _load_yaml(config_path,encoding)#全量加载

rag_conf = load_rag_config()
chroma_conf = load_chroma_config()
prompts_conf = load_prompts_config()
agent_conf = load_agent_config()
map_conf = load_map_config()

if __name__ == "__main__":
    print(rag_conf["chat_model_name"])

