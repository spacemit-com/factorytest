"""
Board detection module.
Reads /proc/device-tree/compatible to identify the current board.
"""

import os

# Mapping from device-tree compatible string to board directory name
COMPATIBLE_MAP = {
    'spacemit,k3-pico-itx':       'k3-pico-itx',
    'spacemit,k3-com260':         'k3-com260',
    'spacemit,k3-com260-kit-v02': 'k3-com260-kit',
    'spacemit,k3-com260-ifx':     'k3-com260-ifx',
    'spacemit,k3-slt':            'k3-slt',
}

COMPATIBLE_PATH = '/proc/device-tree/compatible'


def get_compatible_strings():
    """Read and return all compatible strings from device-tree."""
    try:
        with open(COMPATIBLE_PATH, 'rb') as f:
            data = f.read()
        # Compatible strings are null-separated
        return [s for s in data.decode('utf-8', errors='replace').split('\x00') if s]
    except FileNotFoundError:
        return []


def detect_board():
    """
    Detect the current board by matching device-tree compatible strings.
    Returns the board directory name (e.g. 'k3-com260'), or None if not found.
    """
    compatibles = get_compatible_strings()
    for compat in compatibles:
        if compat in COMPATIBLE_MAP:
            return COMPATIBLE_MAP[compat]
    return None


def is_buildroot():
    """
    Return True if running on a Buildroot system, False on Bianbu (Ubuntu).

    Detection is based on /etc/os-release:
      - Buildroot images contain 'Buildroot'
      - Bianbu images contain 'Bianbu'
    Falls back to True (assume Buildroot) if the file is missing or unreadable.
    """
    os_release = '/etc/os-release'
    try:
        with open(os_release, 'r') as f:
            content = f.read()
        if 'Buildroot' in content:
            return True
        if 'Bianbu' in content:
            return False
        return True
    except OSError:
        return True
