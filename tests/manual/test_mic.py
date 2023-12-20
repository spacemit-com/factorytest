from unittest import TestCase

import threading
import time

from cricket.manual import SimpleManualTestWindow

class MICTest(TestCase):
    LANGUAGES = {
        'zh': {
            'MICTest': '麦克风',
            'test_mic': '录音回放',
            'title': '麦克风',
            'test_step': '''1. 设备自动播放一段铃声，并开启录音
2. 回放
3. 判断回放铃声是否符合预期'''
        },
        'en': {
            'MICTest': 'Mic',
            'test_mic': 'Record and playback',
            'title': 'Mic',
            'test_step': '''1. 设备自动播放一段铃声，并开启录音
2. 回放
3. 判断回放铃声是否符合预期
'''
        }
    }

    def _test_routine(self):
        self.exit_event = threading.Event()
        while not self.exit_event.is_set():
            time.sleep(1)

    def _stop_routine(self):
        self.exit_event.set()

    def test_mic(self):
        window = SimpleManualTestWindow(self._test_routine,
                                        self._stop_routine,
                                        self.LANGUAGES)
        self.assertEqual(window.determine(), True)