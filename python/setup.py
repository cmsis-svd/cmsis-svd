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

from setuptools import setup, find_packages

setup(
    name="cmsis-svd",
    version="0.1",
    description="CMSIS SVD data files and parser",
    author="Paul Osborne",
    author_email="osbpau@gmail.com",
    license="Apache 2.0",
    classifiers=[
        "Development Status :: 5 - Alpha",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
    ],
    install_requires=[
        'six',
    ],
    packages=find_packages(),
    include_package_data=True,
)
