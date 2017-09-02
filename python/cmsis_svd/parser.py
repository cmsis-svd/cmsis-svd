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

from cmsis_svd.model import *
import pkg_resources
import re
from contextlib import contextmanager

def camelize(s):
    first, *rest = s.split('_')
    return ''.join([first, *(e.title() for e in rest)])

def _get_text(node, tag, de=None):
    """Get the text for the provided tag from the provided node"""
    elem = node.find(tag) 
    if elem is None and de is not None:
        elem = de.find(tag)
    if elem is None:
        return None
    return re.sub('\s+', ' ', elem.text).strip()

def _get_int(node, tag, de=None):
    text_value = _get_text(node, tag, de)
    if text_value is None:
        return None
    text_value = text_value.strip().lower()
    if text_value.startswith('0x'):
        return int(text_value[2:], 16)  # hexadecimal
    elif text_value.startswith('#'):
        # TODO(posborne): Deal with strange #1xx case better
        #
        # Freescale will sometimes provide values that look like this:
        #   #1xx
        # In this case, there are a number of values which all mean the
        # same thing as the field is a "don't care".  For now, we just
        # replace those bits with zeros.
        text_value = text_value.replace('x', '0')[1:]
        is_bin = all(x in '01' for x in text_value)
        return int(text_value, 2) if is_bin else int(text_value)  # binary
    elif text_value.lower() == 'true':
        return 1
    elif text_value.lower() == 'false':
        return 0
    else:
        return int(text_value) # decimal

def _get_flag(node, tag, de=None):
    val = _get_int(node, tag, de)
    return None if val is None else bool(val)

@contextmanager
def _node_access(node, parent):
    dv = parent._elements.get(_get_text(node, 'derivedFrom')) if parent else None
    de = None if dv is None else dv.node
    d = {}
    def register(accessor):
        def call(tag, default=None):
            val = accessor(node, camelize(tag), de)
            if val is None:
                val = default
            v = d[tag] = val
            return v
        return call
    yield register(_get_text), register(_get_int), register(_get_flag), d


class Parser(object):
    """The Parser is responsible for mapping the SVD XML to Python Objects"""

    @classmethod
    def for_xml_file(cls, path, remove_reserved=False):
        return cls(ET.parse(path), remove_reserved)

    @classmethod
    def for_packaged_svd(cls, vendor, filename, remove_reserved=False):
        resource = "data/{vendor}/{filename}".format(
            vendor=vendor,
            filename=filename
        )

        filename = pkg_resources.resource_filename("cmsis_svd", resource)
        return cls.for_xml_file(filename, remove_reserved)
    
    @classmethod
    def for_mcu(cls, mcu):
        mcu = mcu.lower()
        vendors = pkg_resources.resource_listdir("cmsis_svd", "data")
        for vendor in vendors:
            fnames = pkg_resources.resource_listdir("cmsis_svd", "data/%s" % vendor)
            for fname in fnames:
                filename = fname.lower()
                if not filename.endswith(".svd"):
                    continue
                filename = filename[:-4]
                if mcu.startswith(filename):
                    return cls.for_packaged_svd(vendor, fname)
            for fname in fnames:
                filename = fname.lower()
                if not filename.endswith(".svd"):
                    continue
                filename = "^%s.*" % filename[:-4].replace('x', '.')
                if re.match(filename, mcu):
                    return cls.for_packaged_svd(vendor, fname)
        return None

    def __init__(self, tree, remove_reserved=False):
        self.remove_reserved = remove_reserved
        self._tree = tree
        self._root = self._tree.getroot()

    def _parse_enumerated_value(self, node, parent, path):
        with _node_access(node, parent) as (text, num, flag, vals):
            text('name', path)
            text('description')
            text('value')
            flag('is_default')
            return EnumeratedValue(node=node, parent=parent, **vals)

    def _parse_field(self, node, parent, path):
        with _node_access(node, parent) as (text, num, flag, vals):
            name = text('name', path)
            if self.remove_reserved and 'reserved' in name:
                return

            bit_range = text('bit_range')
            bit_offset = num('bit_offset')
            bit_width = num('bit_width')
            msb = num('msb')
            lsb = num('lsb')
            if bit_range is not None:
                m = re.search('\[([0-9]+):([0-9]+)\]', bit_range)
                vals['bit_offset'] = int(m.group(2))
                vals['bit_width'] = 1 + (int(m.group(1)) - int(m.group(2)))
            elif msb is not None:
                vals['bit_offset'] = lsb
                vals['bit_width'] = 1 + (msb - lsb)

            text('description')
            text('access'),
            text('modified_write_values'),
            text('read_action')
            field = Field(node=node, parent=parent, **vals)

            for i, vnode in enumerate(node.findall("./enumeratedValues/enumeratedValue")):
                self._parse_enumerated_value(vnode, field, '{}.value{}'.format(name, i))

            return field

    def _parse_registers(self, node, parent, path):
        with _node_access(node, parent) as (text, num, flag, vals):
            dim = num('dim')
            name = text('name', path)
            text('description')
            num('address_offset')
            num('size', parent.size)
            text('access', parent.access)
            text('protection', parent.protection)
            num('reset_value', parent.reset_value)
            num('reset_mask', parent.reset_mask)
            num('dim_increment')
            dim_index_text = text('dim_index')
            text('display_name')
            text('alternate_group')
            text('modified_write_values')
            text('read_action')

            if dim is None:
                element = Register(node=node, parent=parent, **vals)
            else:
                # the node represents a register array
                if dim_index_text is None:
                    dim_indices = range(0, dim)  # some files omit dimIndex
                elif ',' in dim_index_text:
                    dim_indices = dim_index_text.split(',')
                elif '-' in dim_index_text:  # some files use <dimIndex>0-3</dimIndex> as an inclusive inclusive range
                    l, r = re.search(r'([0-9]+)-([0-9]+)', dim_index_text).groups()
                    dim_indices = range(int(l), int(r)+1)
                else:
                    raise ValueError('Cannot parse dim_index_text "{}"'.format(dim_index_text))

                # return RegisterArray (caller will differentiate on type)
                element = RegisterArray(node=node, parent=parent, dim_indices=list(dim_indices), **vals)

            for i, field_node in enumerate(node.findall('.//field')):
                node = self._parse_field(field_node, element, '{}.field{}'.format(name, i))

            return element

    def _parse_address_block(self, node, parent, path):
        with _node_access(node, parent) as (text, num, flag, vals):
            text('name', path)
            num('offset')
            num('size', parent.size)
            text('usage')
            return AddressBlock(node=node, parent=parent, **vals)

    def _parse_interrupt(self, node, parent, path):
        with _node_access(node, parent) as (text, num, flag, vals):
            text('name', path)
            num('value')
            return Interrupt(node=node, parent=parent, **vals)

    def _parse_peripheral(self, node, parent, path):
        with _node_access(node, parent) as (text, num, flag, vals):
            # <name>identifierType</name>
            # <version>xs:string</version>
            # <description>xs:string</description>
            name = text('name', path)
            text('version')
            text('description')

            # <groupName>identifierType</groupName>
            # <prependToName>identifierType</prependToName>
            # <appendToName>identifierType</appendToName>
            # <disableCondition>xs:string</disableCondition>
            # <baseAddress>scaledNonNegativeInteger</baseAddress>
            text('group_name')
            text('prepend_to_name')
            text('append_to_name')
            text('disable_condition')
            num('base_address')

            # <!-- registerPropertiesGroup -->
            # <size>scaledNonNegativeInteger</size>
            # <access>accessType</access>
            # <resetValue>scaledNonNegativeInteger</resetValue>
            # <resetMask>scaledNonNegativeInteger</resetMask>
            num('size', parent.size)
            text('access')
            num('reset_value')
            num('reset_mask')

            # (not mentioned in docs -- applies to all registers)
            text('protection')

            peripheral = Peripheral(node=node, parent=parent, **vals)

            # parse registers
            # <registers>
            #     ...
            # </registers>
            for i, rnode in enumerate(node.findall('./registers/register')):
                reg = self._parse_registers(rnode, peripheral, '{}.reg{}'.format(name, i))

            # parse all interrupts for the peripheral
            # <interrupt>
            #     <name>identifierType</name>
            #     <value>scaledNonNegativeInteger</value>
            # </interrupt>
            for i, inode in enumerate(node.findall('./interrupt')):
                self._parse_interrupt(inode, peripheral, '{}.int{}'.format(name, i))

            # parse address block if any
            # <addressBlock>
            #     <offset>scaledNonNegativeInteger</offset>
            #     <size>scaledNonNegativeInteger</size>
            #     <usage>usageType</usage>
            #     <protection>protectionStringType</protection>
            # </addressBlock>
            bnodes = node.findall('./addressBlock')
            if bnodes:
                self._parse_address_block(bnodes[0], peripheral, '{}.address_block'.format(name))

            return peripheral

    def _parse_cpu(self, node, parent, path):
        with _node_access(node, parent) as (text, num, flag, vals):
            text('name', path)
            text('revision')
            text('endian')
            flag('mpu_present')
            flag('fpu_present')
            num('fpu_dp')
            flag('icache_present')
            flag('dcache_present')
            flag('itcm_present')
            flag('dtcm_present')
            flag('vtor_present')
            num('nvic_prio_bits')
            num('vendor_systick_config')
            num('device_num_interrupts')
            num('sau_num_regions')
            text('sau_regions_config')
            cpu = Cpu(node=node, parent=parent, **vals)

    def _parse_device(self, node):
        with _node_access(node, None) as (text, num, flag, vals):
            text('vendor')
            text('vendor_id')
            name = text('name', 'device')
            text('version')
            text('description')
            num('address_unit_bits')
            num('width')
            num('size', 32)
            text('access')
            text('protection')
            num('reset_value')
            num('reset_mask')
            device = Device(node=node, parent=None, **vals)

        cpu_node = node.find('./cpu')
        if cpu_node:
            self._parse_cpu(cpu_node, device, '{}.cpu'.format(name))

        for i, peripheral_node in enumerate(node.findall('.//peripheral')):
            self._parse_peripheral(peripheral_node, device, '{}.per{}'.format(name, i))

        return device

    def parse(self):
        """Get the device described by this SVD"""
        return self._parse_device(self._root)


def duplicate_array_of_registers(svdreg):  # expects a SVDRegister which is an array of registers
    assert (svdreg.dim == len(svdreg.dim_index))

