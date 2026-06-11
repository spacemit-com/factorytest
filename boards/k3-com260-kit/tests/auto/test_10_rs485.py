from unittest import TestCase
import os
import time
import select


class RS485Test(TestCase):
    PATTERN = b"0x5a5a5a5a"
    TIMEOUT = 2.0

    LANGUAGES = {
        'zh': {
            'RS485Test': 'RS485',
            'test_rs485_loopback': '环回测试'
        },
        'en': {
            'RS485Test': 'RS485',
            'test_rs485_loopback': 'Loopback Test'
        }
    }

    def _write_sysfs(self, path, data):
        with open(path, "w") as f:
            f.write(str(data))

    def _ensure_gpio(self, gpio_num):
        gpio_path = f"/sys/class/gpio/gpio{gpio_num}"
        if not os.path.exists(gpio_path):
            try:
                self._write_sysfs("/sys/class/gpio/export", gpio_num)
            except Exception:
                if not os.path.exists(gpio_path):
                    raise
        self._write_sysfs(f"{gpio_path}/direction", "out")

    def _set_gpio(self, gpio_num, value):
        self._write_sysfs(f"/sys/class/gpio/gpio{gpio_num}/value", int(value))

    def _test_direction(self, send_dev, recv_dev, gpio105, gpio106):
        self._set_gpio(105, gpio105)
        self._set_gpio(106, gpio106)
        time.sleep(0.05)

        fd_send = os.open(send_dev, os.O_RDWR | os.O_NOCTTY)
        fd_recv = os.open(recv_dev, os.O_RDWR | os.O_NOCTTY)

        try:
            os.write(fd_send, self.PATTERN + b"\n")
            
            end = time.time() + self.TIMEOUT
            got = b""
            while time.time() < end:
                r, _, _ = select.select([fd_recv], [], [], max(0, end - time.time()))
                if r:
                    chunk = os.read(fd_recv, 1024)
                    if chunk:
                        got += chunk
                        if len(got) >= len(self.PATTERN):
                            break

            if self.PATTERN not in got.strip():
                raise AssertionError(f"Data mismatch on {recv_dev}: {got!r}")
        finally:
            os.close(fd_send)
            os.close(fd_recv)

    def test_rs485_loopback(self):
        try:
            self._ensure_gpio(105)
            self._ensure_gpio(106)
            self._test_direction("/dev/ttyS5", "/dev/ttyS4", 1, 0)
            self._test_direction("/dev/ttyS4", "/dev/ttyS5", 0, 1)
        except Exception as e:
            self.fail(f"RS485 test failed: {e}")
