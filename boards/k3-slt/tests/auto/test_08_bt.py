from unittest import TestCase

import subprocess

class BTTest(TestCase):
    LANGUAGES = {
        'zh': {
            'BTTest': '蓝牙',
            'test_scan': '扫描'
        },
        'en': {
            'BTTest': 'Bluetooth',
            'test_scan': 'Scan'
        }
    }

    def test_scan(self):
        # timeout: length * 1.28s + buffer time
        # devices: numrsp
        scan = 'hcitool -i hci0 scan --length=5 --numrsp=1'
        try:
            # Increase timeout to 20s to allow for BT initialization and scan completion
            proc = subprocess.run(scan, capture_output=True, text=True, shell=True, timeout=20)
            self.assertEqual(proc.returncode, 0, f"Scan failed with return code {proc.returncode}. stderr: {proc.stderr}")
            
            # Parse and display only device MAC and names
            lines = proc.stdout.strip().splitlines()
            devices = [line.strip() for line in lines if line.strip() and not line.strip().startswith('Scanning')]
            
            for device in devices:
                print(device)
            
            #self.assertGreater(len(proc.stdout.splitlines()), 1)
        except subprocess.TimeoutExpired:
            self.fail('Scan timeout after 20 seconds. Check if hci0 device is available and bluetooth is enabled.')
