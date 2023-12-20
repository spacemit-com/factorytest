from unittest import TestCase

class WiFiTest(TestCase):
    LANGUAGES = {
        'zh': {
            'WiFiTest': '无线网',
            'test_wifi': '搜索热点'
        },
        'en': {
            'WiFiTest': 'WiFi',
            'test_wifi': 'Hotspots Scan'
        }
    }

    def test_wifi(self):
        self.assertEqual(0, 0)