#!/usr/bin/env python
#
# Copyright 2015-2024 cmsis-svd Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import ast
import os
import re
from setuptools import setup, find_packages


def read_version(filename):
    regex = re.compile(r'__version__\s+=\s+(.*)')
    with open(filename, 'rb') as f:
        return str(ast.literal_eval(regex.search(
            f.read().decode('utf-8')).group(1)))


def get_long_description():
    return open('README.md').read()


setup(
    name="cmsis-svd",
    version=read_version(os.path.join('cmsis_svd/__init__.py')),
    url="https://github.com/cmsis-svd/cmsis-svd",
    description="CMSIS SVD parser",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="cmsis-svd Authors",
    author_email="",
    license="Apache 2.0",
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Topic :: System :: Hardware",
        "Topic :: System :: Boot :: Init",
        "Topic :: System :: Hardware :: Hardware Drivers",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Embedded Systems",
        "Topic :: System :: Operating System Kernels",
        "Topic :: Utilities",
        "Topic :: Text Processing :: Markup",
    ],
    install_requires=[
        'six>=1.10',
        'lxml',
    ],
    extras_require={
        'DEV': [
            'nose2',
        ]
    },
    package_data={
        'cmsis_svd': ['py.typed'],
    },
    packages=find_packages(),
)
