from unittest import TestCase

import os
import subprocess
#import usb.core

class minipcie_ssdTest(TestCase):
    LANGUAGES = {
        'zh': {
            'minipcie_ssdTest': 'MINIPCIE SSD',
            'test_read_model': '读取容量'
        },
        'en': {
            'minipcie_ssdTest': 'MINIPCIE SSD',
            'test_read_model': 'Read size'
        }
    }

    def test_read_model(self):
        #size_file = '/sys/class/block/sda/size'
        #self.assertTrue(os.path.exists(model_file))
        with open('/sys/class/block/sda/size', 'r') as file:
            size = int(file.read().strip())
        self.assertGreater(size, 65536)
