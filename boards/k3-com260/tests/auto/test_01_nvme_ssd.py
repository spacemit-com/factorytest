from unittest import TestCase

import os
import time

class NVMeSSDTest(TestCase):
    LANGUAGES = {
        'zh': {
            'NVMeSSDTest': 'NVMe固态硬盘',
            'test_read_model': '读取型号'
        },
        'en': {
            'NVMeSSDTest': 'NVMe SSD',
            'test_read_model': 'Read model'
        }
    }

    def test_read_model(self):
        model_file = '/sys/class/nvme/nvme0/model'
        for _ in range(10):
            if os.path.exists(model_file):
                break
            time.sleep(1)
        self.assertTrue(os.path.exists(model_file))