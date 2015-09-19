#!/usr/bin/env python
from setuptools import setup

setup(
    name='sphotiklib',
    version='1.0',
    description='Avro-like Bangla phonetic parser',
    long_description=(
        'A phonetic parser that parses Bangla text written in Roman'
        ' characters. Understands an avro-like (but not 100% compatible)'
        ' rule-set.'),
    author='Titon Barua',
    author_email='titon@vimmanaic.com',
    license='MIT',
    url='',
    packages=['sphotiklib'],
    package_data={
        'sphotiklib': ['rules/avro/*.txt']},
    test_suite='sphotiklib.parser._TestParser',)
