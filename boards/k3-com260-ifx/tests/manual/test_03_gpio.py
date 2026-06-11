from unittest import TestCase

import subprocess

class GPIOTest(TestCase):
    LANGUAGES = {
        'zh': {
            'GPIOTest': '40 Pin连接器',
            'test_gpio': '开灯'
        },
        'en': {
            'GPIOTest': '40 Pin Connector',
            'test_gpio': 'Turn on light'
        }
    }

    def test_gpio(self):
        try:
            gpios = '0 1 60 61 62 63 70 71 82 83 104 105 106 107 111 112 113 114 118 119 120 121 122 123 124 125 126 127'
            cmd = f'/opt/factorytest/utils/gpio.sh {gpios}'
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        except:
            self.fail('Create gpio subprocess fail')

