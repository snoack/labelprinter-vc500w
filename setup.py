#!/usr/bin/env python3

from pathlib import Path

from setuptools import setup


setup(
    name='labelprinter-vc500w',
    version='1.0',
    description='CLI for controlling Brother VC-500W label printers over TCP/IP',
    long_description=Path('README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    author='Sebastian Noack',
    author_email='sebastian.noack@gmail.com',
    url='https://github.com/snoack/labelprinter-vc500w',
    keywords=[
        'brother',
        'printer',
        'label-printer',
        'vc-500w',
        'cli',
    ],
    license='AGPL-3.0-or-later',
    python_requires='>=3.5',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
    ],
    packages=['labelprinter'],
    install_requires=['Pillow'],
    entry_points={
        'console_scripts': [
            'bclprinter=labelprinter.__main__:main',
        ],
    },
)
