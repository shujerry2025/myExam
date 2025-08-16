# models.py
from dataclasses import dataclass, field
from typing import List

@dataclass
class Question:
    """单个选择题的数据结构"""
    id: str                     # 题号或唯一标识
    content: str                # 题干（可包含换行）
    options: List[str]          # 选项列表，如 ["A. xxx", "B. yyy", ...]
    answer: str                 # 正确答案字母，如 "B"（支持多答案 "AB"）
    explanation: str = ""       # 解析或答案说明
