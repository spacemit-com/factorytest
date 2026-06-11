
import csv
import subprocess
import os
import glob
from datetime import datetime, timedelta
from PyQt5.QtCore import QTimer, QObject
from cricket.loggermanager import LoggerManager
from cricket.ftpclient import FtpUploadThread


class DeviceStatusManager(QObject):
    def __init__(self):
        super().__init__()
        self.period_time = 0
        self.time_loop_count()

        self.log_manager = LoggerManager(name='TestFileLogger')
        self.custom_logger = self.log_manager.get_logger()

        self.time_sync = False
        # eth_sync replaces wifi_sync: True when ethernet is up and time is valid
        self.eth_sync = False
        self.check_mode = 1
        self.set_file_name_flag = False

        self.serial_number = ""
        self.part_number = ""
        self.eth_mac = ""

        self.file_save_dir = "/opt/factorytest/results"
        if not os.path.exists(self.file_save_dir):
            os.makedirs(self.file_save_dir)

        # result dict
        # auto       : tests/auto/*        (NVMe, SpiNor, EEPROM, UFS, ETH, TF, WiFi, BT, TypeC)
        # manual     : tests/manual/*      (DP Audio, Fan, GPIO, MIPI LCD)
        # auto_camera: tests/auto_camera/* (CSI0, CSI2)
        self.results = {'info': {}, 'sn': {}}
        self.sort_list = ['auto', 'manual', 'auto_camera']
        for key in self.sort_list:
            self.results[key] = {}

        # ------------------------------------------------------------------ #
        # FTP configuration                                                    #
        # ------------------------------------------------------------------ #
        # Set to True to enable FTP upload of CSV / syslog / boot files.
        # Set to False to disable all FTP uploads (local save only).
        self.ftp_enable = False

        self.ftp_host = '61.145.255.150'
        self.ftp_port = 60021
        self.ftp_user = 'sw-ptlog'
        self.ftp_passwd = '8JCQ%yhZ$Br%'
        self.ftp_save_dir = 'k3_com260'   # top-level remote folder

        # Switch to internal network server:
        self.internal_net = False
        if self.internal_net:
            self.ftp_host = '10.0.32.102'
            self.ftp_port = 21

        # CSV upload thread (one file at a time)
        self.thread_log = FtpUploadThread(
            self.ftp_host, self.ftp_port, self.ftp_user, self.ftp_passwd,
            self.file_save_dir,   # local path updated before each upload
            f"{self.ftp_save_dir}/unknown")
        self.thread_log.finished.connect(self.on_upload_finished)

        # syslog / factorytest.log upload threads
        self.ftp_file_list = ['/var/log/messages', '/root/factorytest.log']
        self.syslog_ftp_list = [
            FtpUploadThread(
                self.ftp_host, self.ftp_port, self.ftp_user, self.ftp_passwd,
                f, f"{self.ftp_save_dir}/unknown")
            for f in self.ftp_file_list
        ]
        for th in self.syslog_ftp_list:
            th.finished.connect(self.on_upload_finished)

        # boot log upload threads
        self.boot_dir_list = ['/root/boot']
        self.boot_ftp_list = [
            FtpUploadThread(
                self.ftp_host, self.ftp_port, self.ftp_user, self.ftp_passwd,
                d, f"{self.ftp_save_dir}/unknown")
            for d in self.boot_dir_list
        ]
        for th in self.boot_ftp_list:
            th.finished.connect(self.on_upload_finished)

        # Periodically upload syslog and boot files every 2 seconds
        self._timer_syslog = QTimer()
        self._timer_syslog.timeout.connect(self.start_ftp_syslog_file)
        self._timer_syslog.start(2000)

        self._timer_boot = QTimer()
        self._timer_boot.timeout.connect(self.start_ftp_boot_file)
        self._timer_boot.start(2000)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def time_loop_count(self):
        """Count seconds since program start (used to back-calculate boot time)."""
        self.period_time += 1
        QTimer.singleShot(1000, self.time_loop_count)

    def get_time_cst(self):
        """Read system clock (CST/Asia:Shanghai) and update time_sync flag."""
        command = "TZ='Asia/Shanghai' date +\"%Y%m%d%H%M%S\""
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        time_cst = str(result.stdout.strip())
        self.current_save_file_time = time_cst

        self.custom_logger.info(f"get_time_cst raw: {time_cst}")

        # Back-calculate to the time the program started
        time_format = "%Y%m%d%H%M%S"
        try:
            time_obj = datetime.strptime(time_cst, time_format)
            new_time_obj = time_obj - timedelta(seconds=self.period_time)
            time_cst = new_time_obj.strftime(time_format)
        except Exception:
            pass

        # A date >= 2024-08-06 means the system clock has been NTP-synced
        if int(time_cst[0:8]) >= 20240806:
            self.time_sync = True
        else:
            self.time_sync = False

        self.custom_logger.info(f"get_time_cst adjusted: {time_cst}, time_sync={self.time_sync}")
        self.time_cst = time_cst

    # ------------------------------------------------------------------ #
    # File name / CSV helpers                                              #
    # ------------------------------------------------------------------ #

    def set_file_save_name(self):
        status_all = self.check_all_test_pass()
        time_cst = self.time_cst
        sn = self.serial_number if self.serial_number else 'unknown'
        file_name = sn + "-" + status_all + "-" + time_cst + ".csv"
        return os.path.join(self.file_save_dir, file_name)

    def check_all_test_pass(self):
        status_all = "PASS"
        for name, results in self.results.items():
            for sub_name, result in results.items():
                if result == "FAIL":
                    return "FAIL"
        return status_all

    def clear_csv_files(self):
        sn = self.serial_number if self.serial_number else 'unknown'
        pattern = os.path.join(self.file_save_dir, f'{sn}-*.csv')
        csv_files = glob.glob(pattern)
        for csv_file in csv_files:
            try:
                os.remove(csv_file)
            except Exception as e:
                self.custom_logger.error(f"Error deleting {csv_file}: {e}")

    def write_to_csv(self):
        try:
            if self.set_file_name_flag is False:
                self.full_file_path = self.set_file_save_name()
                self.set_file_name_flag = True

            with open(self.full_file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                # Header rows: device info
                line_0 = []
                line_1 = []
                for item, status in self.results['info'].items():
                    line_0.append(item)
                    line_1.append(status)
                for item, status in self.results.get('sn', {}).items():
                    line_0.append(item)
                    line_1.append(status)
                writer.writerow(line_0)
                writer.writerow(line_1)

                writer.writerow([" ", " "])
                writer.writerow(["ItemName", "TestResult"])

                for test_item in self.sort_list:
                    for item, status in self.results[test_item].items():
                        writer.writerow([item, status])

                writer.writerow(["文件写入时间", self.current_save_file_time])

            self.custom_logger.info(f"CSV saved: {self.full_file_path}")
            # Trigger FTP upload after a short delay
            QTimer.singleShot(200, self.start_ftp_upload)
            return True

        except Exception as e:
            self.custom_logger.error(f"fail write csv: {e}")
            return None

    # ------------------------------------------------------------------ #
    # Result update helpers (mirrors muse-paper2 API)                     #
    # ------------------------------------------------------------------ #

    def update_info_test_status(self, item_name, status):
        self.results['info'][item_name] = status

    def update_auto_status(self, item_name, status):
        """Called by on_nodeStatusUpdate for the 'auto' module.
        Tests: NVMe SSD, Mini NVMe SSD, SpiNor, EEPROM, UFS, ETH, TF卡, WiFi, BT, Type-C
        """
        if status == "通过":
            value = "PASS"
        else:
            value = "FAIL"
        self.results['auto'][item_name] = value

    def update_manual_status(self, item_name, status):
        """Called by on_nodeStatusUpdate for the 'manual' module.
        Tests: DP Audio, Fan, GPIO, MIPI LCD
        """
        if status == "通过":
            value = "PASS"
        else:
            value = "FAIL"
        self.results['manual'][item_name] = value

    def update_manual_test_status(self, item_name, status):
        """Called by ManualResultManager buttons (PASSSTR/FAILSTR/INITSTR)."""
        self.results['manual'][item_name] = status

    def update_auto_camera_status(self, item_name, status):
        """Called by on_nodeStatusUpdate for the 'auto_camera' module.
        Tests: CSI0, CSI2
        """
        if status == "通过":
            value = "PASS"
        else:
            value = "FAIL"
        self.results['auto_camera'][item_name] = value

    def update_sn_test_status(self, item_name, status):
        self.results['sn'][item_name] = status

    # ------------------------------------------------------------------ #
    # FTP helpers                                                          #
    # ------------------------------------------------------------------ #

    def _get_ftp_sub_dir(self):
        """Return a per-device sub-directory name for FTP uploads."""
        if self.serial_number:
            return self.serial_number
        elif self.eth_mac:
            return f'ethmac_{self.eth_mac}'
        else:
            return 'unknown'

    def start_ftp_upload(self):
        """Upload the saved CSV to the FTP server (only when eth is up)."""
        if not self.ftp_enable or not self.eth_sync:
            return
        sub_dir = self._get_ftp_sub_dir()
        self.thread_log.remote_folder = f"{self.ftp_save_dir}/{sub_dir}"
        self.thread_log.local_folder = self.full_file_path
        if not self.thread_log.isRunning():
            self.thread_log.start()

    def start_ftp_syslog_file(self):
        """Periodically upload syslog files to FTP (only when eth is up)."""
        if not self.ftp_enable or not self.eth_sync:
            return
        sub_dir = self._get_ftp_sub_dir()
        for th in self.syslog_ftp_list:
            th.remote_folder = f"{self.ftp_save_dir}/{sub_dir}"
            if not th.isRunning():
                th.start()

    def start_ftp_boot_file(self):
        """Periodically upload boot log directory to FTP (only when eth is up)."""
        if not self.ftp_enable or not self.eth_sync:
            return
        sub_dir = self._get_ftp_sub_dir()
        for th in self.boot_ftp_list:
            th.remote_folder = f"{self.ftp_save_dir}/{sub_dir}"
            if not th.isRunning():
                th.start()

    def on_upload_finished(self, message):
        if message.startswith('Fail'):
            self.custom_logger.error(f"FTP upload failed: {message}")
        else:
            self.custom_logger.info(f"FTP upload done: {message}")