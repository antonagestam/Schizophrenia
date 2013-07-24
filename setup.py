#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages

setup(
    name='Schizophrenia',
    version='0.0.1',
    description='A Django Storage with multiple personalitie... storage '
                'backends. Created for the purpose of migrating from one '
                'default storage backend to another.',
    long_description=open('README.md').read(),
    author='Anton Agestam',
    author_email='msn@antonagestam.se',
    packages=find_packages(),
    url='https://github.com/antonagestam/Schizophrenia/',
    license='The MIT License',
    include_package_data=True,
    install_requires=['Django>=1.4'], )
