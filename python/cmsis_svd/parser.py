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
import copy
from lxml import etree

from cmsis_svd.model import SVDDevice
from cmsis_svd.model import SVDPeripheral
from cmsis_svd.model import SVDInterrupt
from cmsis_svd.model import SVDAddressBlock
from cmsis_svd.model import SVDRegister, SVDRegisterArray
from cmsis_svd.model import SVDRegisterCluster, SVDRegisterClusterArray
from cmsis_svd.model import SVDField
from cmsis_svd.model import SVDEnumeratedValue
from cmsis_svd.model import SVDCpu
import re

class ElementABC(object):
    def __init__(self, tag):
        self.tag = tag

    def is_optional(self):
        raise NotImplementedError("is_optional not implemented")

    def parse(self, el):
        raise NotImplementedError("parse not implemented")

class OptionalElement(ElementABC):

    def __init__(self, inner, default=None):
        ElementABC.__init__(self, inner.tag)
        self.inner = inner
        self.default = default

    def is_optional(self):
        return True

    def parse(self, el):
        return self.inner.parse(el)

class TextElement(ElementABC):

    def is_optional(self):
        return False

    def parse(self, el):
        return el.text

class IntElement(ElementABC):

    def is_optional(self):
        return False

    def parse(self, el):
        text_value = el.text.strip().lower()
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
        elif text_value.startswith('true'):
            return 1
        elif text_value.startswith('false'):
            return 0
        else:
            return int(text_value)  # decimal

def _parse_sequences(node, *tags):
    tag_iter = iter(tags)
    res = []

    for el in node:
        while True:
            try:
                tag = next(tag_iter)
                if tag.tag == el.tag:
                    res.append(tag.parse(el))
                    break
                elif tag.is_optional():
                    res.append(tag.default)
                    continue
                else:
                    raise KeyError("Expected tag not found in correct place. Expected: {}, Element was: {}\nNode:\n{}".format(tag.tag, el, etree.tostring(node)))
            except StopIteration:
                print("Res: {}".format(res))
                yield tuple(res)
                tag_iter = iter(tags)
                res = []

    if res:
        for remtag in tag_iter:
            if remtag.is_optional():
                res.append(remtag.default)
            else:
                raise KeyError("Remaining non-optional element: {}".format(remtag))
        yield tuple(res)



def _get_text(node, tag, default=None):
    """Get the text for the provided tag from the provided node"""
    try:
        return node.find(tag).text
    except AttributeError:
        return default


def _get_int(node, tag, default=None):
    text_value = _get_text(node, tag, default)
    try:
        if text_value != default:
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
            elif text_value.startswith('true'):
                return 1
            elif text_value.startswith('false'):
                return 0
            else:
                return int(text_value)  # decimal
    except ValueError:
        return default
    return default


class SVDXmlPreprocessing:
    """This class is responsible for modifying the SVD device tree for
    propagating inherited tag through the tree."""

    _REGISTER_PROPERTIES_GROUP = {
        "size", "access", "protection", "resetValue", "resetMask"}

    def __init__(self, document_root):
        self._root = document_root

    @staticmethod
    def _propagate_register_properties_keys(targets, properties):
        for node in targets:
            for prop in properties:
                if node.find(prop) is None and properties[prop] is not None:
                    node.append(copy.deepcopy(properties[prop]))

    def _propagate_register_properties_group(self):
        rpg = {k: self._root.find(k) for k in self._REGISTER_PROPERTIES_GROUP}

        self._propagate_register_properties_keys(
            self._root.findall('.//peripheral'), rpg)

        self._propagate_register_properties_keys(
            self._root.findall('.//sauRegionsConfig[@protectionWhenDisabled]'),
            {'protection': rpg['protection']})

        for periph in self._root.findall(".//peripheral"):
            rpg_copy = copy.deepcopy(rpg)
            for k in self._REGISTER_PROPERTIES_GROUP:
                node_k = periph.find(k)
                if node_k is not None:
                    rpg_copy[k] = node_k

            self._propagate_register_properties_keys(
                periph.findall('.//register'), rpg_copy)
            self._propagate_register_properties_keys(
                periph.findall('.//cluster'), rpg_copy)
            self._propagate_register_properties_keys(
                periph.findall('.//addressBlock'),
                {'protection': rpg_copy['protection']})

        for reg in self._root.findall('.//register'):
            rpg_copy = copy.deepcopy(rpg)
            for k in self._REGISTER_PROPERTIES_GROUP:
                node_k = reg.find(k)
                if node_k is not None:
                    rpg_copy[k] = node_k

            self._propagate_register_properties_keys(
                reg.findall('.//field'), {'access': rpg_copy['access']})

    @staticmethod
    def _derive_tag(src, dst, override=True):
        dst_tags = [t.tag for t in dst.findall('./')] if override else list()
        for src_tag in filter(lambda t: t.tag not in dst_tags, src.findall('./')):
            dst.append(copy.deepcopy(src_tag))

    def _derived_from_enumerated_values(self):
        for dst in self._root.findall('.//enumeratedValues[@derivedFrom]'):
            src = self._root.find('.//enumeratedValues[name="{}"]'
                                  .format(dst.attrib['derivedFrom']))
            if src is not None:
                 for src_tag in src.findall('./enumeratedValue'):
                     self._derive_tag(src_tag, dst)

    def _derived_from_field(self):
        for dst in self._root.findall('.//field[@derivedFrom]'):
            derived_path = dst.attrib['derivedFrom'].split('.')

            if len(derived_path) == 1:
                src = dst.find('../field[name="{}"]'.format(derived_path[0]))
            elif len(derived_path) == 3:
                src = self._root.find('.//peripheral[name="{}"]'
                                      '//register[name="{}"]//field[name="{}"]'
                                      .format(derived_path[0], derived_path[1],
                                              derived_path[3]))
            else:
                src = None

            if (src is not None and dst.find('./name') is not None
                    and dst.find('./description') is not None):
                self._derive_tag(src, dst)

    def _derived_from_register(self):
        for dst in self._root.findall('.//register[@derivedFrom]'):
            derived_path = dst.attrib['derivedFrom'].split('.')

            if len(derived_path) == 1:
                src = dst.find('../register[name="{}"]'.format(derived_path[0]))
            elif len(derived_path) == 2:
                src = self._root.find('.//peripheral[name="{}"]'
                                      '//register[name="{}"]'.format(
                                      derived_path[0], derived_path[1]))
            else:
                src = None

            if (src is not None and dst.find('./name') is not None
                    and dst.find('./description') is not None
                    and dst.find('./addressOffset') is not None):
                self._derive_tag(src, dst)

    def _derived_from_cluster(self):
        for dst in self._root.findall('.//cluster[@derivedFrom]'):
            derived_path = dst.attrib['derivedFrom'].split('.')

            if len(derived_path) == 1:
                src = dst.find('../cluster[name="{}"]'.format(derived_path[0]))
            elif len(derived_path) == 2:
                src = self._root.find('.//peripheral[name="{}"]'
                                      '//cluster[name="{}"]'.format(
                                      derived_path[0], derived_path[1]))
            else:
                src = None

            if (src is not None and dst.find('./name') is not None
                    and dst.find('./description') is not None
                    and dst.find('./addressOffset') is not None):
                self._derive_tag(src, dst)

    def _derived_from_peripherals(self):
        for dst in self._root.findall('.//peripheral[@derivedFrom]'):
            src = self._root.find('.//peripheral[name="{}"]'.format(
                                  dst.attrib['derivedFrom']))
            if src is not None:
                self._derive_tag(src, dst)

    def preprocess_xml(self):
        self._derived_from_enumerated_values()
        self._derived_from_field()
        self._derived_from_register()
        self._derived_from_cluster()
        self._derived_from_peripherals()
        self._propagate_register_properties_group()


class SVDParser(object):
    """The SVDParser is responsible for mapping the SVD XML to Python Objects"""

    @classmethod
    def for_xml_file(cls, path):
        """Create a new parser for the provided SVD XML file

        These files often have either the .xml or .svd extension and may
        be found as part of CMSIS packs or as part of the data provided
        by the cmsis-svd project.
        """
        return cls(etree.parse(path))

    @classmethod
    def for_packaged_svd(cls, package_root, vendor, filename):
        """Find SVD for a given vendor/mcu within packaged data

        This convenience method requires a "package_root" which is
        expected to be the filesystem location containing the SVD
        data from the cmsis-svd project.  This directory contains
        a number of subdirectories with vendor names and SVD files
        for the vendor beneath that.

        In prior releases, this information was directly distributed
        as part of the python package but that is no longer the case
        as of version 0.5.
        """
        path = os.path.join(package_root, vendor, filename)
        if os.path.exists(path):
            return cls.for_xml_file(path)

        # some vendors like SiliconLabs currently have more deeply nested
        # directory structures, attempt to find recursively.
        for root, _dirs, filenames in os.walk(os.path.join(package_root, vendor)):
            for fname in filenames:
                if fname == filename:
                    return cls.for_xml_file(os.path.join(root, fname))

        return None

    @classmethod
    def for_mcu(cls, package_root, mcu):
        """Attempt to find SVD for a given mcu by name within package root

        This convenience method requires a "package_root" which is
        expected to be the filesystem location containing the SVD
        data from the cmsis-svd project.  This directory contains
        a number of subdirectories with vendor names and SVD files
        for the vendor beneath that.

        In prior releases, this information was directly distributed
        as part of the python package but that is no longer the case
        as of version 0.5.

        This method is similar to `for_packaged_svd` but only requires
        the "MCU" name (svd files are assumed to be named by MCU).
        For instance, within the packaged data there might be an SVD at
        the following path:

            <package_root>/SiliconLabs/Series0/EFM32G/EFM32G210F128.svd

        Note that some MCUs include an "x" in the svd name to capture
        a family of MCUs.  This isn't applied consistently, so you will
        need to provide a pattern that matches one of the SVD files.            
        """
        path = os.path.abspath(package_root)
        expected_fname_lower = f"{mcu}.svd".lower()
        for root, _dirs, filenames in os.walk(path):
            for fname in filenames:
                fname_final_lower = os.path.split(fname)[-1].lower()
                if expected_fname_lower == fname_final_lower:
                    return cls.for_xml_file(os.path.join(root, fname))
                   
        return None

    def __init__(self, tree, remove_reserved=False):
        self.remove_reserved = remove_reserved
        self._tree = tree
        self._root = self._tree.getroot()

    def _parse_enumerated_value(self, enumerated_value_node):
        return SVDEnumeratedValue(
            name=_get_text(enumerated_value_node, 'name'),
            description=_get_text(enumerated_value_node, 'description'),
            value=_get_int(enumerated_value_node, 'value'),
            is_default=_get_int(enumerated_value_node, 'isDefault')
        )

    def _parse_field(self, field_node, register_node):
        enumerated_values = []
        for enumerated_value_node in field_node.findall("./enumeratedValues/enumeratedValue"):
            enumerated_values.append(self._parse_enumerated_value(enumerated_value_node))

        modified_write_values=_get_text(field_node, 'modifiedWriteValues')
        read_action=_get_text(field_node, 'readAction')
        bit_range = _get_text(field_node, 'bitRange')
        bit_offset = _get_int(field_node, 'bitOffset')
        bit_width = _get_int(field_node, 'bitWidth')
        msb = _get_int(field_node, 'msb')
        lsb = _get_int(field_node, 'lsb')
        if bit_range is not None:
            m = re.search('\[([0-9]+):([0-9]+)\]', bit_range)
            bit_offset = int(m.group(2))
            bit_width = 1 + (int(m.group(1)) - int(m.group(2)))
        elif msb is not None:
            bit_offset = lsb
            bit_width = 1 + (msb - lsb)

        return SVDField(
            name=_get_text(field_node, 'name'),
            derived_from=field_node.get('derivedFrom'),
            description=_get_text(field_node, 'description'),
            bit_offset=bit_offset,
            bit_width=bit_width,
            access=_get_text(field_node, 'access'),
            enumerated_values=enumerated_values or None,
            modified_write_values=modified_write_values,
            read_action=read_action,
        )

    def _parse_registers(self, register_node):
        fields = []
        for field_node in register_node.findall('.//field'):
            node = self._parse_field(field_node, register_node)
            if not self.remove_reserved or 'reserved' not in node.name.lower():
                fields.append(node)

        dim = _get_int(register_node, 'dim')
        name = _get_text(register_node, 'name')
        derived_from = register_node.get('derivedFrom')
        description = _get_text(register_node, 'description')
        address_offset = _get_int(register_node, 'addressOffset')
        size = _get_int(register_node, 'size')
        access = _get_text(register_node, 'access')
        protection = _get_text(register_node, 'protection')
        reset_value = _get_int(register_node, 'resetValue')
        reset_mask = _get_int(register_node, 'resetMask')
        dim_increment = _get_int(register_node, 'dimIncrement')
        dim_index_text = _get_text(register_node, 'dimIndex')
        display_name = _get_text(register_node, 'displayName')
        alternate_group = _get_text(register_node, 'alternateGroup')
        modified_write_values = _get_text(register_node, 'modifiedWriteValues')
        read_action = _get_text(register_node, 'readAction')

        if dim is None:
            return SVDRegister(
                name=name,
                fields=fields,
                derived_from=derived_from,
                description=description,
                address_offset=address_offset,
                size=size,
                access=access,
                protection=protection,
                reset_value=reset_value,
                reset_mask=reset_mask,
                display_name=display_name,
                alternate_group=alternate_group,
                modified_write_values=modified_write_values,
                read_action=read_action,
            )
        else:
            # the node represents a register array
            if dim_index_text is None:
                dim_indices = list(range(0, dim))  # some files omit dimIndex
            elif ',' in dim_index_text:
                dim_indices = dim_index_text.split(',')
            elif '-' in dim_index_text:  # some files use <dimIndex>0-3</dimIndex> as an inclusive inclusive range
                start, stop = dim_index_text.split('-')

                if start.isalpha() and stop.isalpha():
                    start_val = ord(start)
                    stop_val = ord(stop)

                    dim_indices = [
                        chr(val)
                        for val in range(start_val, stop_val + 1)
                    ]

                elif start.isdigit() and stop.isdigit():
                    start_val = int(start)
                    stop_val = int(stop)

                    dim_indices = [
                        str(val)
                        for val in range(start_val, stop_val + 1)
                    ]

                else:
                    raise NotImplementedError(
                        f'DimIndex={dim_index_text} is not supported.'
                    )
            else:
                raise ValueError("Unexpected dim_index_text: %r" % dim_index_text)

            # yield `SVDRegisterArray` (caller will differentiate on type)
            return SVDRegisterArray(
                name=name,
                fields=fields,
                derived_from=derived_from,
                description=description,
                address_offset=address_offset,
                size=size,
                access=access,
                protection=protection,
                reset_value=reset_value,
                reset_mask=reset_mask,
                display_name=display_name,
                alternate_group=alternate_group,
                modified_write_values=modified_write_values,
                read_action=read_action,
                dim=dim,
                dim_indices=dim_indices,
                dim_increment=dim_increment,
            )

    def _parse_cluster(self, cluster_node):
        dim = _get_int(cluster_node, 'dim')
        name = _get_text(cluster_node, 'name')
        derived_from = cluster_node.get('derivedFrom')
        description = _get_text(cluster_node, 'description')
        address_offset = _get_int(cluster_node, 'addressOffset')
        size = _get_int(cluster_node, 'size')
        access = _get_text(cluster_node, 'access')
        protection = _get_text(cluster_node, 'protection')
        reset_value = _get_int(cluster_node, 'resetValue')
        reset_mask = _get_int(cluster_node, 'resetMask')
        dim_increment = _get_int(cluster_node, 'dimIncrement')
        dim_index_text = _get_text(cluster_node, 'dimIndex')
        alternate_cluster = _get_text(cluster_node, 'alternateCluster')
        header_struct_name = _get_text(cluster_node, 'headerStructName')
        cluster = []
        for sub_cluster_node in cluster_node.findall("./cluster"):
            cluster.append(self._parse_cluster(sub_cluster_node))
        register = []
        for reg_node in cluster_node.findall("./register"):
            register.append(self._parse_registers(reg_node))

        if dim is None:
            return SVDRegisterCluster(
                name=name,
                derived_from=derived_from,
                description=description,
                address_offset=address_offset,
                size=size,
                access=access,
                protection=protection,
                reset_value=reset_value,
                reset_mask=reset_mask,
                alternate_cluster=alternate_cluster,
                header_struct_name=header_struct_name,
                register=register,
                cluster=cluster,
            )
        else:
            # the node represents a register array
            if dim_index_text is None:
                dim_indices = list(range(0, dim))  # some files omit dimIndex
            elif ',' in dim_index_text:
                dim_indices = dim_index_text.split(',')
            elif '-' in dim_index_text:  # some files use <dimIndex>0-3</dimIndex> as an inclusive inclusive range
                m = re.search(r'([0-9]+)-([0-9]+)', dim_index_text)
                dim_indices = list(range(int(m.group(1)), int(m.group(2)) + 1))
            else:
                raise ValueError("Unexpected dim_index_text: %r" % dim_index_text)

            # yield `SVDRegisterArray` (caller will differentiate on type)
            return SVDRegisterClusterArray(
                name=name,
                derived_from=derived_from,
                description=description,
                address_offset=address_offset,
                size=size,
                access=access,
                protection=protection,
                reset_value=reset_value,
                reset_mask=reset_mask,
                alternate_cluster=alternate_cluster,
                header_struct_name=header_struct_name,
                register=register,
                cluster=cluster,
                dim=dim,
                dim_increment=dim_increment,
                dim_indices=dim_indices,
            )

    def _parse_address_block(self, address_block_node):
        return SVDAddressBlock(
            _get_int(address_block_node, 'offset'),
            _get_int(address_block_node, 'size'),
            _get_text(address_block_node, 'usage')
        )

    def _parse_interrupts(self, interrupt_node):
        tags = [
            TextElement('name'),
            OptionalElement(TextElement('description')),
            TextElement('value'),
        ]

        for (name, value, description) in _parse_sequences(interrupt_node, *tags):
            yield SVDInterrupt(
                name=_get_text(interrupt_node, 'name'),
                value=_get_int(interrupt_node, 'value'),
                description=_get_text(interrupt_node, 'description'))

    def _parse_peripheral(self, peripheral_node):
        # parse registers
        registers = None if peripheral_node.find('registers') is None else []
        register_arrays = None if peripheral_node.find('registers') is None else []
        for register_node in peripheral_node.findall('./registers/register'):
            reg = self._parse_registers(register_node)
            if isinstance(reg, SVDRegisterArray):
                register_arrays.append(reg)
            else:
                registers.append(reg)

        clusters = []
        for cluster_node in peripheral_node.findall('./registers/cluster'):
            reg = self._parse_cluster(cluster_node)
            clusters.append(reg)

        # parse all interrupts for the peripheral
        interrupts = []
        for interrupt_node in peripheral_node.findall('./interrupt'):
            for interrupt in self._parse_interrupts(interrupt_node):
                interrupts.append(interrupt)
        interrupts = interrupts if interrupts else None

        # parse all address blocks for the peripheral
        address_blocks = []
        for address_block_node in peripheral_node.findall('./addressBlock'):
            address_blocks.append(self._parse_address_block(address_block_node))
        address_blocks = address_blocks if address_blocks else None

        return SVDPeripheral(
            # <name>identifierType</name>
            # <version>xs:string</version>
            # <description>xs:string</description>
            name=_get_text(peripheral_node, 'name'),
            version=_get_text(peripheral_node, 'version'),
            derived_from=peripheral_node.get('derivedFrom'),
            description=_get_text(peripheral_node, 'description'),

            # <groupName>identifierType</groupName>
            # <prependToName>identifierType</prependToName>
            # <appendToName>identifierType</appendToName>
            # <disableCondition>xs:string</disableCondition>
            # <baseAddress>scaledNonNegativeInteger</baseAddress>
            group_name=_get_text(peripheral_node, 'groupName'),
            prepend_to_name=_get_text(peripheral_node, 'prependToName'),
            append_to_name=_get_text(peripheral_node, 'appendToName'),
            disable_condition=_get_text(peripheral_node, 'disableCondition'),
            base_address=_get_int(peripheral_node, 'baseAddress'),

            # <!-- registerPropertiesGroup -->
            # <size>scaledNonNegativeInteger</size>
            # <access>accessType</access>
            # <resetValue>scaledNonNegativeInteger</resetValue>
            # <resetMask>scaledNonNegativeInteger</resetMask>
            size=_get_int(peripheral_node, "size"),
            access=_get_text(peripheral_node, 'access'),
            reset_value=_get_int(peripheral_node, "resetValue"),
            reset_mask=_get_int(peripheral_node, "resetMask"),

            # <addressBlock>
            #     <offset>scaledNonNegativeInteger</offset>
            #     <size>scaledNonNegativeInteger</size>
            #     <usage>usageType</usage>
            #     <protection>protectionStringType</protection>
            # </addressBlock>
            address_blocks=address_blocks,

            # <interrupt>
            #     <name>identifierType</name>
            #     <value>scaledNonNegativeInteger</value>
            #     <description>xs:string</description>
            # </interrupt>
            interrupts=interrupts,

            # <registers>
            #     ...
            # </registers>
            register_arrays=register_arrays,
            registers=registers,

            # <cluster>
            #    ...
            # </cluster>
            clusters=clusters,

            # (not mentioned in docs -- applies to all registers)
            protection=_get_text(peripheral_node, 'protection'),
        )

    def _parse_device(self, device_node):
        peripherals = []
        for peripheral_node in device_node.findall('.//peripheral'):
            peripherals.append(self._parse_peripheral(peripheral_node))
        cpu_node = device_node.find('./cpu')
        cpu = SVDCpu(
            name=_get_text(cpu_node, 'name'),
            revision=_get_text(cpu_node, 'revision'),
            endian=_get_text(cpu_node, 'endian'),
            mpu_present=_get_int(cpu_node, 'mpuPresent'),
            fpu_present=_get_int(cpu_node, 'fpuPresent'),
            fpu_dp=_get_int(cpu_node, 'fpuDP'),
            icache_present=_get_int(cpu_node, 'icachePresent'),
            dcache_present=_get_int(cpu_node, 'dcachePresent'),
            itcm_present=_get_int(cpu_node, 'itcmPresent'),
            dtcm_present=_get_int(cpu_node, 'dtcmPresent'),
            vtor_present=_get_int(cpu_node, 'vtorPresent'),
            nvic_prio_bits=_get_int(cpu_node, 'nvicPrioBits'),
            vendor_systick_config=_get_int(cpu_node, 'vendorSystickConfig'),
            device_num_interrupts=_get_int(cpu_node, 'deviceNumInterrupts'),
            sau_num_regions=_get_int(cpu_node, 'sauNumRegions'),
            sau_regions_config=_get_text(cpu_node, 'sauRegionsConfig')
        )

        return SVDDevice(
            vendor=_get_text(device_node, 'vendor'),
            vendor_id=_get_text(device_node, 'vendorID'),
            name=_get_text(device_node, 'name'),
            version=_get_text(device_node, 'version'),
            description=_get_text(device_node, 'description'),
            cpu=cpu,
            address_unit_bits=_get_int(device_node, 'addressUnitBits'),
            width=_get_int(device_node, 'width'),
            peripherals=peripherals,
            size=_get_int(device_node, "size"),
            access=_get_text(device_node, 'access'),
            protection=_get_text(device_node, 'protection'),
            reset_value=_get_int(device_node, "resetValue"),
            reset_mask=_get_int(device_node, "resetMask")
        )

    def get_device(self):
        """Get the device described by this SVD"""
        SVDXmlPreprocessing(self._root).preprocess_xml()
        return self._parse_device(self._root)


def duplicate_array_of_registers(svdreg):  # expects a SVDRegister which is an array of registers
    assert (svdreg.dim == len(svdreg.dim_index))
