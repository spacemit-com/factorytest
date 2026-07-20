from unittest import TestCase

import subprocess

class DPDisplayTest(TestCase):
    LANGUAGES = {
        'zh': {
            'DPDisplayTest': 'DP 屏幕显示',
            'test_desktop': '正常显示桌面'
        },
        'en': {
            'DPDisplayTest': 'DP Display',
            'test_desktop': 'Normal desktop display',
            'title': 'DP Display Test'
        }
    }

    def test_desktop(self):
        pass
