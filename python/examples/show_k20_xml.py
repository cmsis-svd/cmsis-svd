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

from cmsis_svd import SVDParser
import os

SVD_ROOT = os.environ.get(
    "SVD_ROOT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "cmsis-svd-data", "data"),
)

parser = SVDParser.for_packaged_svd(SVD_ROOT, 'Freescale', 'MK20D7.svd')
MK20D7_device = parser.get_device()
print(MK20D7_device.to_xml())
