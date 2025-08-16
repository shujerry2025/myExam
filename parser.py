# parser.py
import re
from typing import List
from docx import Document
from models import Question


def _clean(txt: str) -> str:
    return txt.strip()


def parse_docx(file_path: str) -> List[Question]:
    """
    兼容：
      1. “A. 选项”  → 有点
      2. “A、选项”  → 中文顿号
      3. “A 选项”   → **不带点**（本次需求）
    """
    doc = Document(file_path)
    questions: List[Question] = []
    cur = None

    # 题号：只匹配 “数字+英文/全角句点”
    q_pat = re.compile(r'^(\d+)[\.\．]\s*(.*)')

    # 选项：A‑D 开头，后面可以是 “.”、“、” 或直接空格（即 A 选项）
    #   捕获字母和后面的正文，正文允许出现任意字符（包括中文标点、数字等）
    opt_pat = re.compile(r'^([ABCD])(?:[\.、]|\s)\s*(.*)')

    # 正确答案（可带前置破折号）
    ans_pat = re.compile(r'^(?:—{2,}\s*)?正确答案[:：]\s*([A-D]+)')

    # 解析（可带前置破折号）
    expl_pat = re.compile(r'^(?:—{2,}\s*)?答案解析[:：]\s*(.*)')

    for para in doc.paragraphs:
        txt = _clean(para.text)
        if not txt:
            continue

        # ---------- 1. 题号 ----------
        m_q = q_pat.match(txt)
        if m_q:
            if cur:
                questions.append(Question(**cur))
            cur = {
                "id": m_q.group(1),
                "content": m_q.group(2).strip(),
                "options": [],
                "answer": "",
                "explanation": ""
            }
            continue

        # 题目尚未开始时直接忽略
        if cur is None:
            continue

        # ---------- 2. 选项 ----------
        m_opt = opt_pat.match(txt)
        if m_opt:
            # 统一存为 “A. 选项正文”
            cur["options"].append(f"{m_opt.group(1)}. {m_opt.group(2).strip()}")
            continue

        # ---------- 3. 正确答案 ----------
        m_ans = ans_pat.match(txt)
        if m_ans:
            cur["answer"] = m_ans.group(1).strip()
            continue

        # ---------- 4. 解析 ----------
        m_expl = expl_pat.match(txt)
        if m_expl:
            cur["explanation"] = m_expl.group(1).strip()
            continue

        # ---------- 5. 其余行 ----------
        if not cur["answer"]:            # 仍在题干阶段 → 归入题干
            cur["content"] += "\n" + txt
        else:                           # 已出现答案，全部归入解释（防止 “1、2、…” 被误判）
            if not cur["explanation"]:
                cur["explanation"] = txt
            else:
                cur["explanation"] += "\n" + txt

    # 最后一题
    if cur:
        questions.append(Question(**cur))

    return questions
