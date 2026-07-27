from unittest import TestCase

import os

class TFCardTest(TestCase):
    LANGUAGES = {
        'zh': {
            'TFCardTest': 'TF卡',
            'test_identify': '识别'
        },
        'en': {
            'TFCardTest': 'TF Card',
            'test_identify': 'Identify'
        }
    }

    def test_identify(self):
        block_file = '/sys/class/block/mmcblk0'
        self.assertTrue(os.path.exists(block_file))
