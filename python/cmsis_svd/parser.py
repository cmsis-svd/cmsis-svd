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
from xml.etree import ElementTree as ET

from cmsis_svd.model import SVDDevice
from cmsis_svd.model import SVDPeripheral
from cmsis_svd.model import SVDInterrupt
from cmsis_svd.model import SVDAddressBlock
from cmsis_svd.model import SVDRegister
from cmsis_svd.model import SVDField
from cmsis_svd.model import SVDEnumeratedValue
import pkg_resources


def _get_text(node, tag, default=None):
    """Get the text for the provided tag from the provided node"""
    try:
        return node.find(tag).text
    except AttributeError:
        return default


def _get_int(node, tag, default=None):
    text_value = _get_text(node, tag, default)
    if text_value != default:
        if text_value.lower().startswith('0x'):
            return int(text_value[2:], 16)  # hexadecimal
        elif text_value.startswith('#'):
            # TODO(posborne): Deal with strange #1xx case better
            #
            # Freescale will sometimes provide values that look like this:
            #   #1xx
            # In this case, there are a number of values which all mean the
            # same thing as the field is a "don't care".  For now, we just
            # replace those bits with zeros.
            text_value = text_value.replace('x', '0')
            return int(text_value[1:], 2)  # binary
        else:
            return int(text_value)  # decimal
    return default


class SVDParser(object):
    """THe SVDParser is responsible for mapping the SVD XML to Python Objects"""

    @classmethod
    def for_xml_file(cls, path):
        return cls(ET.parse(path))

    @classmethod
    def for_packaged_svd(cls, vendor, filename):
        resource = "data/{vendor}/{filename}".format(
            vendor=vendor,
            filename=filename
        )
        return cls.for_xml_file(pkg_resources.resource_filename("cmsis_svd", resource))

    def __init__(self, tree):
        self._tree = tree
        self._root = self._tree.getroot()

    def _parse_enumerated_value(self, enumerated_value_node):
        return SVDEnumeratedValue(
            name=_get_text(enumerated_value_node, 'name'),
            description=_get_text(enumerated_value_node, 'description'),
            value=_get_int(enumerated_value_node, 'value')
        )

    def _parse_field(self, field_node):
        enumerated_values = []
        for enumerated_value_node in field_node.findall("./enumeratedValues/enumeratedValue"):
            enumerated_values.append(self._parse_enumerated_value(enumerated_value_node))

        return SVDField(
            name=_get_text(field_node, 'name'),
            description=_get_text(field_node, 'description'),
            bit_offset=_get_int(field_node, 'bitOffset'),
            bit_width=_get_int(field_node, 'bitWidth'),
            access=_get_text(field_node, 'access'),
            enumerated_values=enumerated_values or None,
        )

    def _parse_register(self, register_node):
        fields = []
        for field_node in register_node.findall('.//field'):
            fields.append(self._parse_field(field_node))
        return SVDRegister(
            name=_get_text(register_node, 'name'),
            description=_get_text(register_node, 'description'),
            address_offset=_get_int(register_node, 'addressOffset'),
            size=_get_int(register_node, 'size'),
            access=_get_text(register_node, 'access'),
            reset_value=_get_int(register_node, 'resetValue'),
            reset_mask=_get_int(register_node, 'resetMask'),
            fields=fields,
        )

    def _parse_address_block(self, address_block_node):
        return SVDAddressBlock(
            _get_int(address_block_node, 'offset'),
            _get_int(address_block_node, 'size'),
            _get_text(address_block_node, 'usage')
        )

    def _parse_interrupt(self, interrupt_node):
        return SVDInterrupt(
            name=_get_text(interrupt_node, 'name'),
            value=_get_int(interrupt_node, 'value')
        )

    def _parse_peripheral(self, peripheral_node):
        registers = []
        for register_node in peripheral_node.findall('./registers/register'):
            registers.append(self._parse_register(register_node))

        interrupts = []
        for interrupt_node in peripheral_node.findall('./interrupt'):
            interrupts.append(self._parse_interrupt(interrupt_node))

        address_block_nodes = peripheral_node.findall('./addressBlock')
        if address_block_nodes:
            address_block = self._parse_address_block(address_block_nodes[0])
        else:
            address_block = None

        return SVDPeripheral(
            name=_get_text(peripheral_node, 'name'),
            description=_get_text(peripheral_node, 'description'),
            prepend_to_name=_get_text(peripheral_node, 'prependToName'),
            base_address=_get_int(peripheral_node, 'baseAddress'),
            address_block=address_block,
            interrupts=interrupts,
            registers=registers,
        )

    def _parse_device(self, device_node):
        peripherals = []
        for peripheral_node in device_node.findall('.//peripheral'):
            peripherals.append(self._parse_peripheral(peripheral_node))
        return SVDDevice(
            vendor=_get_text(device_node, 'vendor'),
            vendor_id=_get_text(device_node, 'vendorID'),
            name=_get_text(device_node, 'name'),
            version=_get_text(device_node, 'version'),
            description=_get_text(device_node, 'description'),
            cpu=None,  # TODO
            address_unit_bits=_get_int(device_node, 'addressUnitBits'),
            width=_get_int(device_node, 'width'),
            peripherals=peripherals,
        )

    def get_device(self):
        """Get the device described by this SVD"""
        return self._parse_device(self._root)
