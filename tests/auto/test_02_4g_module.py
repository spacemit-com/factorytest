from unittest import TestCase

import os
import subprocess
#import usb.core

class minipcie_4GTest(TestCase):
    LANGUAGES = {
        'zh': {
            'minipcie_4GTest': '4G模块',
            'test_read_model': '设备是否枚举'
        },
        'en': {
            'minipcie_4GTest': '4G moduel',
            'test_read_model': 'Whether Enumeration OK'
        }
    }

    def test_read_model(self):
     #   model_file = '/sys/class/nvme/nvme0/model'
     #   self.assertTrue(os.path.exists(model_file))
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        output = result.stdout

        # 判断输出结果中是否包含设备信息
        self.assertIn('Bus 001 Device 002: ID 2c7c:0125', output)