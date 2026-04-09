import hashlib
import os

from langchain_community.document_loaders import PyPDFLoader,TextLoader
from langchain_core.documents import Document

from utils.logger_handler import get_logger


logger = get_logger(__name__)

def get_file_md5_hex(filepath:str):
    if not os.path.exists(filepath):
        logger.error(f"File {filepath} does not exist")
        return

    if not os.path.isfile(filepath):
        logger.error(f"File {filepath} is not a file")
        return

    md5 = hashlib.md5()

    chunk_size = 4096 #4kB分片

    try:
        with open(filepath, "rb") as f:  #必须二进制读取
            while chunk:= f.read(chunk_size):
                md5.update(chunk)
            """
            等同于：
            chunk=f.read(chunk_size)
            while chunk:
                chunk=f.read(chunk_size)
                md5.update(chunk)
                
            """

            md5_hex = md5.hexdigest()
            return md5_hex
    except Exception as e:
        logger.error(f"File {filepath} 计算MD5失败")
        raise e


def listdir_with_allowed_type(path:str,allowed_types:tuple[str]): #返回文件夹内的文件列表
    files=[]
    if not os.path.isdir(path):
        logger.error(f"Directory {path} is not a directory")
        return allowed_types

    for f in os.listdir(path):
        if f.endswith(allowed_types):
            files.append(os.path.join(path, f))

    return tuple(files) #元组 不可改变


def pdf_loader(filepath:str,passwd=None)->list[Document]:
    return PyPDFLoader(filepath,passwd).load()


def txt_loader(filepath:str)->list[Document]:
    return TextLoader(filepath).load()


