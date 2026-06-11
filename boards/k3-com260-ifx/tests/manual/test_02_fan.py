from unittest import TestCase

import subprocess

class FanTest(TestCase):
    LANGUAGES = {
        'zh': {
            'FanTest': '风扇',
            'test_speed': '上电运转'
        },
        'en': {
            'FanTest': 'Fan',
            'test_speed': 'Rotate when powered on',
            'title': 'Fan'
        }
    }

    def test_speed(self):
        pass
