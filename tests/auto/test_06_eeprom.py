from unittest import TestCase

import os
import subprocess

class EEPROM_Test(TestCase):
    LANGUAGES = {
        'zh': {
            'EEPROM_Test': 'IIC EEPROM',
            'test_iic_eeprom': '检测设备'
        },
        'en': {
            'EEPROM_Test': 'IIC EEPROM',
            'test_iic_eeprom': 'detect device'
        }
    }

    def test_iic_eeprom(self):
        # 执行i2cget命令，读取I2C设备的数据
        # result = subprocess.run(['i2cget', '-y', '2', '0x50', '0x01'], capture_output=True, text=True)
        
        # 验证命令执行结果是否成功
        # self.assertEqual(result.returncode, 0)
        
        # 验证读取到的数据是否符合预期
        # expected_data = '0x6c'  # 假设期望读取到的数据是0x6c
        # self.assertEqual(result.stdout.strip(), expected_data)
        dev_file = '/sys/class/i2c-adapter/i2c-2/2-0050'
        self.assertTrue(os.path.exists(dev_file))