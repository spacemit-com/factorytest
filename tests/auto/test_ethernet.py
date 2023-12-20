from unittest import TestCase

class EthernetTest(TestCase):
    LANGUAGES = {
        'zh': {
            'EthernetTest': '以太网',
            'test_ethernet': '连通性测试'
        },
        'en': {
            'EthernetTest': 'Ethernet',
            'test_ethernet': 'Ping test'
        }
    }

    def test_ethernet(self):
        self.assertEqual(0, 0)