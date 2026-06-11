from unittest import TestCase

import subprocess

class UARTTest(TestCase):
    LANGUAGES = {
        'zh': {
            'UARTTest': '串口',
            'test_uart': '串口输出正常'
        },
        'en': {
            'UARTTest': 'UART',
            'test_uart': 'Normal UART output',
            'title': 'UART Test'
        }
    }

    def test_uart(self):
        pass
