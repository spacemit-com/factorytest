from unittest import TestCase

import os

class StorageTest(TestCase):
    LANGUAGES = {
        'zh': {
            'StorageTest': '存储',
            'test_rw': '读写测试'
        },
        'en': {
            'StorageTest': 'Storage',
            'test_rw': 'Read and write test'
        }
    }

    def _write_data(self, path, size):
        try:
            with open(path, 'wb') as file:
                data = bytearray(os.urandom(size))
                return file.write(data)
        except Exception as e:
            print(f'{e}')
            return -1

    def _read_data(self, path, size):
        try:
            with open(path, 'rb') as file:
                if file.read(size):
                    return 0
                else:
                    return -1
        except:
            return -1

    def test_rw(self):
        path = os.path.expanduser('~') + '/tmp.bin'
        size = 100 * 1024 * 1024
        self.assertEqual(self._write_data(path, size), size)
        self.assertEqual(self._read_data(path, size), 0)