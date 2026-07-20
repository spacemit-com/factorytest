from unittest import TestCase

import os
import subprocess

class SpiNorTest(TestCase):
    LANGUAGES = {
        'zh': {
            'SpiNorTest': 'Spi Nor',
            'test_read_model': '读取型号'
        },
        'en': {
            'SpiNorTest': 'Spi Nor',
            'test_read_model': 'Read model'
        }
    }

    def test_read_model(self):
        model_file = '/dev/mtd0'
        self.assertTrue(os.path.exists(model_file))
