"""A module containing a visual representation of the testModule.

This is the "View" of the MVC world.
"""

from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QColor, QPixmap, QImage, QPalette
from PyQt5.QtWidgets import (
    QMainWindow,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QCheckBox,
    QComboBox,
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QGroupBox,
    QTableWidget,
    QAbstractItemView,
    QStatusBar,
    QTableWidgetItem,
    QHeaderView,
    QSlider
)


import qrcode
from PIL import ImageQt

import os
import time
import threading
import subprocess
import re
from datetime import datetime
from importlib import import_module

from cricket.model import TestMethod, TestCase, TestModule
from cricket.executor import Executor
from cricket.lang import SimpleLang
from cricket.macro import *
from cricket.statusview import StatusView
from cricket.peripheraltestview import PeripheralTestWindow
from cricket.wifimacview import WifiMacView
from cricket.loggermanager import LoggerManager as _LM, save_dmesg_to_log, update_log_filename
from cricket.testlogmanager import DeviceStatusManager
from cricket.manualmanager import ManualResultManager

_logger = _LM(name='MainWindow').get_logger()


class MainWindow(QMainWindow):
    def __init__(self, root):
        super().__init__()
        self.sl = SimpleLang()
        self._project = None
        self.test_table = {}
        self.test_list = {}
        self.run_status = {}
        self.executor = {}

        self.usb_list = []

        self.set_brightness()

        self.wifi_mac_Ok = False

        # Save-file manager (CSV + time-sync state)
        self._save_file_manager = DeviceStatusManager()
        self.manual_res_manager = ManualResultManager(self, save_file_manager=self._save_file_manager)

        self.root = root
        self.setWindowTitle(self.sl.get_text('title'))
        # self.showFullScreen()

        self.font_size = 14

        # Set up the main content for the window.
        self._setup_main_content()

        self.peripheral_test_view = PeripheralTestWindow(self)

        # Set up listeners for runner events.
        Executor.bind('test_status_update', self.on_executorStatusUpdate)
        Executor.bind('test_start', self.on_executorTestStart)
        Executor.bind('test_end', self.on_executorTestEnd)
        Executor.bind('suite_end', self.on_executorSuiteEnd)
        Executor.bind('suite_error', self.on_executorSuiteError)

    ######################################################
    # Internal GUI layout methods.
    ######################################################

    def _setup_main_content(self):
        '''
        The button toolbar runs as a horizontal area at the top of the GUI.
        It is a persistent GUI component
        '''

        self.setStyleSheet(f'font-size: {self.font_size}px;')

        self.content = QFrame(self)
        self.content_layout = QVBoxLayout(self.content)

        # Information
        self._setup_info()

        # toolbar
        toolbar = QFrame(self.content)
        layout = QGridLayout(toolbar)

        self.run_all_button = QPushButton(self.sl.get_text('run_all_button'), toolbar)
        self.run_all_button.clicked.connect(self.cmd_run_all)
        self.run_all_button.setFocus()
        layout.addWidget(self.run_all_button, 0, 0)

        self.run_selected_button = QPushButton(self.sl.get_text('run_selected_button'),
                                               toolbar)
        self.run_selected_button.setDisabled(True)
        self.run_selected_button.clicked.connect(self.cmd_run_selected)
        layout.addWidget(self.run_selected_button, 0, 1)

        self.stop_button = QPushButton(self.sl.get_text('stop_button'), toolbar)
        self.stop_button.setDisabled(True)
        self.stop_button.clicked.connect(self.cmd_stop)
        layout.addWidget(self.stop_button, 0 , 2)

        self.reboot_button = QPushButton(self.sl.get_text('reboot_button'), toolbar)
        self.reboot_button.clicked.connect(self.cmd_reboot)
        layout.addWidget(self.reboot_button, 0, 3)

        self.poweroff_button = QPushButton(self.sl.get_text('poweroff_button'), toolbar)
        self.poweroff_button.clicked.connect(self.cmd_poweroff)
        layout.addWidget(self.poweroff_button, 0, 4)

        # Save / clear test results
        self.save_test_button = QPushButton(self.sl.get_text('save_test_results'), toolbar)
        self.save_test_button.clicked.connect(self.cmd_save_test)
        self.save_test_button.setEnabled(False)
        layout.addWidget(self.save_test_button, 0, 5)

        self.clear_test_button = QPushButton(self.sl.get_text('clear_test_results'), toolbar)
        self.clear_test_button.clicked.connect(self.cmd_clear_test)
        layout.addWidget(self.clear_test_button, 0, 6)

        self.content_layout.addWidget(toolbar)

        # tests
        # -------------------
        # |        |        |
        # | auto   | camera |
        # |        |        |
        # -------------------
        # | manual | others |
        # |        |        |
        # -------------------
        self.tests = QFrame(self.content)
        self.tests_layout = QGridLayout(self.tests)

        self._setup_test_table('auto', 0, 0, 5, 1)
        self._setup_usb_frame(5, 0, 1, 1)
        self._setup_test_table('manual', 6, 0, 4, 1)

        camera_box = QGroupBox(self.sl.get_text('camera'), self.tests)
        camera_box_layout = QVBoxLayout(camera_box)

        # Camera test table (auto_camera module)
        self._setup_camera_test_table(camera_box_layout)

        # others
        self._setup_others()

        self.tests_layout.addWidget(camera_box, 0, 1, 6, 1)
        self.tests_layout.addWidget(self.others_box, 6, 1, 4, 1)

        self.tests_layout.setRowStretch(0, 6)
        self.tests_layout.setRowStretch(1, 6)
        self.tests_layout.setRowStretch(2, 6)
        self.tests_layout.setRowStretch(3, 6)
        self.tests_layout.setRowStretch(4, 6)
        self.tests_layout.setRowStretch(5, 6)

        self.tests_layout.setRowStretch(6, 4)
        self.tests_layout.setRowStretch(7, 4)
        self.tests_layout.setRowStretch(8, 4)
        self.tests_layout.setRowStretch(9, 4)

        self.tests_layout.setColumnStretch(0, 1)
        self.tests_layout.setColumnStretch(1, 1)

        self.content_layout.addWidget(self.tests)

        # set main content to window
        self.setCentralWidget(self.content)

    def _setup_info(self):
        info = QFrame(self.content)
        info_layout = QGridLayout(info)

        cpu_model = QLabel(f'{self.sl.get_text("cpu_model")}: {self._get_CPU_model()}', info)
        info_layout.addWidget(cpu_model, 0, 0)

        cpu_freq = QLabel(f'{self.sl.get_text("cpu_freq")}: {self._get_CPU_freq()} GHz', info)
        info_layout.addWidget(cpu_freq, 0, 1)

        self.cpu_temp = QLabel(f'{self.sl.get_text("cpu_temp")}: {self._get_CPU_Temp()} °C', info)
        self._cpu_temp_timer = QTimer(self)
        self._cpu_temp_timer.timeout.connect(self.on_cpuTempUpdate)
        self._cpu_temp_timer.start(1000)
        info_layout.addWidget(self.cpu_temp, 0, 2)

        ddr_size = QLabel(f'{self.sl.get_text("ddr_size")}: {self._get_DDR_size()} GB', info)
        info_layout.addWidget(ddr_size, 0, 3)

        ufs_size = QLabel(f'{self.sl.get_text("ufs_size")}: {self._get_UFS_size()} GB', info)
        info_layout.addWidget(ufs_size, 0, 4)

        ssd_size = QLabel(f'{self.sl.get_text("ssd_size")}: {self._get_SSD_size()} GB', info)
        info_layout.addWidget(ssd_size, 0, 5)

        sd_size = QLabel(f'{self.sl.get_text("tf_size")}: {self._get_TF_size()} GB', info)
        info_layout.addWidget(sd_size, 0, 6)

        product_name = QLabel(f'{self.sl.get_text("product_name")}: {self._get_product_name()}', info)
        info_layout.addWidget(product_name, 0, 7)

        fw_version = QLabel(f'{self.sl.get_text("fw_version")}: {self._get_fw_version()}', info)
        info_layout.addWidget(fw_version, 0, 8)

        # Current time label (updated when ethernet is up)
        self.current_time_label = QLabel(
            f'   {self.sl.get_text("current_time")}: --', info)
        info_layout.addWidget(self.current_time_label, 0, 9)

        # Ethernet IP label
        self.eth_ip_label = QLabel(
            f'   {self.sl.get_text("eth_ip")}: --', info)
        info_layout.addWidget(self.eth_ip_label, 0, 10)

        self.content_layout.addWidget(info)

        # Write static device info into CSV results['info']
        for label in [cpu_model, cpu_freq, ddr_size, ufs_size, ssd_size, sd_size,
                      product_name, fw_version]:
            try:
                key, value = label.text().split(':', 1)
                self._save_file_manager.update_info_test_status(key.strip(), value.strip())
            except Exception:
                pass
        # CPU temp is dynamic — also write initial value, updated in on_cpuTempUpdate
        try:
            key, value = self.cpu_temp.text().split(':', 1)
            self._save_file_manager.update_info_test_status(key.strip(), value.strip())
        except Exception:
            pass

        # Start ethernet + time-sync polling loop (after ETH test passes)
        self._eth_interface = self._get_detected_eth_interface()
        self._eth_sync_started = False

    def _setup_test_table(self, name, row, column, row_span, column_span):
        module = import_module(name)

        box = QGroupBox(module.MODULE_NAME[self.sl.current_lang], self.tests)
        box.setStyleSheet("QGroupBox::title { font-weight: bold; }")
        layout = QVBoxLayout(box)

        columns = self.sl.get_text('test_table_head')

        table = QTableWidget(box)
        table.setStyleSheet('QTableWidget { background-color: black; color: white; }')
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        for i in range(len(columns)):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        table.verticalHeader().setStyleSheet('QHeaderView::section { width: 32px; }')
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.itemSelectionChanged.connect(self.on_testMethodSelected)
        layout.addWidget(table)
        self.test_table[name] = table

        status = QStatusBar(box)
        status.showMessage('Not running')
        layout.addWidget(status)
        self.run_status[name] = status

        self.tests_layout.addWidget(box, row, column, row_span, column_span)

    def _setup_camera_test_table(self, parent_layout):
        columns = self.sl.get_text('test_table_head')

        table = QTableWidget()
        table.setStyleSheet('QTableWidget { background-color: black; color: white; }')
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        for i in range(len(columns)):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        table.verticalHeader().setStyleSheet('QHeaderView::section { width: 32px; }')
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.itemSelectionChanged.connect(self.on_testMethodSelected)
        parent_layout.addWidget(table)
        self.test_table['auto_camera'] = table

        status = QStatusBar()
        status.showMessage('Not running')
        parent_layout.addWidget(status)
        self.run_status['auto_camera'] = status

    def _setup_others(self):
        self.others_box = QGroupBox(self.sl.get_text('others'), self.tests)
        self.others_box_layout = QVBoxLayout(self.others_box)

        # Comment the code below if you don't need it

        # item
        self._setup_others_item()

        # status
        self._setup_others_status()

    def _setup_others_item(self):
        self.others_item = QFrame(self.others_box)
        self.others_item_layout = QHBoxLayout(self.others_item)
        self.others_box_layout.addWidget(self.others_item)

        self._setup_others_test()

        self.wifi_mac_view = WifiMacView(self.others_item)
        self.wifi_mac_view.setFixedWidth(200)
        self.others_item_layout.addWidget(self.wifi_mac_view)

        sn = self._get_sn()
        if sn:
            sn_clean = str(sn).replace('\x00', '')
            self._save_file_manager.serial_number = sn_clean
            self._save_file_manager.update_sn_test_status(self.sl.get_text('sn'), sn_clean)
            self._setup_sn_qrcode(sn)
            update_log_filename(sn_clean)
        else:
            self._save_file_manager.update_sn_test_status(self.sl.get_text('sn'), 'FAIL')

        self.others_item_layout.addStretch()

    def _setup_others_test(self):
        others_test = QFrame(self.others_item)
        others_test_layout = QVBoxLayout(others_test)

        # peripheral test
        peripheral_frame = QFrame(others_test)
        peripheral_frame.setAutoFillBackground(True)
        peripheral_frame.setPalette(QPalette(QColor('darkgray')))
        peripheral_layout = QHBoxLayout(peripheral_frame)
        self.peripheral_test_button = QPushButton(self.sl.get_text('peripheral_test'), peripheral_frame)
        self.peripheral_test_button.setAutoFillBackground(True)
        self.peripheral_test_button.clicked.connect(self.cmd_peripheral_test)
        peripheral_layout.addWidget(self.peripheral_test_button)
        others_test_layout.addWidget(peripheral_frame)

        # aging test
        aging_test = QFrame(others_test)
        aging_test.setAutoFillBackground(True)
        aging_test.setPalette(QPalette(QColor('darkgray')))
        aging_test_layout = QVBoxLayout(aging_test)

        self.aging_button = QPushButton(self.sl.get_text('aging_test'), aging_test)
        self.aging_button.setAutoFillBackground(True)
        self.aging_button.clicked.connect(self.cmd_aging)
        aging_test_layout.addWidget(self.aging_button)

        aging_item = QFrame(aging_test)
        aging_item_layout = QHBoxLayout(aging_item)
        self.cpu_aging = QCheckBox('CPU', aging_item)
        self.cpu_aging.setChecked(True)
        aging_item_layout.addWidget(self.cpu_aging)
        self.ddr_aging = QCheckBox('DDR', aging_item)
        self.ddr_aging.setChecked(True)
        aging_item_layout.addWidget(self.ddr_aging)
        self.gpu_aging = QCheckBox('GPU', aging_item)
        self.gpu_aging.setChecked(True)
        aging_item_layout.addWidget(self.gpu_aging)
        self.vpu_aging = QCheckBox('VPU', aging_item)
        self.vpu_aging.setChecked(True)
        aging_item_layout.addWidget(self.vpu_aging)
        self.ai_cpu_aging = QCheckBox('AI-CPU', aging_item)
        self.ai_cpu_aging.setChecked(True)
        aging_item_layout.addWidget(self.ai_cpu_aging)
        aging_test_layout.addWidget(aging_item)

        aging_duration = QFrame(aging_test)
        aging_duration_layout = QHBoxLayout(aging_duration)
        aging_duration_label = QLabel(f'{self.sl.get_text("aging_duration")}: ', aging_duration)
        aging_duration_layout.addWidget(aging_duration_label)
        self.aging_duration_choice = QComboBox(aging_test)
        self.aging_duration_choice.addItems(['4', '8', '12', '24'])
        self.aging_duration_choice.setCurrentText('8')
        aging_duration_layout.addWidget(self.aging_duration_choice)
        aging_test_layout.addWidget(aging_duration)

        others_test_layout.addWidget(aging_test)

        self.others_item_layout.addWidget(others_test)


    # wifi signal part
    def _setup_others_status(self):

        self.others_status_view = StatusView(self.others_box)
        self.others_box_layout.addWidget(self.others_status_view)

    # [start] Check the usb to see if the device is inserted
    def usb_loop(self, label, usb_path):
        while True:
            if os.path.exists(usb_path):
                label.setPalette(QPalette(QColor(PASS_COLOR)))
            else:
                label.setPalette(QPalette(QColor(255, 255,255)))

            time.sleep(1)

    def _add_usb_test(self, text: str, row: int, column: int, path: str):
        label = QLabel(text, self.usb_frame)
        label.setAutoFillBackground(True)
        label.setPalette(QPalette(QColor('white')))
        label.setAlignment(Qt.AlignCenter)
        self.usb_frame_layout.addWidget(label, row, column)
        self.usb_list.append(label)

        thread = threading.Thread(target=self.usb_loop, args=(label, path))
        thread.start()

    def _setup_usb_frame(self, row, column, row_span, column_span):
        self.usb_frame = QFrame(self.tests)
        self.usb_frame_layout = QGridLayout(self.usb_frame)

        self._add_usb_test('USB A口 (左上) 2.0', 0, 0,
                           '/sys/bus/usb/devices/usb2/2-1/2-1.4/product')
        self._add_usb_test('USB A口 (左上) 3.0', 1, 0,
                           '/sys/bus/usb/devices/usb3/3-1/3-1.4/product')

        self._add_usb_test('USB A口 (左下) 2.0', 0, 1,
                           '/sys/bus/usb/devices/usb2/2-1/2-1.1/product')
        self._add_usb_test('USB A口 (左下) 3.0', 1, 1,
                           '/sys/bus/usb/devices/usb3/3-1/3-1.1/product')

        self._add_usb_test('USB A口 (右上) 2.0', 0, 2,
                           '/sys/bus/usb/devices/usb2/2-1/2-1.2/product')
        self._add_usb_test('USB A口 (右上) 3.0', 1, 2,
                           '/sys/bus/usb/devices/usb3/3-1/3-1.2/product')

        self._add_usb_test('USB A口 (右下) 2.0', 0, 3,
                           '/sys/bus/usb/devices/usb2/2-1/2-1.3/product')
        self._add_usb_test('USB A口 (右下) 3.0', 1, 3,
                           '/sys/bus/usb/devices/usb3/3-1/3-1.3/product')


        self.tests_layout.addWidget(self.usb_frame, row, column, row_span, column_span)
    # [end] Check the usb to see if the device is inserted

    def _create_qrcode(self, data):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=0,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')
        # Convert PIL Image to QImage directly
        img = img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimage = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def _setup_sn_qrcode(self, sn):
        sn_qrcode = QFrame(self.others_item)
        sn_qrcode_layout = QVBoxLayout(sn_qrcode)

        qr_label = QLabel(sn_qrcode)
        qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setPixmap(self._create_qrcode(sn))
        sn_qrcode_layout.addWidget(qr_label)

        sn_label = QLabel(f'{self.sl.get_text("sn")}: {sn}', sn_qrcode)
        sn_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        sn_qrcode_layout.addWidget(sn_label)

        self.others_item_layout.addWidget(sn_qrcode)


    ######################################################
    # Handlers for setting a new project
    ######################################################

    @property
    def project(self):
        return self._project

    def _get_text(self, subModuleName, subModule, key):
        module = import_module(subModule.parent.path)
        testcase = getattr(module, subModuleName)
        if hasattr(testcase, 'LANGUAGES'):
            langs = getattr(testcase, 'LANGUAGES')
            lang = langs.get(self.sl.current_lang)
            if lang is not None:
                text = lang.get(key)
                if text is not None:
                    return text

        return key

    def _add_test_module(self, parentNode, testModule):
        for subModuleName, subModule in sorted(testModule.items()):
            if isinstance(subModule, TestModule):
                self._add_test_module(parentNode, subModule)
            else:
                for testMethod_name, testMethod in sorted(subModule.items()):
                    self.test_list.setdefault(parentNode, []).append(testMethod.path)

                    table = self.test_table[parentNode]
                    row = table.rowCount()
                    table.insertRow(row)
                    item = QTableWidgetItem(self._get_text(subModuleName, subModule, subModuleName))
                    table.setItem(row, 0, item)

                    # Get test method name
                    method_text = self._get_text(subModuleName, subModule, testMethod_name)

                    # Check if test class has get_capacity method and display capacity info
                    try:
                        module = import_module(subModule.parent.path)
                        testcase = getattr(module, subModuleName)
                        if hasattr(testcase, 'get_capacity'):
                            capacity = testcase.get_capacity()
                            if capacity > 0:
                                method_text = f'{method_text} ({capacity} GB)'
                    except Exception as e:
                        _logger.debug(f'Error getting capacity for {subModuleName}: {e}')

                    item = QTableWidgetItem(method_text)
                    table.setItem(row, 1, item)

                    if parentNode == 'manual':
                        column_0_text = self._get_text(subModuleName, subModule, subModuleName)
                        widget = self.manual_res_manager.append_pass_and_fail_btn(column_0_text, method_text)
                        table.setCellWidget(row, 2, widget)
                    else:
                        item = QTableWidgetItem('')
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setData(Qt.UserRole, testMethod.path)
                        table.setItem(row, 2, item)

                    logical_dpi = table.logicalDpiY()
                    font_pixel = self.font_size * logical_dpi / 72
                    row_height = int(font_pixel * 1.8)
                    table.setRowHeight(row, row_height)

    @project.setter
    def project(self, project):
        self._project = project

        # Get a count of active tests to display in the status bar.
        # count, labels = self.project.find_tests(True)
        # self.run_summary.set('T:%s P:0 F:0 E:0 X:0 U:0 S:0' % count)

        # Populate the initial tree nodes. This is recursive, because
        # the tree could be of arbitrary depth.
        for testModule_name, testModule in sorted(project.items()):
            self._add_test_module(testModule_name, testModule)
            self.executor[testModule_name] = None

        self.manual_res_manager.setup_slot_connection()
        self.showFullScreen()

        TestMethod.bind('status_update', self.on_nodeStatusUpdate)

    ######################################################
    # TK Main loop
    ######################################################

    def mainloop(self):
        self.hdmi_thread = threading.Thread(target=self.hdmi_loop)
        self.hdmi_thread.start()

        self.audio_thread = threading.Thread(target=lambda: self.audio_loop())
        self.audio_thread.start()

        self.cmd_run_all()

        self.root.exec_()

    def hdmi_loop(self):
        pass
        # HDMI detection removed

    def _play_wav(self, device, volume, path):
        cmd = f'amixer -c 1 cset numid=1,iface=MIXER,name="DAC Playback Volume" {volume}'
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        # print(f'Set playback volume to {volume} return {proc.returncode}')

        cmd = f'aplay -D{device} -r 48000 -f S16_LE {path} -c 2'
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        # print(f'Play {path} on {device} return {proc.returncode}')

    def _record_wav(self, device, volume, duration, path):
        cmd = f'amixer -c 1 cset numid=1,iface=MIXER,name="ADC Capture Volume" {volume},{volume}'
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        # print(f'Set capture volume to {volume} return {proc.returncode}')

        cmd = f'arecord -D{device} -r 48000 -f S16_LE -d {duration} {path} -c 2'
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        # print(f'Record {path} on {device} in {duration}s return {proc.returncode}')

    def audio_loop(self):
        # sleep for a while
        time.sleep(15)

        device = 'hw:1'
        playback_volume = 184
        record_volume = 184
        duration = 5

        res_path = '/opt/factorytest/res'
        start_record_file = f'{res_path}/start-record.wav'
        stop_record_file = f'{res_path}/stop-record.wav'
        start_play_file = f'{res_path}/start-play.wav'
        stop_play_file = f'{res_path}/stop-play.wav'
        record_file = '/tmp/factorytest-record.wav'

        while True:
            self._play_wav(device, playback_volume, start_record_file)
            self._record_wav(device, record_volume, duration, record_file)
            self._play_wav(device, playback_volume, stop_record_file)
            self._play_wav(device, playback_volume, start_play_file)
            self._play_wav(device, playback_volume, record_file)
            self._play_wav(device, playback_volume, stop_play_file)
            time.sleep(duration)

    # lcd part
    # def update_lcd_color(self):
    #     color = self.lcd_color_list[self.lcd_color_index % len(self.lcd_color_list)]
    #     self.lcd_color_index += 1
    #     self.setPalette(QPalette(QColor(color)))

    def set_brightness(self, brightness = 128):
        path = '/sys/devices/platform/soc/soc:lcd_backlight/backlight/soc:lcd_backlight/brightness'
        try:
            with open(path, 'w') as f:
                f.write(f'{brightness}')
        except:
            pass

    # def keyPressEvent(self, event):
    #     super().keyPressEvent(event)

    # def mousePressEvent(self, event):
    #     super().mousePressEvent(event)

    ######################################################
    # User commands
    ######################################################
    # def cmd_lcd(self):
    #     self.on_lcdTest = True
    #     self.content.setVisible(False)
    #     self.lcd_color_index = 0
    #     self.update_lcd_color()

    def cmd_poweroff(self):
        self.stop()
        os.system('poweroff')

    def cmd_reboot(self):
        self.stop()
        os.system('reboot')

    # ------------------------------------------------------------------ #
    # Ethernet time-sync loop                                              #
    # ------------------------------------------------------------------ #

    def _get_detected_eth_interface(self):
        """Read detected ethernet interface from test result, default to eth0."""
        try:
            with open('/tmp/detected_eth_interface', 'r') as f:
                ifname = f.read().strip()
                if ifname in ['eth0', 'eth1']:
                    _logger.info(f'Using detected interface: {ifname}')
                    return ifname
        except:
            pass
        _logger.info('Using default interface: eth0')
        return 'eth0'

    def _get_eth_ip(self, interface):
        """Return the IPv4 address of *interface*, or None if not available."""
        try:
            result = subprocess.run(
                ['ip', '-4', 'addr', 'show', interface],
                capture_output=True, text=True)
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
            if match:
                ip = match.group(1)
                # Ignore link-local addresses
                if not ip.startswith('169.254'):
                    return ip
        except Exception as e:
            _logger.error(f'_get_eth_ip error: {e}')
        return None

    def _eth_sync_loop(self):
        """Poll ethernet IP every second; once obtained, sync time and enable save button."""
        ip = self._get_eth_ip(self._eth_interface)

        if ip:
            # Update IP label
            self.eth_ip_label.setText(
                f'   {self.sl.get_text("eth_ip")}: {ip}')

            # Refresh time
            command = "TZ='Asia/Shanghai' date +\"%Y%m%d%H%M%S\""
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            time_cst = result.stdout.strip()
            try:
                dt_obj = datetime.strptime(time_cst, "%Y%m%d%H%M%S")
                formatted = dt_obj.strftime("%Y/%m/%d %H:%M")
                self.current_time_label.setText(
                    f'   {self.sl.get_text("current_time")}: {formatted}')
            except Exception:
                pass

            # Check whether the clock has been NTP-synced
            if int(time_cst[0:8]) >= 20240806:
                self._save_file_manager.eth_sync = True
                self._save_file_manager.time_sync = True
                self.save_test_button.setEnabled(True)
                self.save_test_button.setText(self.sl.get_text('save_test_results'))
            else:
                self._save_file_manager.eth_sync = False
                self._save_file_manager.time_sync = False
                self.save_test_button.setEnabled(False)
                self.save_test_button.setText(
                    f"{self.sl.get_text('save_test_results')}(不可用-时间未同步)")
        else:
            self.eth_ip_label.setText(
                f'   {self.sl.get_text("eth_ip")}: --')
            self._save_file_manager.eth_sync = False
            if self._save_file_manager.time_sync:
                # Lost ethernet after sync — keep time display but disable save
                self.save_test_button.setEnabled(False)
                self.save_test_button.setText(
                    f"{self.sl.get_text('save_test_results')}(不可用-网络断开)")

        QTimer.singleShot(1000, self._eth_sync_loop)

    # ------------------------------------------------------------------ #
    # Save / clear test results commands                                   #
    # ------------------------------------------------------------------ #

    def cmd_save_test(self):
        """Save test results to CSV when ethernet is up and time is synced."""
        from PyQt5.QtWidgets import QMessageBox
        self._save_file_manager.get_time_cst()
        if self._save_file_manager.time_sync and self._save_file_manager.eth_sync:
            ret = self._save_file_manager.write_to_csv()
            if ret:
                self.save_test_button.setPalette(QPalette(QColor(PASS_COLOR)))
                self.save_test_button.setText('已保存')
                QTimer.singleShot(2000, self._reset_save_test_button)
            else:
                self.save_test_button.setPalette(QPalette(QColor(FAIL_COLOR)))
                self.save_test_button.setText(
                    f"{self.sl.get_text('save_test_results')}(保存失败)")
        else:
            dlg = QMessageBox()
            dlg.setIcon(QMessageBox.Critical)
            dlg.setWindowTitle("错误")
            if not self._save_file_manager.time_sync and not self._save_file_manager.eth_sync:
                dlg.setInformativeText("时间未同步，请先连接有线网络！")
            elif not self._save_file_manager.time_sync:
                dlg.setInformativeText("时间未同步，请检查网络时间是否正常")
            else:
                dlg.setInformativeText("请连接有线网络！")
            dlg.setStandardButtons(QMessageBox.Ok)
            dlg.exec_()

    def _reset_save_test_button(self):
        self.save_test_button.setPalette(QPalette(QColor('white')))
        self.save_test_button.setText(self.sl.get_text('save_test_results'))

    def cmd_clear_test(self):
        """Clear all saved CSV result files after user confirmation."""
        from PyQt5.QtWidgets import QMessageBox
        dlg = QMessageBox(QMessageBox.Question, '清除确认',
                          '确认要清除所有测试结果文件吗？',
                          QMessageBox.Yes | QMessageBox.No, self)
        if dlg.exec_() == QMessageBox.Yes:
            self._save_file_manager.clear_csv_files()
            self._save_file_manager.set_file_name_flag = False
            _logger.info('Test result files cleared.')


    def cmd_quit(self):
        "Command: Quit"
        # If the runner is currently running, kill it.
        self.stop()

        self.root.quit()

    def cmd_stop(self, event=None):
        "Command: The stop button has been pressed"
        self.stop()

    def cmd_run_all(self, event=None):
        "Command: The Run all button has been pressed"
        # If the executor isn't currently running, we can
        # start a test run.
        for module, executor in self.executor.items():
            if not executor or not executor.is_running:
                self.run(module)

    def cmd_run_selected(self, event=None):
        "Command: The 'run selected' button has been pressed"
        for module, table in self.test_table.items():
            # If the executor isn't currently running, we can
            # start a test run.
            labels = []
            for item in table.selectedItems():
                data = item.data(Qt.UserRole)
                if data is not None:
                    labels.append(data)

            if labels and (not self.executor[module] or
                           not self.executor[module].is_running):
                self.run(module, labels=labels)

    # aging part
    def _convert_seconds(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60

        return hours, minutes, remaining_seconds

    def update_aging_hints(self, error: str = None):
        hours, minutes, seconds = self._convert_seconds(self.aging_elapse)
        hints = '正在进行老化测试...\n'
        hints += f'计划老化 {self.aging_duration_choice.currentText()} 小时\n'
        hints += f'已老化 {hours} 小时 {minutes} 分 {seconds} 秒\n'
        if error:
            hints += error
        self.aging_dialog.setLabelText(hints)

    def start_aging_test(self):
        self.cpu_aging_proc = None
        self.ddr_aging_proc = None
        self.gpu_aging_proc = None
        self.vpu_aging_proc = None
        self.ai_cpu_aging_proc = None

        if self.cpu_aging.isChecked():
            _logger.info('start cpu aging test')
            cmd = 'stress-ng --cpu 8 --cpu-method all --cpu-load 50 --metrics-brief'
            self.cpu_aging_proc = subprocess.Popen(cmd, shell=True,
                                                   start_new_session= True,
                                                   stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE)

        if self.ddr_aging.isChecked():
            _logger.info('start ddr aging test')
            cmd = '/opt/factorytest/utils/memtester.sh'
            self.ddr_aging_proc = subprocess.Popen(cmd, shell=True,
                                                   start_new_session= True,
                                                   stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE)

        if self.gpu_aging.isChecked():
            _logger.info('start gpu aging test')
            cmd = 'glmark2-es2-wayland --off-screen --run-forever > /tmp/glmark2.log'
            self.gpu_aging_proc = subprocess.Popen(cmd, shell=True,
                                                   start_new_session= True,
                                                   stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE)

        if self.vpu_aging.isChecked():
            _logger.info('start vpu aging test')
            cmd = '/opt/factorytest/utils/vpu.sh'
            self.vpu_aging_proc = subprocess.Popen(cmd, shell=True,
                                                   start_new_session= True,
                                                   stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE)

        if self.ai_cpu_aging.isChecked():
            _logger.info('start ai-cpu aging test')
            cmd = '/opt/factorytest/utils/stress_ng_ai_cpu.sh stress-ng --cpu 8 --cpu-method all --cpu-load 50 --metrics-brief'
            self.ai_cpu_aging_proc = subprocess.Popen(cmd, shell=True,
                                                      start_new_session=True,
                                                      stdout=subprocess.PIPE,
                                                      stderr=subprocess.PIPE)

    def on_agingTestUpdate(self):
        self.aging_elapse += 1
        self.aging_dialog.setValue(self.aging_elapse)

        error_modules = []
        if self.cpu_aging.isChecked():
            if self.cpu_aging_proc and self.cpu_aging_proc.poll():
                if self.cpu_aging_proc.returncode != 0:
                    _logger.error('cpu aging test fail')
                    error_modules.append('CPU')
                self.cpu_aging_proc = None

        if self.ddr_aging.isChecked():
            if self.ddr_aging_proc and self.ddr_aging_proc.poll():
                if self.ddr_aging_proc.returncode != 0:
                    _logger.error('ddr aging test fail')
                    error_modules.append('DDR')
                self.ddr_aging_proc = None

        if self.gpu_aging.isChecked():
            if self.gpu_aging_proc and self.gpu_aging_proc.poll():
                if self.gpu_aging_proc.returncode != 0:
                    _logger.error('gpu aging test fail')
                    error_modules.append('GPU')
                self.gpu_aging_proc = None

        if self.vpu_aging.isChecked():
            if self.vpu_aging_proc and self.vpu_aging_proc.poll():
                if self.vpu_aging_proc.returncode != 0:
                    _logger.error('vpu aging test fail')
                    error_modules.append('VPU')
                self.vpu_aging_proc = None

        if self.ai_cpu_aging.isChecked():
            if self.ai_cpu_aging_proc and self.ai_cpu_aging_proc.poll():
                if self.ai_cpu_aging_proc.returncode != 0:
                    _logger.error('ai-cpu aging test fail')
                    error_modules.append('AI-CPU')
                self.ai_cpu_aging_proc = None

        if error_modules:
            error = ', '.join(error_modules) + '老化测试异常'
            self.aging_pass = False
            self.aging_timer.stop()
        else:
            error = '一切正常'

        self.update_aging_hints(error)

        if self.aging_elapse >= self.aging_duration and not error_modules:
            self.aging_dialog.close()

    def stop_aging_test(self):
        if self.cpu_aging.isChecked():
            _logger.info('stop cpu aging test')
            if self.cpu_aging_proc and not self.cpu_aging_proc.poll():
                self.cpu_aging_proc.kill()
                self.cpu_aging_proc.wait()
            self.cpu_aging_proc = None

        if self.ddr_aging.isChecked():
            _logger.info('stop ddr aging test')
            if self.ddr_aging_proc and not self.ddr_aging_proc.poll():
                self.ddr_aging_proc.kill()
                self.ddr_aging_proc.wait()
            self.ddr_aging_proc = None

        if self.gpu_aging.isChecked():
            _logger.info('stop gpu aging test')
            if self.gpu_aging_proc and not self.gpu_aging_proc.poll():
                self.gpu_aging_proc.kill()
                self.gpu_aging_proc.wait()
            self.gpu_aging_proc = None

        if self.vpu_aging.isChecked():
            _logger.info('stop vpu aging test')
            if self.vpu_aging_proc and not self.vpu_aging_proc.poll():
                self.vpu_aging_proc.kill()
                self.vpu_aging_proc.wait()
            self.vpu_aging_proc = None

        if self.ai_cpu_aging.isChecked():
            _logger.info('stop ai-cpu aging test')
            if self.ai_cpu_aging_proc and not self.ai_cpu_aging_proc.poll():
                self.ai_cpu_aging_proc.kill()
                self.ai_cpu_aging_proc.wait()
            self.ai_cpu_aging_proc = None

    def cmd_aging(self):
        self.aging_duration = int(self.aging_duration_choice.currentText()) * 3600
        self.aging_elapse = 0
        self.aging_pass = True

        self.aging_dialog = QProgressDialog('', f'{self.sl.get_text("aging_cancel")}',
                                            0, self.aging_duration, self)
        self.aging_dialog.setWindowTitle(self.sl.get_text('aging_test'))
        self.update_aging_hints()
        self.aging_dialog.setValue(0)
        self.aging_dialog.setAutoClose(True)
        self.aging_dialog.setAutoReset(False)
        self.aging_dialog.setAutoFillBackground(True)
        self.aging_dialog.setPalette(QPalette(QColor('yellow')))
        self.aging_dialog.resize(320, 200)

        self.start_aging_test()

        self.aging_timer = QTimer(self.aging_dialog)
        self.aging_timer.timeout.connect(self.on_agingTestUpdate)
        self.aging_timer.start(1000)

        rc = self.aging_dialog.exec_()
        _logger.info(f'aging dialog closed with rc={rc}')

        self.aging_timer.stop()

        self.stop_aging_test()

        if self.aging_elapse >= self.aging_duration and self.aging_pass:
            _logger.info('aging test PASSED')
            self.aging_button.setPalette(QPalette(QColor(PASS_COLOR)))
        else:
            _logger.error(f'aging test FAILED (elapsed={self.aging_elapse}s, duration={self.aging_duration}s, pass={self.aging_pass})')
            self.aging_button.setPalette(QPalette(QColor(FAIL_COLOR)))

    #
    def cmd_peripheral_test(self):
        self.peripheral_test_view.exec_()

    ######################################################
    # GUI Callbacks
    ######################################################

    def on_testMethodSelected(self):
        "Event handler: a test case has been selected in the tree"
        # update "run selected" button enabled state
        self.set_selected_button_state()

    def _get_sn(self):
        path = '/proc/device-tree/serial-number'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.readline().strip()

    def _get_fw_version(self):
        path = '/etc/bianbu_version'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.readline().strip()

    def _get_product_name(self):
        path = '/proc/device-tree/model'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.readline().replace('spacemit', '').replace('board', '').strip()

    def _get_SSD_size(self):
        path = '/sys/class/nvme/nvme0/nvme0n1/size'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return round(int(f.readline().strip()) / 1000 / 1000 / 2, 0)
        return 0

    def _get_TF_size(self):
        path = '/sys/class/block/mmcblk0/size'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return round(int(f.readline().strip()) / 1000 / 1000 / 2, 1)
        return 0

    def _get_UFS_size(self):
        path = '/sys/class/block/sda/size'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return round(int(f.readline().strip()) / 1000 / 1000 / 2, 1)
        return 0

    def _get_DDR_size(self):
        with open('/proc/meminfo', 'r') as f:
            for line in f.readlines():
                if line.startswith('MemTotal:'):
                    return round(int(line.split()[1]) / 1024 / 1024, 0)

    def _get_CPU_model(self):
        cpu_models = []
        with open('/proc/cpuinfo', 'r') as f:
            for line in f.readlines():
                if line.startswith('model name'):
                    model = line.split(':')[1].strip()
                    if model not in cpu_models:
                        cpu_models.append(model)
        
        if len(cpu_models) == 1:
            return cpu_models[0]
        elif len(cpu_models) > 1:
            return ' + '.join(cpu_models)
        else:
            return 'Unknown'

    def _get_CPU_freq(self):
        with open('/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq', 'r') as f:
            return round(int(f.readline().strip()) / 1000 / 1000, 1)

    # cpu temp part
    def on_cpuTempUpdate(self):
        self.cpu_temp.setText(f'{self.sl.get_text("cpu_temp")}: {self._get_CPU_Temp()} °C')
        try:
            key, value = self.cpu_temp.text().split(':', 1)
            self._save_file_manager.update_info_test_status(key.strip(), value.strip())
        except Exception:
            pass

    def _get_CPU_Temp(self):
        temp_path = "/sys/class/thermal/thermal_zone0/temp"
        ret = "None"

        try:
            if os.path.isfile(temp_path):
                with open(temp_path, 'r') as temp_file:
                    temp_content = temp_file.read().strip()
                    temp_content = int(temp_content) // 1000
                    ret = str(temp_content)
        except Exception as e:
            print(f"An error occurred when getting cpu temperature: {e}")

        return ret

    def on_nodeStatusUpdate(self, node):
        "Event handler: a node on the tree has received a status update"
        module = node.path.split('.')[0]
        # Manual tests use pass/fail buttons, skip automatic status update
        if module == 'manual':
            return
        table = self.test_table[module]
        columnCount = table.columnCount()
        for row in range(table.rowCount()):
            item = table.item(row, columnCount-1)
            if item is not None:
                if item.data(Qt.UserRole) == node.path:
                    if module == 'manual' and node.status == TestMethod.STATUS_PASS:
                        item.setText('人工判断')
                        break

                    for column in range(columnCount):
                        _item = table.item(row, column)
                        _item.setBackground(QColor(STATUS[node.status]['color']))

                    item.setText(STATUS[node.status]['description'])

                    # Persist result into DeviceStatusManager for CSV export
                    item_name = table.item(row, 0).text()
                    description = STATUS[node.status]['description']
                    try:
                        if module == 'auto':
                            self._save_file_manager.update_auto_status(item_name, description)
                            # Start time-sync after ETH test passes
                            if item_name == '网口' and node.status == TestMethod.STATUS_PASS and not self._eth_sync_started:
                                self._eth_sync_started = True
                                self._eth_sync_loop()
                        elif module == 'auto_camera':
                            self._save_file_manager.update_auto_camera_status(item_name, description)
                    except Exception as e:
                        _logger.error(f'fail update_status for {module}/{item_name}: {e}')

                    break

    def on_testProgress(self, executor):
        "Event handler: a periodic update to poll the runner for output, generating GUI updates"
        if executor and executor.poll():
            QTimer.singleShot(100, lambda: self.on_testProgress(executor))

    def on_executorStatusUpdate(self, event, module, update):
        "The executor has some progress to report"
        # Update the status line.
        self.run_status[module].showMessage(update)

    def on_executorTestStart(self, event, module, test_path):
        "The executor has started running a new test."
        # Update status line
        self.run_status[module].showMessage('Running %s...' % test_path)

    def on_executorTestEnd(self, event, module, test_path, result, remaining_time):
        "The executor has finished running a test."
        self.run_status[module].showMessage('')
        # Update the progress meter
        # self.progress_value.set(self.progress_value.get() + 1)

        # Update the run summary
        # self.run_summary.set('T:%(total)s P:%(pass)s F:%(fail)s E:%(error)s X:%(expected)s U:%(unexpected)s S:%(skip)s, ~%(remaining)s remaining' % {
        #     'total': self.executor.total_count,
        #     'pass': self.executor.result_count.get(TestMethod.STATUS_PASS, 0),
        #     'fail': self.executor.result_count.get(TestMethod.STATUS_FAIL, 0),
        #     'error': self.executor.result_count.get(TestMethod.STATUS_ERROR, 0),
        #     'expected': self.executor.result_count.get(TestMethod.STATUS_EXPECTED_FAIL, 0),
        #     'unexpected': self.executor.result_count.get(TestMethod.STATUS_UNEXPECTED_SUCCESS, 0),
        #     'skip': self.executor.result_count.get(TestMethod.STATUS_SKIP, 0),
        #     'remaining': remaining_time
        # })

        # If the test that just fininshed is the one (and only one)
        # selected on the tree, update the display.
        # current_tree = self.current_test_tree
        # if len(current_tree.selection()) == 1:
        #     # One test selected.
        #     if current_tree.selection()[0] == test_path:
        #         # If the test that just finished running is the selected
        #         # test, force reset the selection, which will generate a
        #         # selection event, forcing a refresh of the result page.
        #         current_tree.selection_set(current_tree.selection())
        # else:
        #     # No or Multiple tests selected
        #     self.name.set('')
        #     self.test_status.set('')

        #     self.duration.set('')
        #     self.description.delete('1.0', END)

        #     self._hide_test_output()
        #     self._hide_test_errors()

    def on_executorSuiteEnd(self, event, module, error=None):
        "The test suite finished running."
        # Display the final results
        self.run_status[module].showMessage('Finished.')

        # Drop the reference to the executor
        self.executor[module] = None

        # Reset the buttons
        self.reset_button_states_on_end()

        # If all modules have finished, save dmesg to log
        if all(ex is None for ex in self.executor.values()):
            save_dmesg_to_log()

    def on_executorSuiteError(self, event, module, error):
        "An error occurred running the test suite."
        # Display the error in a dialog
        self.run_status[module].showMessage('Error running test suite.')
        # FailedTestDialog(self.root, error)

        # Drop the reference to the executor
        self.executor[module] = None

    def reset_button_states_on_end(self):
        "A test run has ended and we should enable or disable buttons as appropriate."
        is_stoped = True
        for executor in self.executor.values():
            if executor and executor.is_running:
                is_stoped = False

        if is_stoped:
            self.stop_button.setDisabled(True)
            self.run_all_button.setDisabled(False)

        self.set_selected_button_state()

    def set_selected_button_state(self):
        is_running = False
        for executor in self.executor.values():
            if executor and executor.is_running:
                is_running = True

        is_selected = False
        for table in self.test_table.values():
            if table.selectedItems():
                is_selected = True

        if is_running:
            self.run_selected_button.setDisabled(True)
        elif is_selected:
            self.run_selected_button.setDisabled(False)
        else:
            self.run_selected_button.setDisabled(True)

    ######################################################
    # GUI utility methods
    ######################################################

    def run(self, module, active=True, status=None, labels=None):
        """Run the test suite.

        If active=True, only active tests will be run.
        If status is provided, only tests whose most recent run
            status matches the set provided will be executed.
        If labels is provided, only tests with those labels will
            be executed
        """
        labels = labels if labels else self.test_list[module]

        self.run_status[module].showMessage('Running...')
        # self.run_summary.set('T:%s P:0 F:0 E:0 X:0 U:0 S:0' % count)

        self.run_all_button.setDisabled(True)
        self.run_selected_button.setDisabled(True)
        self.stop_button.setDisabled(False)

        # self.progress['maximum'] = count
        # self.progress_value.set(0)

        # Create the runner
        self.executor[module] = Executor(self.project, module, len(labels), labels)

        # Queue the first progress handling event
        QTimer.singleShot(100, lambda: self.on_testProgress(self.executor[module]))

    def stop(self):
        "Stop the test suite."
        for module, executor in self.executor.items():
            if executor and executor.is_running:
                self.run_status[module].showMessage('Stopping...')

                executor.terminate()
                executor = None

                self.run_status[module].showMessage('Stopped.')

        self.reset_button_states_on_end()

    def _hide_test_output(self):
        "Hide the test output panel on the test results page"
        self.output_label.grid_remove()
        self.output.grid_remove()
        self.output_scrollbar.grid_remove()
        self.details_frame.rowconfigure(3, weight=0)

    def _show_test_output(self, content):
        "Show the test output panel on the test results page"
        self.output.delete('1.0', END)
        self.output.insert('1.0', content)

        self.output_label.grid()
        self.output.grid()
        self.output_scrollbar.grid()
        self.details_frame.rowconfigure(3, weight=5)

    def _hide_test_errors(self):
        "Hide the test error panel on the test results page"
        self.error_label.grid_remove()
        self.error.grid_remove()
        self.error_scrollbar.grid_remove()

    def _show_test_errors(self, content):
        "Show the test error panel on the test results page"
        self.error.delete('1.0', END)
        self.error.insert('1.0', content)

        self.error_label.grid()
        self.error.grid()
        self.error_scrollbar.grid()
