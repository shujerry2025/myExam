# main.py
import sys
import random
from pathlib import Path
from typing import List, Dict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QComboBox,
    QCheckBox, QGroupBox, QRadioButton, QButtonGroup
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from models import Question
from parser import parse_docx
from utils import save_wrong_questions, load_wrong_questions


class QuestionBank:
    """管理多个题库（库名 → Question 列表）"""
    def __init__(self):
        self.banks: Dict[str, List[Question]] = {}

    def add_bank(self, name: str, path: str):
        qs = parse_docx(path)
        self.banks[name] = qs

    def get_all(self) -> List[Question]:
        all_q = []
        for qs in self.banks.values():
            all_q.extend(qs)
        return all_q

    def get_by_name(self, name: str) -> List[Question]:
        return self.banks.get(name, [])


class BrushApp(QMainWindow):
    # 设计稿基准尺寸与字号
    BASE_WIDTH = 800
    BASE_HEIGHT = 600
    BASE_FONT = 12          # pt

    def __init__(self):
        super().__init__()
        self.setWindowTitle("刷题小软件")
        self.resize(self.BASE_WIDTH, self.BASE_HEIGHT)

        # ----------------- 数据 -----------------
        self.bank = QuestionBank()
        self.current_questions: List[Question] = []   # 本轮题目顺序
        self.current_index: int = 0
        self.wrong_questions: List[Question] = []    # 本轮错题
        self.correct_cnt: int = 0

        # ----------------- UI -----------------
        self._init_ui()
        self._apply_style()
        self.adjust_ui_scaling()      # 首次根据基准尺寸设置字体

    # -------------------------------------------------
    # 窗口大小变化时自动重新计算 UI 缩放
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_ui_scaling()

    def adjust_ui_scaling(self):
        """根据当前窗口尺寸动态调整字体、按钮高度等 UI 元素"""
        w_factor = self.width()  / self.BASE_WIDTH
        h_factor = self.height() / self.BASE_HEIGHT
        factor = min(w_factor, h_factor)          # 取较小者防止字体过大

        # ---------- 字体 ----------
        new_pt = max(8, int(self.BASE_FONT * factor))   # 最小 8pt
        font = QFont()
        font.setPointSize(new_pt)
        self.current_font_size = new_pt  # 记录当前字号，供富文本和弹窗用

        # 为所有需要同步的控件统一设定字体
        self.lbl_progress.setFont(font)
        self.lbl_question.setFont(font)
        self.lbl_feedback.setFont(font)
        self.cb_bank.setFont(font)
        self.cb_mode.setFont(font)
        self.chk_wrong.setFont(font)
        self.btn_upload.setFont(font)
        self.btn_start.setFont(font)
        self.btn_submit.setFont(font)
        self.btn_next.setFont(font)
        self.btn_save_wrong.setFont(font)
        self.btn_finish.setFont(font)
        for rb in self.opt_radios:
            rb.setFont(font)
            # 动态同步选项字号
            rb.setStyleSheet(f"font-size: {new_pt}pt; padding: 6px 12px;")

        # ---------- 按钮高度 ----------
        btn_h = max(24, int(30 * factor))
        for btn in (self.btn_upload, self.btn_start, self.btn_submit,
                    self.btn_next, self.btn_save_wrong, self.btn_finish):
            btn.setMinimumHeight(btn_h)

        # ---------- 选项框高度 ----------
        self.opt_box.setMinimumHeight(btn_h * len(self.opt_radios))

        # 触发布局刷新
        self.update()

    # -------------------------------------------------
    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(32, 24, 32, 24)  # 增加边距
        main_layout.setSpacing(18)
        central.setLayout(main_layout)

        # ---------- 顶部控制 ----------
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)
        main_layout.addLayout(top_layout)

        self.btn_upload = QPushButton("上传题库")
        self.btn_upload.setMinimumWidth(120)
        self.btn_upload.clicked.connect(self.upload_bank)
        top_layout.addWidget(self.btn_upload)

        self.cb_bank = QComboBox()
        self.cb_bank.addItem("全部题库")
        self.cb_bank.setMinimumWidth(140)
        top_layout.addWidget(self.cb_bank)

        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["按库顺序刷题", "全部随机刷题"])
        self.cb_mode.setMinimumWidth(140)
        top_layout.addWidget(self.cb_mode)

        self.chk_wrong = QCheckBox("刷错题模式")
        top_layout.addWidget(self.chk_wrong)

        self.btn_start = QPushButton("开始刷题")
        self.btn_start.setMinimumWidth(120)
        self.btn_start.clicked.connect(self.start_practice)
        top_layout.addWidget(self.btn_start)

        # ---------- 题目展示 ----------
        self.lbl_progress = QLabel("")
        self.lbl_progress.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.lbl_progress)

        self.lbl_question = QLabel("")
        self.lbl_question.setWordWrap(True)
        self.lbl_question.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_question.setMinimumHeight(60)
        main_layout.addWidget(self.lbl_question)

        # ---------- 选项 ----------
        self.opt_group = QButtonGroup()
        self.opt_box = QGroupBox("选项")
        opt_layout = QVBoxLayout()
        opt_layout.setSpacing(10)
        self.opt_box.setLayout(opt_layout)
        self.opt_radios: List[QRadioButton] = []
        for i in range(4):      # 默认最多四个选项；如有更多可自行扩展
            rb = QRadioButton("")
            rb.setMinimumHeight(32)
            # 选项字号与主字号保持一致
            rb.setStyleSheet(f"font-size: {self.BASE_FONT}pt; padding: 6px 12px;")
            self.opt_radios.append(rb)
            self.opt_group.addButton(rb, i)
            opt_layout.addWidget(rb)
        main_layout.addWidget(self.opt_box)

        # ---------- 按钮区 ----------
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        main_layout.addLayout(btn_row)

        self.btn_submit = QPushButton("提交答案")
        self.btn_submit.setMinimumWidth(120)
        self.btn_submit.clicked.connect(self.check_answer)
        btn_row.addWidget(self.btn_submit)

        self.btn_next = QPushButton("下一题")
        self.btn_next.setMinimumWidth(120)
        self.btn_next.clicked.connect(self.next_question)
        self.btn_next.setEnabled(False)
        btn_row.addWidget(self.btn_next)

        self.btn_save_wrong = QPushButton("保存错题")
        self.btn_save_wrong.setMinimumWidth(120)
        self.btn_save_wrong.clicked.connect(self.save_current_wrong)
        self.btn_save_wrong.setEnabled(False)
        btn_row.addWidget(self.btn_save_wrong)

        self.btn_finish = QPushButton("结束刷题")
        self.btn_finish.setMinimumWidth(120)
        self.btn_finish.clicked.connect(self.finish_practice)
        btn_row.addWidget(self.btn_finish)

        # ---------- 反馈 ----------
        self.lbl_feedback = QLabel("")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_feedback.setMinimumHeight(40)
        main_layout.addWidget(self.lbl_feedback)

    # -------------------------------------------------
    def _apply_style(self):
        """统一的现代化浅暗色 Fusion 主题 + QSS美化"""
        QApplication.setStyle("Fusion")
        dark_bg = "#23272e"  # 更深色背景
        card_bg = "#2b2f38"  # 卡片色块
        accent = "#5a9bd4"   # 按钮主色
        accent_hover = "#7fb0e2"
        border_radius = 8
        self.setStyleSheet(f"""
            QWidget {{ background-color: {dark_bg}; color: #f0f0f0; }}
            QGroupBox {{
                background-color: {card_bg};
                border-radius: {border_radius}px;
                margin-top: 12px;
                padding: 12px;
                font-size: 16px;
                border: 1px solid #444;
            }}
            QLabel {{ font-size: 18px; line-height: 1.6; }}
            QComboBox, QCheckBox {{ font-size: 16px; }}
            QPushButton {{
                background-color: {accent};
                color: #fff;
                border: none;
                padding: 10px 20px;
                border-radius: {border_radius}px;
                font-size: 17px;
                font-weight: 500;
                margin: 4px;
            }}
            QPushButton:hover {{ background-color: {accent_hover}; }}
            QPushButton:disabled {{ background-color: #444; color: #aaa; }}
        """)

    # -------------------------------------------------
    # ---- 上传题库 ----
    def upload_bank(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择 Word 题库文件", "", "Word 文档 (*.docx)"
        )
        if not files:
            return
        for f in files:
            name = Path(f).stem
            try:
                self.bank.add_bank(name, f)
                self.cb_bank.addItem(name)
                QMessageBox.information(self, "成功", f"已加载题库《{name}》")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载《{name}》时出错:\n{e}")

    # -------------------------------------------------
    # ---- 开始刷题 ----
    def start_practice(self):
        if self.chk_wrong.isChecked():
            # 刷错题模式
            f, _ = QFileDialog.getOpenFileName(
                self, "加载错题库", "", "JSON 文件 (*.json)"
            )
            if not f:
                return
            try:
                self.current_questions = load_wrong_questions(f)
                if not self.current_questions:
                    QMessageBox.information(self, "提示", "错题库为空，无法开始刷题。")
                    return
                self.setWindowTitle(f"刷题小软件 - 刷错题（{Path(f).name}）")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载错题库失败:\n{e}")
                return
        else:
            # 正常刷题
            mode = self.cb_mode.currentText()
            if self.cb_bank.currentText() == "全部题库":
                all_qs = self.bank.get_all()
            else:
                all_qs = self.bank.get_by_name(self.cb_bank.currentText())
            if not all_qs:
                QMessageBox.warning(self, "提示", "当前没有可用的题目，请先上传题库。")
                return
            if mode == "按库顺序刷题":
                self.current_questions = all_qs[:]
            else:   # 随机刷题
                self.current_questions = all_qs[:]
                random.shuffle(self.current_questions)

        # 初始化状态
        self.current_index = 0
        self.wrong_questions.clear()
        self.correct_cnt = 0
        self.btn_next.setEnabled(False)
        self.btn_save_wrong.setEnabled(False)
        self.lbl_feedback.clear()
        self.show_current_question()

    # -------------------------------------------------
    # ---- 展示当前题目 ----
    def show_current_question(self):
        if self.current_index >= len(self.current_questions):
            self.finish_practice()
            return

        q = self.current_questions[self.current_index]
        self.lbl_progress.setText(f"第 {self.current_index + 1}/{len(self.current_questions)} 题")
        # 用 HTML 设置题目字号
        self.lbl_question.setText(f'<span style="font-size:{self.current_font_size}pt">{q.id}. {q.content}</span>')

        # 隐藏所有选项，随后只显示实际存在的
        for rb in self.opt_radios:
            rb.hide()
            rb.setChecked(False)

        for i, opt in enumerate(q.options):
            if i < len(self.opt_radios):
                self.opt_radios[i].setText(opt)
                self.opt_radios[i].show()

        # 重置按钮状态
        self.btn_submit.setEnabled(True)
        self.btn_next.setEnabled(False)
        self.btn_save_wrong.setEnabled(False)
        self.lbl_feedback.clear()

    # -------------------------------------------------
    # ---- 检查答案 ----
    def check_answer(self):
        selected_id = self.opt_group.checkedId()
        if selected_id == -1:
            QMessageBox.warning(self, "提示", "请先选择一个选项！")
            return

        selected_letter = chr(ord('A') + selected_id)   # 0->A,1->B...
        q = self.current_questions[self.current_index]
        is_correct = selected_letter.upper() in q.answer.upper()

        if is_correct:
            self.lbl_feedback.setStyleSheet("color: #5cb85c;")
            feedback = f'<span style="font-size:{self.current_font_size}pt">✅ 正确！<br>解析：{q.explanation}</span>'
            self.correct_cnt += 1
        else:
            self.lbl_feedback.setStyleSheet("color: #d9534f;")
            feedback = (f'<span style="font-size:{self.current_font_size}pt">❌ 错误！正确答案：{q.answer}<br>'
                        f'解析：{q.explanation}</span>')
            # 记录错题
            self.wrong_questions.append(q)

        self.lbl_feedback.setText(feedback)

        # 按钮切换
        self.btn_submit.setEnabled(False)
        self.btn_next.setEnabled(True)
        self.btn_save_wrong.setEnabled(True)

    # -------------------------------------------------
    # ---- 保存当前错题（单题）----
    def save_current_wrong(self):
        if not self.wrong_questions:
            QMessageBox.information(self, "提示", "暂无错题需要保存。")
            return
        f, _ = QFileDialog.getSaveFileName(
            self, "保存错题库", "错题库.json", "JSON 文件 (*.json)"
        )
        if not f:
            return
        try:
            save_wrong_questions(f, self.wrong_questions)
            QMessageBox.information(self, "成功", f"错题已保存至 {f}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败:\n{e}")

    # -------------------------------------------------
    # ---- 下一题 ----
    def next_question(self):
        self.current_index += 1
        self.show_current_question()

    # -------------------------------------------------
    # ---- 结束刷题 ----
    def finish_practice(self):
        total = len(self.current_questions)
        if total == 0:
            return
        accuracy = self.correct_cnt / total * 100
        msg = (f"本轮共完成 {total} 题，正确 {self.correct_cnt} 题，"
               f"正确率 {accuracy:.2f}%<br>")
        if self.wrong_questions:
            msg += f"错题数量：{len(self.wrong_questions)}<br>是否将错题保存到本地？"
        else:
            msg += "恭喜！没有错题 🎉"
        # 用 HTML 设置弹窗字号
        reply = QMessageBox.question(
            self, "刷题结束",
            f'<span style="font-size:{self.current_font_size}pt">{msg}</span>',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if reply == QMessageBox.Yes and self.wrong_questions:
            f, _ = QFileDialog.getSaveFileName(
                self, "保存错题库", "错题库.json", "JSON 文件 (*.json)"
            )
            if f:
                try:
                    save_wrong_questions(f, self.wrong_questions)
                    QMessageBox.information(self, "已保存", f"错题库已保存至 {f}")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"保存错题库失败:\n{e}")

        # ----------- 重置 UI ----------
        self.lbl_progress.setText("")
        self.lbl_question.setText("")
        self.lbl_feedback.setText("")
        for rb in self.opt_radios:
            rb.hide()
        self.btn_submit.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.btn_save_wrong.setEnabled(False)

def main():
    app = QApplication(sys.argv)
    window = BrushApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
