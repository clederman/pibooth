#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='pibooth-share',
    version='1.0.0',
    description='Pibooth plugin to share photos via local web server and QR code',
    long_description=open('README.md').read() if __import__('os').path.isfile('README.md') else '',
    long_description_content_type='text/markdown',
    author='Philippe Le Guen',
    license='MIT',
    packages=['pibooth_share'],
    python_requires='>=3.10',
    install_requires=[
        'pibooth>=3.0.0',
        'qrcode[pil]>=7.0',
    ],
    entry_points={
        'pibooth': ['pibooth_share = pibooth_share.plugin:SharePlugin'],
    },
    zip_safe=False,
)
