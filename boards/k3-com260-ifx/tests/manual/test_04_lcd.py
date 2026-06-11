from unittest import TestCase

import subprocess
import os
import re

class LCDTest(TestCase):
    LANGUAGES = {
        'zh': {
            'LCDTest': 'MIPI屏',
            'test_lcd': '彩色条纹'
        },
        'en': {
            'LCDTest': 'MIPI Screen',
            'test_lcd': 'Color Bar'
        }
    }

    def test_lcd(self):
        try:
            drm_path = '/sys/class/drm'
            dsi_device = next((e for e in os.listdir(drm_path) if 'DSI' in e and e.startswith('card')), None)
            if not dsi_device:
                self.fail('DSI device not found')
            
            card_num = re.match(r'card(\d+)-', dsi_device).group(1)
            stdout = subprocess.check_output(f'modetest -M spacemit -D /dev/dri/card{card_num} | head -n 10', 
                                            shell=True, text=True)
            
            crtc_id = next((line.split()[1] for line in stdout.split('\n') if 'DSI' in line and len(line.split()) >= 2), None)
            if not crtc_id or crtc_id == '0':
                self.fail(f'Failed to get valid crtc ID, output: {stdout}')
            
            with open(f'{drm_path}/{dsi_device}/connector_id', 'r') as f:
                connector_id = f.read().strip()
            
            if not connector_id:
                self.fail('Failed to read connector_id')
            
            subprocess.Popen(f'modetest -M spacemit -s {connector_id}@{crtc_id}:800x480', 
                           shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            self.fail(f'LCD test failed: {str(e)}')
