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

from typing import Any
from enum import Enum
import json
import six

from ..model import SVDElement


class SVDJSONEncoder(json.JSONEncoder):
    _TO_DICT_SKIP_KEYS = {
        'parent',
        'dim_index_separator',
        'to_dict', 'to_json', 'to_json_file',
        'to_xml_node', 'to_xml', 'to_xml_file',
    }

    def default(self, obj: Any) -> Any:
        if isinstance(obj, SVDElement):
            eldict = {}
            for k, v in six.iteritems(obj.__dict__):
                if k in self._TO_DICT_SKIP_KEYS:
                    continue
                if k.startswith("_"):
                    pubkey = k[1:]
                    eldict[pubkey] = getattr(obj, pubkey)
                else:
                    eldict[k] = v
            return eldict

        if isinstance(obj, Enum):
            return obj.value

        return json.JSONEncoder.default(self, obj)


class SVDJsonSerializer:
    def __init__(self, svd_item: SVDElement):
        self.svd_item = svd_item

    def to_dict(self) -> dict:
        # This is a little convoluted, but it works and ensures a
        # json-compatible dictionary representation (at the cost of
        # some computational overhead)
        return json.loads(SVDJSONEncoder().encode(self.svd_item))

    def to_json(self, sort_keys=True, indent=4, separators=(',', ': ')) -> str:
        return json.dumps(self.to_dict(), sort_keys=sort_keys, indent=indent,
                          separators=separators)

    def to_json_file(self, path: str, sort_keys=True, indent=4,
                     separators=(',', ': ')) -> None:
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, sort_keys=sort_keys, indent=indent,
                      separators=separators)
