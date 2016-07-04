#!/usr/bin/env python

from setuptools import setup

from setuputils import find_version


setup(
    name='decoUtils',
    version=find_version('decoUtils/__init__.py'),
    description='the collections of decorator',
    author='x r',
    packages=['decoUtils'],
    py_modules=['setuputils']
)
