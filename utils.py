# utils.py
import json
from typing import List
from models import Question

def save_wrong_questions(file_path: str, wrong_qs: List[Question]) -> None:
    """把错题列表保存为 JSON（后缀 .json）"""
    data = [q.__dict__ for q in wrong_qs]
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_wrong_questions(file_path: str) -> List[Question]:
    """从 JSON 文件加载错题，返回 Question 对象列表"""
    with open(file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Question(**item) for item in raw]
