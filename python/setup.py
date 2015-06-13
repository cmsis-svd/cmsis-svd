#!/usr/bin/env python
#
# Copyright 2015 Paul Osborne <osbpau@gmail.com>
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

import os
import shutil
from setuptools import setup, find_packages

THIS_DIR = os.path.dirname(__file__)
DATA_DST_DIR = os.path.join(THIS_DIR, "cmsis_svd", "data")
DATA_SRC_DIR = os.path.join(THIS_DIR, "..", "data")

# for distribution we want to include the SVD data, so we copy
# over the tree if it exists
if os.path.exists(DATA_SRC_DIR):
    print("Copying over data files for distribution...")
    shutil.rmtree(DATA_DST_DIR, ignore_errors=True)
    shutil.copytree(DATA_SRC_DIR, DATA_DST_DIR)


def get_long_description():
    long_description = open('README.md').read()
    try:
        import subprocess
        import pypandoc
        long_description = pypandoc.convert('README.md', 'rst')
        open("README.rst", "w").write(long_description)
    except:
        if os.path.exists("README.rst"):
            long_description = open("README.rst").read()
        else:
            print("Could not find pandoc or convert properly")
            print("  make sure you have pandoc (system) and pyandoc (python module) installed")

    return long_description


setup(
    name="cmsis-svd",
    version="0.1",
    url="https://github.com/posborne/cmsis-svd",
    description="CMSIS SVD data files and parser",
    long_description=get_long_description(),
    author="Paul Osborne",
    author_email="osbpau@gmail.com",
    license="Apache 2.0",
    classifiers=[
        "Development Status :: 3 - Alpha",
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
        'six',
    ],
    packages=find_packages(),
    include_package_data=True,
)
