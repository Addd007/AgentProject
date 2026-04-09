
#为整个工程提供统一的绝对路径
import os


#获取工程所在的根目录
def get_project_root()->str:

    #当前文件的绝对路径
    current_file=os.path.abspath(os.path.abspath(__file__))

    #util路径
    current_dir=os.path.dirname(current_file)
    #根目录
    root=os.path.dirname(current_dir)
    return root

#传入相对路径，返回绝对路径
def get_abs_path(relative_path:str)->str:
    project_root=get_project_root()
    return os.path.join(project_root,relative_path)

if __name__=='__main__':
    abs_path=get_abs_path("config\config.txt")
    print(abs_path)

