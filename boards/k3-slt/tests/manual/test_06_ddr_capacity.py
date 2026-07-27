from unittest import TestCase


class DDRCapacityTest(TestCase):
    LANGUAGES = {
        'zh': {
            'DDRCapacityTest': 'DDR容量',
            'test_capacity': '容量检测'
        },
        'en': {
            'DDRCapacityTest': 'DDR Capacity',
            'test_capacity': 'Capacity Detection'
        }
    }

    def test_capacity(self):
        """Read and display DDR capacity from /proc/meminfo"""
        ddr_size = self.get_capacity()
        print(f'\nDDR Capacity: {ddr_size} GB')
        self.assertGreater(ddr_size, 0, 'DDR capacity should be greater than 0')

    @classmethod
    def get_capacity(cls):
        """Get DDR size in GB from /proc/meminfo"""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f.readlines():
                    if line.startswith('MemTotal:'):
                        # MemTotal is in KB, convert to GB
                        return round(int(line.split()[1]) / 1024 / 1024, 1)
        except Exception as e:
            print(f'Error reading DDR capacity: {e}')
            return 0
        return 0