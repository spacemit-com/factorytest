from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QFrame,
    QVBoxLayout,
    QGroupBox,
    QLabel,
    QStatusBar,
    QPushButton,
    QGridLayout
)

import threading

from cricket.lang import SimpleLang

class SimpleManualTestWindow(SimpleLang):
    def __init__(self, test_routine, stop_routine, languages) -> None:
        super().__init__()

        self.test_routine = test_routine
        self.stop_routine = stop_routine
        self.languages = languages

        self.app = QApplication([])

        self.window = QMainWindow()
        self.window.setWindowTitle(self._get_text('title'))
        self.window.setWindowFlags(Qt.WindowStaysOnTopHint)

        # Main content
        content = QFrame(self.window)
        content_layout = QVBoxLayout(content)

        # Test step
        box = QGroupBox(self.get_text('test_step'), content)
        box_layout = QVBoxLayout(box)

        label = QLabel(self._get_text('test_step'), box)
        box_layout.addWidget(label)

        content_layout.addWidget(box)

        # Status
        self.status = QStatusBar(content)
        self.status.showMessage('Not running')
        content_layout.addWidget(self.status)

        # Toolbar
        toolbar = QFrame(content)
        toolbar_layout = QGridLayout(toolbar)

        self.start_button = QPushButton(self.get_text('start_button'), toolbar)
        self.start_button.clicked.connect(self.cmd_start)
        self.start_button.setFocus()
        toolbar_layout.addWidget(self.start_button, 0, 0)

        self.stop_button = QPushButton(self.get_text('stop_button'), toolbar)
        self.stop_button.setDisabled(True)
        self.stop_button.clicked.connect(self.cmd_stop)
        toolbar_layout.addWidget(self.stop_button, 0, 1)

        self.pass_button = QPushButton(self.get_text('pass_button'), toolbar)
        self.pass_button.setDisabled(True)
        self.pass_button.clicked.connect(self.cmd_pass)
        toolbar_layout.addWidget(self.pass_button, 0, 2)

        self.fail_button = QPushButton(self.get_text('fail_button'), toolbar)
        self.fail_button.setDisabled(True)
        self.fail_button.clicked.connect(self.cmd_fail)
        toolbar_layout.addWidget(self.fail_button, 0, 3)

        content_layout.addWidget(toolbar)

        self.window.setCentralWidget(content)

        # Move to center
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            window_geometry = self.window.geometry()
            x = (screen_geometry.width() - window_geometry.width()) // 2
            y = (screen_geometry.height() - window_geometry.height()) // 2
            self.window.move(x, y)

        self.window.show()

        self.result = False

    def _get_text(self, key):
        if self.languages:
            lang = self.languages.get(self.current_lang)
            if lang is not None:
                text = lang.get(key)
                if text is not None:
                    return text

        return 'Undefined'

    def cmd_start(self):
        self.status.showMessage('Running...')
        self.start_button.setDisabled(True)
        self.thread = threading.Thread(target=self.test_routine)
        self.thread.start()
        self.stop_button.setDisabled(False)
        self.pass_button.setDisabled(False)
        self.fail_button.setDisabled(False)

    def cmd_stop(self):
        self.status.showMessage('Stopping...')
        self.stop_button.setDisabled(True)
        self.stop_routine()
        self.thread.join()
        self.start_button.setDisabled(True)
        self.status.showMessage('Stopped')

    def cmd_pass(self):
        self.status.showMessage('Stopping...')
        self.stop_routine()
        self.thread.join()
        self.result = True
        self.app.quit()

    def cmd_fail(self):
        self.status.showMessage('Stopping...')
        self.stop_routine()
        self.thread.join()
        self.result = False
        self.app.quit()

    def determine(self):
        self.app.exec_()
        return self.result
