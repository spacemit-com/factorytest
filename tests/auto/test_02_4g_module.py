from unittest import TestCase

import os
import subprocess
#import usb.core

class USB4GModuleTest(TestCase):
    LANGUAGES = {
        'zh': {
            'USB4GModuleTest': '4G模块',
            'test_read_product': '读取型号'
        },
        'en': {
            'USB4GModuleTest': '4G Moduel',
            'test_read_product': 'Read product name'
        }
    }

    def test_read_product(self):
        product_file = '/sys/devices/platform/soc/c0980100.ehci1/usb1/1-1/product'
        self.assertTrue(os.path.exists(product_file))