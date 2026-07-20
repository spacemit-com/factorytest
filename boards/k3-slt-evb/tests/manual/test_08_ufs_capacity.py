from unittest import TestCase
import os


class UFSCapacityTest(TestCase):
    LANGUAGES = {
        'zh': {
            'UFSCapacityTest': 'UFS容量',
            'test_capacity': '容量检测'
        },
        'en': {
            'UFSCapacityTest': 'UFS Capacity',
            'test_capacity': 'Capacity Detection'
        }
    }

    def test_capacity(self):
        """Read and display UFS capacity from /sys/class/block/sda/size"""
        ufs_size = self.get_capacity()
        print(f'\nUFS Capacity: {ufs_size} GB')
        self.assertGreater(ufs_size, 0, 'UFS capacity should be greater than 0')

    @classmethod
    def get_capacity(cls):
        """Get UFS size in GB from /sys/class/block/sda/size"""
        path = '/sys/class/block/sda/size'
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    # Size is in 512-byte blocks, convert to GB
                    size_blocks = int(f.readline().strip())
                    return round(size_blocks / 1000 / 1000 / 2, 1)
            else:
                print(f'UFS device path not found: {path}')
                return 0
        except Exception as e:
            print(f'Error reading UFS capacity: {e}')
            return 0