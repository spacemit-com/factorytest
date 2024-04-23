from unittest import TestCase

import os
import subprocess

class EEPROM_Test(TestCase):
    LANGUAGES = {
        'zh': {
            'EEPROM_Test': 'IIC EEPROM',
            'test_iic_eeprom': '读取数据'
        },
        'en': {
            'EEPROM_Test': 'IIC EEPROM',
            'test_iic_eeprom': 'read data'
        }
    }

    def test_iic_eeprom(self):
        # 执行i2cget命令，读取I2C设备的数据
        result = subprocess.run(['i2cget', '-y', '2', '0x50', '0x01'], capture_output=True, text=True)
        
        # 验证命令执行结果是否成功
        self.assertEqual(result.returncode, 0)
        
        # 验证读取到的数据是否符合预期
        expected_data = '0x6c'  # 假设期望读取到的数据是0x6c
        self.assertEqual(result.stdout.strip(), expected_data)