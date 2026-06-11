from unittest import TestCase
import subprocess
import re
import time
import os

LOG_FILE = '/tmp/csi1_test_imx219.log'


class CSI0Test(TestCase):
    LANGUAGES = {
        'zh': {
            'CSI0Test': 'Camera0',
            'test_channel': '通路测试'
        },
        'en': {
            'CSI0Test': 'Camera0',
            'test_channel': 'Channel Test'
        }
    }

    def test_channel(self):
        subprocess.run('killall -q csi-test', shell=True)

        proc = subprocess.Popen(
            f'csi-test -n 0 -c 1 -a 1 > {LOG_FILE} 2>&1',
            shell=True,
            stdin=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )

        # 轮询日志文件，最多等待 15 秒
        deadline = time.time() + 15
        found = False
        last_output = ''
        while time.time() < deadline:
            time.sleep(1)
            try:
                with open(LOG_FILE, 'r', errors='replace') as f:
                    last_output = f.read()
            except FileNotFoundError:
                continue
            if re.search(r'csi1 frame\(\d+\) done timeStamp', last_output):
                found = True
                break

        subprocess.run('killall -q csi-test', shell=True)
        time.sleep(1)

        if not found:
            self.fail(f'csi1 frame done timeStamp not found:\n{last_output}')
