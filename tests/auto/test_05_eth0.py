from unittest import TestCase

import os
import time
import socket
import struct
import fcntl
import subprocess

from dns.resolver import Resolver

class Eth0Test(TestCase):
    LANGUAGES = {
        'zh': {
            'Eth0Test': '网口',
            'test_ping': 'ping'
        },
        'en': {
            'Eth0Test': '网口',
            'test_ping': 'ping'
        }
    }

    def get_operstate(self, ifname: str):
        operstate = f'/sys/class/net/{ifname}/operstate'

        with open(operstate, 'r') as f:
            return f.read().strip()

    def get_ip(self, ifname: str):
        try:
            result = subprocess.run(f'ip -4 addr show {ifname}', capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.startswith('inet '):
                        ip = line.split()[1].split('/')[0]
                        if not ip.startswith('169.254.'):
                            return ip
        except:
            pass
        return None

    def test_ping(self):
        
        timeout_wait_interface = 30
        i = 0
        while i < timeout_wait_interface:
            if os.path.exists('/sys/class/net/eth0'):
                break
            time.sleep(1)
            i += 1
        
        if i == timeout_wait_interface:
            self.fail('Network interface eth0 not found')
        
        interface_file = '/sys/class/net/eth0/device/interface'
        ifname = 'eth0'

        if os.path.exists(interface_file):
            try:
                with open(interface_file, 'r') as f:
                    content = f.read().strip()
                    if 'CDC' in content and 'ECM' in content:
                        ifname = 'eth1'
                        print(f'Detected CDC ECM interface, using {ifname}')
            except:
                pass
        
        i = 0
        while i < timeout_wait_interface:
            if os.path.exists(f'/sys/class/net/{ifname}'):
                break
            time.sleep(1)
            i += 1
        
        if i == timeout_wait_interface:
            self.fail(f'Network interface {ifname} not found')
        
        site = 'www.baidu.com'
        ping = f'ping -I {ifname} -c 10 {site}'
        timeout = 20

        i = 0
        while i < timeout:
            if self.get_operstate(ifname) == 'up':
                break

            time.sleep(1)
            i += 1

        if i == timeout:
            self.fail('Get carrier imeout')

        i = 0
        while i < timeout:
            ip = self.get_ip(ifname)
            if ip:
                print(f'{ifname}: {ip}')
                break
            else:
                time.sleep(1)
                i += 1

        if i == timeout:
            self.fail('Get ip timeout')

        i = 0
        while i < timeout:
            try:
                resolver = Resolver()
                answer = resolver.query(site)
                if answer:
                    print(f'nameserver: {answer.nameserver}')
                    break
            except:
                time.sleep(1)
                i += 1

        if i == timeout:
            self.fail('DNS query timeout')

        try:
            result = subprocess.run(ping, capture_output=True, shell=True, timeout=timeout)
            self.assertEqual(result.returncode, 0)
        except subprocess.TimeoutExpired:
            self.fail('Ping timeout')