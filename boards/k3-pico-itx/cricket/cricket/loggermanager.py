
import logging
import logging.handlers
import subprocess
import sys

# Module-level singleton: one root logger shared by all callers
_root_logger = None


def _init_root_logger(console_level=logging.INFO):
    global _root_logger
    if _root_logger is not None:
        return _root_logger

    logger = logging.getLogger('factorytest')
    logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if this function is somehow called twice
    if logger.handlers:
        _root_logger = logger
        return _root_logger

    # Simple format: just "LEVEL - message"
    formatter = logging.Formatter('%(levelname)s - %(message)s')

    # File handler only – overwrite each run ('w')
    file_handler = logging.FileHandler('/root/factorytest.log', mode='w')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _root_logger = logger
    return _root_logger


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