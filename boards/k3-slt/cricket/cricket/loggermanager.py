
import logging
import logging.handlers
import subprocess
import sys
import os
from datetime import datetime

# Module-level singleton: one root logger shared by all callers
_root_logger = None
_file_handler = None
_log_file_path = '/root/tmp-factorytest.log'


def _init_root_logger(console_level=logging.INFO):
    global _root_logger, _file_handler, _log_file_path
    if _root_logger is not None:
        return _root_logger

    logger = logging.getLogger('factorytest')
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        _root_logger = logger
        return _root_logger

    formatter = logging.Formatter('%(levelname)s - %(message)s')

    # Append mode: avoid overwriting other machines' logs
    _file_handler = logging.FileHandler(_log_file_path, mode='a')
    _file_handler.setLevel(logging.INFO)
    _file_handler.setFormatter(formatter)
    logger.addHandler(_file_handler)

    _root_logger = logger
    return _root_logger


def update_log_filename(sn):
    """Rename log file to SN-date-factorytest.log when SN is known."""
    global _root_logger, _file_handler, _log_file_path
    if not sn or _root_logger is None:
        return

    date_str = datetime.now().strftime('%Y%m%d')
    new_path = f'/root/{sn}-{date_str}-factorytest.log'

    if new_path == _log_file_path:
        return

    # Swap file handler to new path
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    _root_logger.removeHandler(_file_handler)
    _file_handler.close()

    try:
        if os.path.exists(_log_file_path):
            os.rename(_log_file_path, new_path)
    except Exception:
        pass

    _file_handler = logging.FileHandler(new_path, mode='a')
    _file_handler.setLevel(logging.INFO)
    _file_handler.setFormatter(formatter)
    _root_logger.addHandler(_file_handler)
    _log_file_path = new_path


def save_dmesg_to_log():
    """Save dmesg output to the log file. Call this after all tests finish."""
    logger = _init_root_logger().getChild('dmesg')
    logger.info('=' * 60)
    logger.info('--- dmesg begin ---')
    try:
        result = subprocess.run(['dmesg'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        for line in result.stdout.splitlines():
            logger.info('[dmesg] ' + line)
    except Exception as e:
        logger.error(f'Failed to capture dmesg: {e}')
    logger.info('--- dmesg end ---')


class LoggerManager:
    def __init__(self, name='LoggerManager', console_level=logging.INFO):
        # Ensure the shared root logger is initialised
        root = _init_root_logger(console_level)
        # Return a child logger so %(name)s still shows the caller's name
        self.logger = root.getChild(name)

    def get_logger(self):
        return self.logger
