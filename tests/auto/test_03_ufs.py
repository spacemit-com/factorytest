from unittest import TestCase

import os

class UFSTest(TestCase):
    LANGUAGES = {
        'zh': {
            'UFSTest': 'UFS',
            'test_identify': '识别'
        },
        'en': {
            'UFSTest': 'UFS',
            'test_identify': 'Identify'
        }
    }

    def test_identify(self):
        block_file = '/sys/class/block/sda'
        self.assertTrue(os.path.exists(block_file))
