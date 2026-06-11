from unittest import TestCase

import subprocess
import os
import tempfile
import time
import re
import shutil

class CAN3_4Test(TestCase):
    LANGUAGES = {
        'zh': {
            'CAN3_4Test': 'CAN3与CAN4',
            'test_connect': '通路'
        },
        'en': {
            'CAN3_4Test': 'CAN3 and CAN4',
            'test_connect': 'Connect'
        }
    }

    def _run(self, cmd, **kwargs):
        return subprocess.run(cmd, check=True, **kwargs)

    def test_connect(self):
            tmpdir = tempfile.mkdtemp(prefix='can_test_')
            logfile = os.path.join(tmpdir, 'candump.log')
            candump_procs = []
            fds = []

            try:
                # bring down interfaces first (in case they are already up)
                subprocess.run(["ip", "link", "set", "can3", "down"], check=False)
                subprocess.run(["ip", "link", "set", "can4", "down"], check=False)
                
                # configure and bring up interfaces
                self._run(["ip", "link", "set", "can3", "type", "can", "bitrate", "1000000", "fd", "off"])
                self._run(["ip", "link", "set", "can4", "type", "can", "bitrate", "1000000", "fd", "off"])
                self._run(["ip", "link", "set", "can3", "up"])
                self._run(["ip", "link", "set", "can4", "up"])

                # start candump processes logging to the same file
                fd1 = open(logfile, 'a+')
                fd2 = open(logfile, 'a+')
                fds.extend([fd1, fd2])

                p1 = subprocess.Popen(["candump", "can3"], stdout=fd1, stderr=subprocess.DEVNULL, start_new_session=True)
                p2 = subprocess.Popen(["candump", "can4"], stdout=fd2, stderr=subprocess.DEVNULL, start_new_session=True)
                candump_procs.extend([p1, p2])

                # helper to read new content since an offset
                def read_new(path, offset):
                    with open(path, 'r') as rf:
                        rf.seek(offset)
                        return rf.read()

                # allow candump to initialize
                time.sleep(0.5)

                # First test: send on can3
                offset = os.path.getsize(logfile)
                self._run(["cansend", "can3", "001#a5a5a5a5"])
                time.sleep(0.8)
                out1 = read_new(logfile, offset)

                patt_can3 = re.compile(r'\bcan3\s+001\s+\[4\]\s+A5(?:\s+A5){3}', re.IGNORECASE)
                patt_can4 = re.compile(r'\bcan4\s+001\s+\[4\]\s+A5(?:\s+A5){3}', re.IGNORECASE)

                if not (patt_can4.search(out1) and patt_can3.search(out1)):
                    self.fail('CAN test failed after sending on can3: expected frames not observed.\nLog excerpt:\n%s' % out1)

                # Second test: send on can4
                offset = os.path.getsize(logfile)
                self._run(["cansend", "can4", "001#a5a5a5a5"])
                time.sleep(0.8)
                out2 = read_new(logfile, offset)

                if not (patt_can4.search(out2) and patt_can3.search(out2)):
                    self.fail('CAN test failed after sending on can4: expected frames not observed.\nLog excerpt:\n%s' % out2)

            except subprocess.CalledProcessError as e:
                self.fail(f'Command failed: {e}')
            except FileNotFoundError as e:
                self.fail(f'Required tool not found: {e}')
            finally:
                # cleanup candump processes and fds
                for p in candump_procs:
                    try:
                        p.terminate()
                        p.wait(timeout=1)
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass

                for fd in fds:
                    try:
                        fd.close()
                    except Exception:
                        pass

                try:
                    shutil.rmtree(tmpdir)
                except Exception:
                    pass