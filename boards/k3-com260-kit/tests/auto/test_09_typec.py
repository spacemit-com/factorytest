from unittest import TestCase

import subprocess
import os

class TYPECTest(TestCase):
    LANGUAGES = {
        'zh': {
            'TYPECTest': 'Type-C',
            'test_connect': '连接'
        },
        'en': {
            'TYPECTest': 'Type-C',
            'test_connect': 'Connect'
        }
    }

    def test_connect(self):
        try:
            devices_path = '/sys/bus/usb/devices/'
            usb_buses = [d for d in os.listdir(devices_path) if d.startswith('usb') and d[3:].isdigit()]
            
            target_bus = None
            for bus in usb_buses:
                bus_path = os.path.join(devices_path, bus)
                devspec_path = os.path.join(bus_path, 'devspec')
                speed_path = os.path.join(bus_path, 'speed')
                
                if os.path.exists(devspec_path) and os.path.exists(speed_path):
                    with open(devspec_path, 'r') as f:
                        devspec = f.read().strip()
                    with open(speed_path, 'r') as f:
                        speed = f.read().strip()
                    
                    if 'usb3@cad00000' in devspec and speed == '5000':
                        target_bus = bus
                        break
            
            if not target_bus:
                self.fail('No USB bus found with devspec containing usb3@cad00000 and speed 5000')
            
            bus_num = target_bus[3:]
            product_path = os.path.join(devices_path, target_bus, f'{bus_num}-1', 'product')
            
            if not os.path.exists(product_path):
                self.fail(f'Product file not found at {product_path}')

        except Exception as e:
            self.fail(f'Type-C test failed: {str(e)}')
