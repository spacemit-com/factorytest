import os
from PyQt5.QtCore import QThread, pyqtSignal
from ftplib import FTP
from cricket.loggermanager import LoggerManager


class FtpUploadThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, host, port, user, passwd, local_folder, remote_folder):
        super().__init__()
        self.log_manager = LoggerManager(name='FTPLogger')
        self.custom_logger = self.log_manager.get_logger()
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.local_folder = local_folder
        self.remote_folder = remote_folder

    def run(self):
        try:
            ftp = FTP(timeout=30)
            ftp.connect(self.host, self.port)
            ftp.login(user=self.user, passwd=self.passwd)
            self.upload_directory(ftp, self.local_folder, self.remote_folder)
            ftp.quit()
            self.finished.emit(f"PASS{self.local_folder}")
        except Exception as e:
            self.finished.emit(f"Fail{self.local_folder}: {str(e)}")

    def upload_directory(self, ftp: FTP, local_dir, remote_dir: str):
        try:
            ftp.cwd('/')
            ftp.cwd(remote_dir)
        except Exception:
            dirs = remote_dir.split("/")
            path = ""
            for directory in dirs:
                if directory:
                    path += "/" + directory
                    try:
                        ftp.mkd(path)
                    except Exception as e:
                        self.custom_logger.error(f"ftp mkd error: {e}")
            ftp.cwd(remote_dir)

        if not os.path.isfile(local_dir):
            for item in os.listdir(local_dir):
                if item == '.shaders':
                    continue
                local_path = os.path.join(local_dir, item)
                if os.path.isfile(local_path):
                    self.upload_if_newer(ftp, local_path, item)
                elif os.path.isdir(local_path):
                    remote_path = os.path.join(remote_dir, item)
                    self.upload_directory(ftp, local_path, remote_path)
        else:
            remote_path = os.path.basename(local_dir)
            self.upload_if_newer(ftp, local_dir, remote_path)

    def upload_if_newer(self, ftp: FTP, local_path, remote_path):
        try:
            remote_time = ftp.sendcmd(f"MDTM {remote_path}")[4:].strip()
            remote_size = ftp.size(remote_path)
        except Exception:
            remote_time = None
            remote_size = -1

        local_time = os.path.getmtime(local_path)
        local_size = os.path.getsize(local_path)

        # Upload if remote file doesn't exist, local is newer, or sizes differ
        if remote_time is None or local_time > float(remote_time) or local_size != remote_size:
            try:
                with open(local_path, 'rb') as f:
                    ftp.storbinary(f'STOR {remote_path}', f)
            except Exception as e:
                self.custom_logger.error(f"Fail upload {local_path}: {e}")
        else:
            pass
