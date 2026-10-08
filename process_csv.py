from pathlib import Path

import pandas as pd

BASE_DIR: Path = Path(__file__).resolve().parent


def read_data(path: Path) -> list[dict]:
    """
    读取 CSV 文件并将其转换为列表字典格式。
    1. 使用 pandas 读取指定路径的 CSV 文件，返回一个 DataFrame。
    2. 使用 to_dict('records') 方法将 DataFrame 转换为列表字典。
    3. pandas 会自动推断类型（int/float），前端用 Number() 统一处理
    :return:
    """
    return pd.read_csv(path).to_dict("records")
