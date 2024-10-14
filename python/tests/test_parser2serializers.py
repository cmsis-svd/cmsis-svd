"""

Copyright 2015-2024 cmsis-svd Authors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

from typing import Callable
import os

from cmsis_svd import SVDParser

THIS_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(THIS_DIR, "..", "..", "cmsis-svd-data", "data")


def make_svd_parser2serializers_test(svd_file: str) -> Callable[[], None]:
    def verify_svd_validity() -> None:
        parser = SVDParser.for_xml_file(svd_file)

        device = parser.get_device()
        assert device is not None

        xml_str = device.to_xml()
        assert xml_str is not None

        json_dict = device.to_dict()
        assert json_dict is not None

    mcu = (os.path.basename(svd_file).replace('.svd', '').replace('_svd', '')
           .replace('.', '-').lower())
    vendor = os.path.split(os.path.dirname(svd_path))[-1].lower()
    verify_svd_validity.__name__ = f'test_{vendor}_{mcu}'
    return verify_svd_validity


#
# Generate a test function for each SVD file that exists
#
for dirpath, _dirnames, filenames in os.walk(DATA_DIR):
    for filename in (f for f in filenames if f.endswith('.svd')):
        svd_path = os.path.join(dirpath, filename)
        test = make_svd_parser2serializers_test(svd_path)
        globals()[test.__name__] = test
