
"""
    执行该脚本前先准备以下内容
    
    1.下载 https://github.com/kendryte/nncase/files/7594453/libomp140.x86_64.zip 并解压到 C:\Windows\System32 
    2.安装 dotnet-7 并添加环境变量
    3.安装 python 3.10.11
    4.创建 python 3.10.11 的虚拟环境
    ----------------------------------------------
        python -m venv venv
        source venv/bin/activate  # Linux/MacOS
        venv\Scripts\activate     # Windows
        deactivate                # 退出虚拟环境（可选）
    ----------------------------------------------
    5.进入 yolo 目录
    6.安装 pip install ultralytics (不用开梯子)
    7.开梯子
    8.运行 .py

    注意：如果报错找不到 datasets 请修改 C:\Users\<user_name>\AppData\Roaming\Ultralytics\settings.json 的 datasets_dir 为 yolo 目录，例如下面
        "datasets_dir": "E:\\Project\\Github\\yolo_test\\yolo",

    TODO: 
        1.后面考虑兼容 Linux/MacOS

最后：出现 runs/detect/train/weights/best.kmodel 就算成功了，该脚本就没用了！！！

"""

import os
import sys
import subprocess
import requests
import zipfile
import shutil

def download_file(url, destination):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    if os.path.exists(destination):
        print(f"文件已存在，跳过下载：{destination}")
        return True

    print(f"下载文件 {url}...")
    try:
        response = requests.get(url, headers=headers, stream=True, allow_redirects=True)
        response.raise_for_status()
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        print(f"文件已下载到 {destination}！")
        return True
    except requests.exceptions.RequestException as e:
        print(f"下载失败：{e}")
        print(f"无法下载文件 {url}，请检查链接的合法性或稍后重试。")
        return False

def is_directory_empty(directory):
    """
    检查目录是否为空。
    如果目录不存在或为空，则返回 True；否则返回 False。
    """
    if not os.path.exists(directory):
        return True
    return len(os.listdir(directory)) == 0


# def extract_zip(zip_path, extract_to):
#     """
#     解压 ZIP 文件到指定目录。
#     如果目标目录已存在且不为空，则跳过解压。
#     """
#     if not os.path.exists(zip_path):
#         print(f"文件不存在，跳过解压：{zip_path}")
#         return

#     if not is_directory_empty(extract_to):
#         print(f"目标目录已存在且不为空，跳过解压：{extract_to}")
#         return

#     print(f"解压文件 {zip_path} 到 {extract_to}...")
#     with zipfile.ZipFile(zip_path, "r") as zip_ref:
#         zip_ref.extractall(extract_to)
#     print(f"解压完成：{zip_path} -> {extract_to}")

def extract_zip(zip_path, extract_to, directory=None):
    """
    从 ZIP 文件中解压指定目录下的所有内容到目标目录。
    如果不指定目录，则解压整个 ZIP 文件。

    参数:
        zip_path (str): ZIP 文件的路径。
        directory (str, optional): ZIP 文件中需要解压的目录路径。默认为 None，表示解压整个 ZIP 文件。
        extract_to (str): 目标目录路径。默认为当前目录。
    """

    if not os.path.exists(zip_path):
        print(f"文件不存在，跳过解压：{zip_path}")
        return

    # if not is_directory_empty(extract_to):
    #     print(f"目标目录已存在且不为空，跳过解压：{extract_to}")
    #     return 

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # 获取 ZIP 文件中的所有文件和目录
        all_files = zip_ref.namelist()

        if directory is None:
            # 解压整个 ZIP 文件
            print(f"解压整个 ZIP 文件到 {extract_to}...")
            zip_ref.extractall(extract_to)
        else:
            # 过滤出指定目录下的所有文件和子目录
            directory_files = [f for f in all_files if f.startswith(directory + os.sep)]

            if not directory_files:
                print(f"指定的目录 {directory} 在 ZIP 文件中不存在或为空。")
                return

            # 解压指定目录下的所有文件和子目录
            print(f"解压目录 {directory} 下的所有内容到 {extract_to}...")
            for file in directory_files:
                zip_ref.extract(file, extract_to)

        print(f"解压完成！")

def run_command(command):
    """
    运行命令
    """
    try:
        print(f"运行命令: {' '.join(command)}")
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败：{e}")


def train_yolo_model(data_config, model_file, epochs, imgsz):
    command = [
        "yolo", "detect", "train",
        f"data={data_config}",
        f"model={model_file}",
        f"epochs={epochs}",
        f"imgsz={imgsz}"
    ]
    run_command(command)

def export_yolo_model(runs_path):
    print("导出 YOLO 模型为 ONNX 格式...")
    model_path = os.path.join(runs_path, "detect", "train", "weights", "best.pt")
    command = [
        "yolo", "export",
        f"model={model_path}",
        "format=onnx",
        "imgsz=320"
    ]
    run_command(command)
    print("ONNX 模型导出完成！")


def convert_to_kmodel(onnx_model_path, kmodel_output_dir, dataset_path):
    print("将 ONNX 模型转换为 Kmodel 格式...")
    if not os.path.exists(kmodel_output_dir):
        os.makedirs(kmodel_output_dir)

    command = [
        sys.executable,  # 使用当前 Python 解释器
        os.path.join("tools", "test_yolo11", "detect", "to_kmodel.py"),
        "--target", "k230",
        "--model", onnx_model_path,
        "--dataset", dataset_path,
        "--input_width", "320",
        "--input_height", "320",
        "--ptq_option", "0"
    ]
    run_command(command)
    print("Kmodel 转换完成！")


def install_dependencies(requirements):
    """
    安装依赖库，如果依赖已安装则跳过。
    """
    print("检查并安装依赖库...")
    for dep in requirements:
        if os.path.isfile(dep):  # 检查是否为本地文件
            if not os.path.exists(dep):
                print(f"文件不存在，跳过安装：{dep}")
                continue
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
        except subprocess.CalledProcessError as e:
            print(f"安装依赖时发生错误：{e}")
    print("依赖安装完成！")


if __name__ == "__main__":
    # 定义路径
    root_yolo_path = os.path.dirname(os.path.abspath(__file__))
    downloads_path = os.path.join(root_yolo_path, "downloads")
    dataset_path = os.path.join(root_yolo_path, "datasets")
    tools_path = os.path.join(root_yolo_path, "tools")
    models_path = os.path.join(root_yolo_path, "models")
    runs_path = os.path.join(root_yolo_path, "runs")

    # 创建必要的目录
    os.makedirs(downloads_path, exist_ok=True)
    #os.makedirs(dataset_path, exist_ok=True)
    os.makedirs(tools_path, exist_ok=True)

    # 下载文件
    download_urls = [
        ("https://github.com/kendryte/nncase/releases/download/v2.9.0/nncase_kpu-2.9.0-py2.py3-none-win_amd64.whl",
         os.path.join(downloads_path, "nncase_kpu-2.9.0-py2.py3-none-win_amd64.whl")),
        ("https://kendryte-download.canaan-creative.com/developer/k230/yolo_files/datasets.zip",
         os.path.join(downloads_path, "datasets.zip")),
        ("https://kendryte-download.canaan-creative.com/developer/k230/yolo_files/test_yolo11.zip",
         os.path.join(downloads_path, "test_yolo11.zip")),
         # 其他 yolo 版本的转换工具链接
        ("https://kendryte-download.canaan-creative.com/developer/k230/yolo_files/test_yolov5.zip",
         os.path.join(downloads_path, "test_yolov5.zip")),
        ("https://kendryte-download.canaan-creative.com/developer/k230/yolo_files/test_yolov8.zip",
         os.path.join(downloads_path, "test_yolov8.zip"))
    ]


    failed_downloads = []  # 用于记录下载失败的文件

    for url, destination in download_urls:
        if not download_file(url, destination):
            failed_downloads.append((url, destination))

    # 检查是否有下载失败的文件
    if failed_downloads:
        print("\n以下文件下载失败：")
        for url, destination in failed_downloads:
            print(f"下载地址：{url}")
            print(f"目标位置：{destination}")
        print("请检查网络连接或离线下载到指定位置！！！\n再次重试！！！")
        sys.exit(1)  # 由于有文件下载失败，退出脚本

    # 如果所有文件下载成功，继续后续操作


    # 解压文件
    zip_files = [
        (os.path.join(downloads_path, "datasets.zip"), root_yolo_path, None),
        (os.path.join(downloads_path, "test_yolo11.zip"), tools_path, None)
    ]

    for zip_path, extract_to, directory in zip_files:
        extract_zip(zip_path, extract_to, directory)

    # 安装依赖
    requirements = [
        "onnx",
        "onnxruntime",
        "onnxsim",
        "nncase==2.9.0",  # 动态安装 nncase
        os.path.join(downloads_path, "nncase_kpu-2.9.0-py2.py3-none-win_amd64.whl")
    ]
    install_dependencies(requirements)

    # 训练模型
    train_yolo_model(
        data_config=os.path.join(dataset_path, "fruits_yolo.yaml"),
        model_file=os.path.join(models_path, "yolo11n.pt"),
        epochs=2,
        imgsz=320
    )

    # 导出 ONNX 模型
    export_yolo_model(runs_path)

    # 转换为 Kmodel
    onnx_model_path = os.path.join(runs_path,"detect", "train", "weights", "best.onnx") 
    kmodel_output_dir = os.path.dirname(onnx_model_path)
    dataset_path = os.path.join(dataset_path,"fruits_yolo", "images", "test") 
    convert_to_kmodel(onnx_model_path, kmodel_output_dir, dataset_path)