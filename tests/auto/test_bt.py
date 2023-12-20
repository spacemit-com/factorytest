from unittest import TestCase

class BTTest(TestCase):
    LANGUAGES = {
        'zh': {
            'BTTest': '蓝牙',
            'test_bt': '搜索设备'
        },
        'en': {
            'BTTest': 'BT',
            'test_bt': 'Device Scan'
        }
    }

    def test_bt(self):
        self.assertEqual(0, 0)