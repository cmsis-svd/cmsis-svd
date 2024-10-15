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

from typing import Union
import asyncio
import contextvars
import functools
import os
import re
import json
import hashlib
import time
import random
import socket
import argparse
from urllib import request
from urllib.error import URLError

INDEX_JSON = 'index.json'
INDEX_MD5 = 'index.md5'

CMSIS_SVD_DATA_URL = ('https://raw.githubusercontent.com'
                      '/cmsis-svd/cmsis-svd-data/refs/heads/svd-indexer')
CMSIS_SVD_DATA_INDEX_JSON = f'{CMSIS_SVD_DATA_URL}/{INDEX_JSON}'
CMSIS_SVD_DATA_INDEX_MD5 = f'{CMSIS_SVD_DATA_URL}/{INDEX_MD5}'

LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
LOCAL_DATA_INDEX_JSON = os.path.join(LOCAL_DATA_DIR, INDEX_JSON)
LOCAL_DATA_INDEX_MD5 = os.path.join(LOCAL_DATA_DIR, INDEX_MD5)


async def to_thread(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)


class SvdDlError(Exception):
    pass


class SvdDl:
    def __init__(self):
        socket.setdefaulttimeout(2)
        self._svd_resource_matcher = re.compile(
            r'^([a-zA-Z0-9_-]*)(\.([a-zA-Z0-9_-]*)){0,3}$')

    @staticmethod
    def _get_file_hash(filename: Union[str, os.PathLike]) -> str:
        with open(filename, 'rb') as f:
            dl_hash = hashlib.md5(f.read()).hexdigest()
        return dl_hash

    @staticmethod
    def _get_hash_from_index_md5(filename: Union[str, os.PathLike]) -> str:
        with open(filename, 'r') as f:
            content = f.read()

        content = tuple(content.split(' '))

        if (len(content) != 2 or content[0] != 'index.json'
                or re.match(content[1], r'^[a-z0-9_-]{32}$')):
            raise SvdDlError('Invalid index.md5 file.')

        return content[1]

    @staticmethod
    def _urlretrieve_wrapper(url: str, filename: Union[str, os.PathLike],
                             retry: int = 5) -> None:
        retry_count = 0
        while True:
            try:
                request.urlretrieve(url, filename)
                return
            except (URLError, socket.timeout) as exc:
                retry_count += 1
                if retry_count == retry - 1:
                    raise exc
                else:
                    time.sleep(random.randrange(1, 5))

    def dl_svd_to_local(self, svd_path_part: str, svd_hash: str):
        svd_path = os.path.join(LOCAL_DATA_DIR, svd_path_part)
        doted_name = svd_path_part.replace("/", ".")[:-4]

        if os.path.exists(svd_path) and os.path.isfile(svd_path):
            if self._get_file_hash(svd_path) == svd_hash:
                print(f'[+] SVD already exist "{svd_path_part.replace("/", ".")}"')
                return
            else:
                print(f'[i] SVD already exist but hash differ "{doted_name}" Update')

        os.makedirs(os.path.dirname(svd_path), exist_ok=True)
        svd_url = f'{CMSIS_SVD_DATA_URL}/data/{svd_path_part}'
        print(f'[i] Downloading: "{doted_name}"')
        self._urlretrieve_wrapper(svd_url, svd_path)
        if self._get_file_hash(svd_path) != svd_hash:
            raise SvdDlError(f'Downloaded SVD file for "{doted_name}" is '
                             f'corrupted.')

    async def download_svd(self, download_string: str) -> None:
        download_files, download_packs = [], []
        os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
        print(f'[i] Downloading: index.md5')
        request.urlretrieve(CMSIS_SVD_DATA_INDEX_MD5, LOCAL_DATA_INDEX_MD5)
        print(f'[i] Downloading: index.json')
        request.urlretrieve(CMSIS_SVD_DATA_INDEX_JSON, LOCAL_DATA_INDEX_JSON)
        index_json_hash = self._get_file_hash(LOCAL_DATA_INDEX_JSON)
        index_json_hash_valid = self._get_hash_from_index_md5(LOCAL_DATA_INDEX_MD5)

        if index_json_hash != index_json_hash_valid:
            raise SvdDlError(f'"index.json" is corrupted.')

        with open(LOCAL_DATA_INDEX_JSON, 'r') as f:
            index_json = json.load(f)

        if download_string == 'ALL':
            for indexed, meta in index_json['data'].items():
                await to_thread(self.dl_svd_to_local, meta['path'], meta['hash'])
        else:
            svd_resources = download_string.split(',')

            for to_check in svd_resources:
                if self._svd_resource_matcher.match(to_check) is None:
                    raise SvdDlError(f'Invalid pattern for SVD resource "{to_check}"')

            for rsc in svd_resources:
                if rsc in index_json['data']:
                    download_files.append(rsc)
                else:
                    for indexed, indexed_hash in index_json['data'].items():
                        if indexed.startswith(rsc) and indexed[len(rsc)] == '.':
                            download_packs.append(rsc)
                            break

            for svd_file in download_files:
                self.dl_svd_to_local(svd_file, index_json['data'][svd_file])

            for svd_packs in download_packs:
                for indexed, indexed_hash in index_json['data'].items():
                    if indexed.startswith(svd_packs) and indexed[len(svd_packs)] == '.':
                        self.dl_svd_to_local(indexed, indexed_hash)


def main():
    parser = argparse.ArgumentParser(
        prog='svd-dl',
        description=f'SVD file downloader from the cmsis-svd project.'
    )

    subparsers = parser.add_subparsers(required=True, dest='svd_dl_subparser')
    sub_parser_dl = 'download'
    parser_dl = subparsers.add_parser(sub_parser_dl, help='download SVD file')
    parser_dl.add_argument(
        '--svd-resources', required=True,
        help='List of svd resources with doted notation. '
             'ex: Atmel.AT91SAM9CN11,Nordic')

    script_args = parser.parse_args()

    if script_args.svd_dl_subparser == sub_parser_dl:
        asyncio.run(SvdDl().download_svd(script_args.svd_resources))
