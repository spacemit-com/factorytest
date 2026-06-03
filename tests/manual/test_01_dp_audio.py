from unittest import TestCase

import subprocess

class DPAudioTest(TestCase):
    LANGUAGES = {
        'zh': {
            'DPAudioTest': 'DP Audio',
            'test_dp_audio': '播放一段音乐'
        },
        'en': {
            'DPAudioTest': 'DP Audio',
            'test_dp_audio': 'Play a piece of music'
        }
    }

    def test_dp_audio(self):
        try:
            music_file = '/opt/factorytest/res/canon.wav'
            cmd = f'aplay -Dhw:1,0 -r 48000 -f S16_LE {music_file}'
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
        except:
            self.fail('Create subprocess fail')
