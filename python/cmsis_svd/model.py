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
import json
import six


def _check_type(value, expected_type):
    """Perform type checking on the provided value

    This is a helper that will raise ``TypeError`` if the provided value is
    not an instance of the provided type.  This method should be used sparingly
    but can be good for preventing problems earlier when you want to restrict
    duck typing to make the types of fields more obvious.

    If the value passed the type check it will be returned from the call.
    """
    if not isinstance(value, expected_type):
        raise TypeError("Value {value!r} has unexpected type {actual_type!r}, expected {expected_type!r}".format(
            value=value,
            expected_type=expected_type,
            actual_type=type(value),
        ))
    return value

    def __repr__(self):
        return repr(self.__dict__)


class SVDJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, SVDElement):
            return obj.__dict__
        else:
            return json.JSONEncoder.default(self, obj)


class SVDElement(object):
    """Base class for all SVD Elements"""

    def to_dict(self):
        # This is a little convoluted but it works and ensures a
        # json-compatible dictionary representation (at the cost of
        # some computational overhead)
        encoder = SVDJSONEncoder()
        return json.loads(encoder.encode(self))


class SVDEnumeratedValue(SVDElement):

    def __init__(self, name, description, value):
        SVDElement.__init__(self)
        self.name = name
        self.description = description
        self.value = value


class SVDField(SVDElement):

    def __init__(self, name, description, bit_offset, bit_width, access, enumerated_values):
        SVDElement.__init__(self)
        self.name = name
        self.description = description
        self.bit_offset = bit_offset
        self.bit_width = bit_width
        self.access = access
        self.enumerated_values = enumerated_values

    @property
    def is_enumerated_type(self):
        """Return True if the field is an enumerated type"""
        return self.enumerated_values is not None

    @property
    def is_reserved(self):
        return self.name.lower() == "reserved"


class SVDRegister(SVDElement):

    def __init__(self, name, description, address_offset, size, access, reset_value, reset_mask, fields):
        SVDElement.__init__(self)
        self.name = name
        self.description = description
        self.address_offset = address_offset
        self.size = size
        self.access = access
        self.reset_value = reset_value
        self.reset_mask = reset_mask
        self.fields = fields


class SVDAddressBlock(SVDElement):

    def __init__(self, offset, size, usage):
        SVDElement.__init__(self)
        self.offset = offset
        self.size = size
        self.usage = usage


class SVDInterrupt(SVDElement):

    def __init__(self, name, value):
        SVDElement.__init__(self)
        self.name = name
        self.value = _check_type(value, six.integer_types)


class SVDPeripheral(SVDElement):

    def __init__(self, name, description, prepend_to_name, base_address, address_block, interrupts, registers):
        SVDElement.__init__(self)
        self.name = name
        self.description = description
        self.prepend_to_name = prepend_to_name
        self.base_address = base_address
        self.address_block = address_block
        self.interrupts = interrupts
        self.registers = registers


class SVDDevice(SVDElement):

    def __init__(self, vendor, vendor_id, name, version, description, cpu, address_unit_bits, width, peripherals):
        SVDElement.__init__(self)
        self.vendor = vendor
        self.vendor_id = vendor_id
        self.name = name
        self.version = version
        self.description = description
        self.cpu = cpu
        self.address_unit_bits = _check_type(address_unit_bits, six.integer_types)
        self.width = _check_type(width, six.integer_types)
        self.peripherals = peripherals
