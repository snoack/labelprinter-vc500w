#!/usr/bin/env python3

from pathlib import Path

from setuptools import setup


setup(
    name='labelprinter-vc500w',
    version='0.1',
    description='CLI for controlling Brother VC-500W label printers over TCP/IP',
    long_description=Path('README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    url='https://gitlab.com/lenchan139/labelprinter-vc500w',
    license='AGPL-3.0-or-later',
    packages=['labelprinter'],
    install_requires=['Pillow'],
    entry_points={
        'console_scripts': [
            'bclprinter=labelprinter.__main__:main',
        ],
    },
)
