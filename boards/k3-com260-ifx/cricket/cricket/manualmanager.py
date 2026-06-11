from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSpacerItem, QSizePolicy
from cricket.macro import *


class ManualResultManager(QWidget):
    def __init__(self, mainwindow, save_file_manager):
        super().__init__(mainwindow)
        self.mainwindow = mainwindow
        self.manual_save_file_manager = save_file_manager
        self.status_list = []

    def append_pass_and_fail_btn(self, column_0_text, column_1_text):
        """Creates a widget with Pass and Fail buttons for a manual test item"""
        widget = QWidget(self)
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)

        pass_btn = QPushButton("通过", widget)
        pass_btn.setFixedWidth(130)
        pass_btn.setFixedHeight(30)
        pass_btn.setStyleSheet("background-color: white; text-align: center;")
        layout.addWidget(pass_btn)

        spacer = QSpacerItem(10, 32, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addSpacerItem(spacer)

        fail_btn = QPushButton("失败", widget)
        fail_btn.setFixedWidth(130)
        fail_btn.setFixedHeight(30)
        fail_btn.setStyleSheet("background-color: white; text-align: center;")
        layout.addWidget(fail_btn)

        self.status_list.append([column_0_text, column_1_text, pass_btn, fail_btn])
        return widget

    def setup_slot_connection(self):
        """Connects button click signals to handler methods"""
        for column_0_text, column_1_text, pass_btn, fail_btn in self.status_list:
            pass_btn.clicked.connect(
                lambda checked, c0=column_0_text, b1=pass_btn, b2=fail_btn:
                self.on_pass_btn_clicked(c0, b1, b2)
            )
            fail_btn.clicked.connect(
                lambda checked, c0=column_0_text, b1=pass_btn, b2=fail_btn:
                self.on_fail_btn_clicked(c0, b1, b2)
            )
            self.manual_save_file_manager.update_manual_test_status(column_0_text, INITSTR)

    def on_pass_btn_clicked(self, column_0_text, btn1, btn2):
        btn1.setStyleSheet(f"background-color: {PASS_COLOR}")
        btn2.setStyleSheet("background-color: white")
        self.manual_save_file_manager.update_manual_test_status(column_0_text, PASSSTR)

    def on_fail_btn_clicked(self, column_0_text, btn1, btn2):
        btn1.setStyleSheet("background-color: white")
        btn2.setStyleSheet(f"background-color: {FAIL_COLOR}")
        self.manual_save_file_manager.update_manual_test_status(column_0_text, FAILSTR)

    def reset_check_status(self):
        for column_0_text, column_1_text, pass_btn, fail_btn in self.status_list:
            pass_btn.setStyleSheet("background-color: white")
            fail_btn.setStyleSheet("background-color: white")
