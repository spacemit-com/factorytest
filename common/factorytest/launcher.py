"""
Launcher module.
Detects the current board and launches the factory test UI
by setting up the correct Python path and working directory.
"""

import os
import sys


def main():
    # Resolve the installation root: /opt/factorytest
    launcher_path = os.path.realpath(__file__)
    # common/factorytest/launcher.py -> go up two levels to reach install root
    install_root = os.path.dirname(os.path.dirname(os.path.dirname(launcher_path)))

    # Add board_detect location to path
    sys.path.insert(0, os.path.dirname(launcher_path))
    from board_detect import detect_board

    board_name = detect_board()
    if board_name is None:
        sys.stderr.write(
            'ERROR: Could not detect board from /proc/device-tree/compatible.\n'
            'Supported boards: k3-pico-itx, k3-com260, k3-com260-kit, k3-com260-ifx\n'
        )
        sys.exit(1)

    # After installation, cricket/ and tests/ are directly under install_root.
    # The boards/<name>/ directory layout only exists in the source tree.
    cricket_path = os.path.join(install_root, 'cricket')
    tests_path   = os.path.join(install_root, 'tests')

    if not os.path.isdir(cricket_path):
        sys.stderr.write(f'ERROR: cricket directory not found: {cricket_path}\n')
        sys.exit(1)

    if not os.path.isdir(tests_path):
        sys.stderr.write(f'ERROR: tests directory not found: {tests_path}\n')
        sys.exit(1)

    # Set up Python path: cricket framework under install_root
    sys.path.insert(0, cricket_path)
    sys.path.insert(0, install_root)
    # Add common/factorytest so tests can import board_detect
    sys.path.insert(0, os.path.join(install_root, 'common', 'factorytest'))

    # Change to tests directory so cricket unittest discoverer finds test files
    os.chdir(tests_path)
    sys.path.insert(0, tests_path)

    # Launch cricket unittest runner
    from cricket.unittest.__main__ import main as cricket_main
    cricket_main()


if __name__ == '__main__':
    main()
