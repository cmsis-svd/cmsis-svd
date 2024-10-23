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

from typing import Union, List, Dict, Any, Tuple
from enum import Enum
import os
import copy
import re

import lxml
from lxml import etree
from lxml.etree import ElementTree, Element

from .model import (
    SVDDevice, SVDCpu, SVDPeripheral, SVDInterrupt, SVDAddressBlock,
    SVDRegister, SVDRegisterArray, SVDRegisterCluster, SVDRegisterClusterArray,
    SVDField, SVDEnumeratedValue, SVDWriteConstraint, SVDPeripheralArray,
    SVDAccessType, SVDAddressBlockUsageType, SVDDataTypeType, SVDProtectionType,
    SVDModifiedWriteValuesType, SVDReadActionType, SVDFieldArray, SVDCPUNameType,
    SVDDimArrayIndex, SVDEndianType, SVDSauAccessType, SVDSauRegionsConfig,
    SVDWriteConstraintRange, SVDSauRegionsConfigRegion, SVDEnumeratedValues,
    DimElementGroupType, RegisterPropertiesGroupType, SVDEnumUsageType)


class SVDXmlPreprocessing:
    """This class is responsible for modifying the SVD device tree for
    propagating inherited tag through the tree."""

    _REGISTER_PROPERTIES_GROUP = {
        "size", "access", "protection", "resetValue", "resetMask"}

    def __init__(self, document_root: Element):
        self._root: Element = document_root

    @staticmethod
    def _propagate_register_properties_keys(
        targets: List[Element], properties: Dict[str, str]
    ) -> None:
        for node in targets:
            for prop in properties:
                if node.find(prop) is None and properties[prop] is not None:
                    node.append(copy.deepcopy(properties[prop]))

    def _propagate_register_properties_group(self) -> None:
        rpg = {k: self._root.find(k) for k in self._REGISTER_PROPERTIES_GROUP}

        self._propagate_register_properties_keys(
            self._root.findall('.//peripheral'), rpg)

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
    def _derive_tag(src: Element, dst: Element, override: bool = True) -> None:
        dst_tags = [t.tag for t in dst.findall('./')] if override else []
        for src_tag in filter(lambda t: t.tag not in dst_tags, src.findall('./')):
            dst.append(copy.deepcopy(src_tag))

    def _derived_from_enumerated_values(self) -> None:
        for dst in self._root.findall('.//enumeratedValues[@derivedFrom]'):
            src = self._root.find(f'.//enumeratedValues'
                                  f'[name="{dst.attrib["derivedFrom"]}"]')
            if src is not None:
                for src_tag in src.findall('./enumeratedValue'):
                    self._derive_tag(src_tag, dst)

    def _derived_from_field(self) -> None:
        for dst in self._root.findall('.//field[@derivedFrom]'):
            derived_path = dst.attrib['derivedFrom'].split('.')

            if len(derived_path) == 1:
                src = dst.find(f'../field[name="{derived_path[0]}"]')
            elif len(derived_path) == 3:
                src = self._root.find(f'.//peripheral[name="{derived_path[0]}"]'
                                      f'//register[name="{derived_path[1]}"]'
                                      f'//field[name="{derived_path[3]}"]')
            else:
                src = None

            if (src is not None and dst.find('./name') is not None
                    and dst.find('./description') is not None):
                self._derive_tag(src, dst)

    def _derived_from_register(self) -> None:
        for dst in self._root.findall('.//register[@derivedFrom]'):
            derived_path = dst.attrib['derivedFrom'].split('.')

            if len(derived_path) == 1:
                src = dst.find(f'../register[name="{derived_path[0]}"]')
            elif len(derived_path) == 2:
                src = self._root.find(f'.//peripheral[name="{derived_path[0]}"]'
                                      f'//register[name="{derived_path[1]}"]')
            else:
                src = None

            if (src is not None and dst.find('./name') is not None
                    and dst.find('./description') is not None
                    and dst.find('./addressOffset') is not None):
                self._derive_tag(src, dst)

    def _derived_from_cluster(self) -> None:
        for dst in self._root.findall('.//cluster[@derivedFrom]'):
            derived_path = dst.attrib['derivedFrom'].split('.')

            if len(derived_path) == 1:
                src = dst.find(f'../cluster[name="{derived_path[0]}"]')
            elif len(derived_path) == 2:
                src = self._root.find(f'.//peripheral[name="{derived_path[0]}"]'
                                      f'//cluster[name="{derived_path[1]}"]')
            else:
                src = None

            if (src is not None and dst.find('./name') is not None
                    and dst.find('./description') is not None
                    and dst.find('./addressOffset') is not None):
                self._derive_tag(src, dst)

    def _derived_from_peripherals(self) -> None:
        for dst in self._root.findall('.//peripheral[@derivedFrom]'):
            src = self._root.find(f'.//peripheral'
                                  f'[name="{dst.attrib["derivedFrom"]}"]')
            if src is not None:
                self._derive_tag(src, dst)

    def preprocess_xml(self) -> None:
        self._derived_from_enumerated_values()
        self._derived_from_field()
        self._derived_from_register()
        self._derived_from_cluster()
        self._derived_from_peripherals()
        self._propagate_register_properties_group()


def _get_text(node: Element, tag: str, default: Any = None) -> Union[str, Any]:
    """Get the text for the provided tag from the provided node"""
    try:
        return node.find(tag).text
    except AttributeError:
        return default


def _get_int(node: Element, tag: str, default: Any = None) -> Union[int, Any]:
    text_value = _get_text(node, tag, default)
    try:
        if text_value != default:
            text_value = text_value.strip().lower()

            if text_value.startswith('0x'):
                ret_value = int(text_value[2:], 16)  # hexadecimal
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
                ret_value = int(text_value, 2) if is_bin else int(text_value)  # binary
            elif text_value.startswith('true'):
                ret_value = 1
            elif text_value.startswith('false'):
                ret_value = 0
            else:
                ret_value = int(text_value)  # decimal

            return ret_value
    except ValueError:
        return default
    return default


def _parse_bool(text_value: str) -> Union[bool, None]:
    text_bool = text_value.lower().strip()

    if text_bool == '0' or text_bool == 'false':
        return False
    elif text_bool == '1' or text_bool == 'true':
        return True

    return None


def _get_bool(node: Element, tag: str, default: Any = None) -> Union[bool, Any]:
    if text_value := _get_text(node, tag, default):
        return _parse_bool(text_value)
    return None


def _is_reserved_name(name: str) -> bool:
    normalized_name = name.lower().replace(' ', '')
    if 'reserved' == normalized_name:
        return True
    return False


def scan_schema_versions() -> List[str]:
    versions: List[str] = []
    with os.scandir(os.path.join(os.path.dirname(__file__), 'schemas')) as it:
        for entry in it:
            xsd = re.search(r'^CMSIS-SVD((_[0-9]{1,2}){1,3})\.xsd$', entry.name)
            if xsd is not None and entry.is_file():
                versions.append(xsd.group(1)[1:].replace('_', '.'))
    return versions


SVD_SCHEMA_VERSIONS = scan_schema_versions()


class SVDParserValidationError(Exception):
    pass


class SVDParser:
    """The SVDParser is responsible for mapping the SVD XML to Python Objects"""

    @staticmethod
    def _get_latest_schema_version() -> str:
        if len(SVD_SCHEMA_VERSIONS) == 0:
            raise SVDParserValidationError('SVD schema versions not found.')

        def parse_version(version):
            return list(map(int, version.split('.')))

        versions = list(map(parse_version, SVD_SCHEMA_VERSIONS))
        latest = max(versions)
        return '.'.join(map(str, latest))

    @classmethod
    def validate_xml_tree(
        cls, tree: lxml.etree._ElementTree, schema_version: str = 'latest',
        schema_version_detection: bool = True
    ) -> Tuple[bool, str]:
        root = tree.getroot()

        schema_ver_validation = schema_version
        if schema_version == 'latest':
            schema_ver_validation = cls._get_latest_schema_version()

        if schema_version_detection:
            parsed_schema_version = root.get('schemaVersion')
            if parsed_schema_version is not None:
                if parsed_schema_version in SVD_SCHEMA_VERSIONS:
                    schema_ver_validation = parsed_schema_version
                else:
                    raise SVDParserValidationError(
                        f'Invalid detected schema version '
                        f'"{parsed_schema_version}"')

        version_part = schema_ver_validation.replace('.', '_')
        schema_file_path = os.path.join(os.path.dirname(__file__), 'schemas',
                                        f'CMSIS-SVD_{version_part}.xsd')

        if not os.path.exists(schema_file_path):
            raise SVDParserValidationError(
                f'Schema file not found: {schema_file_path}')

        with open(schema_file_path, 'rb') as f:
            xmlschema = lxml.etree.XMLSchema(lxml.etree.parse(f))

        if not xmlschema.validate(tree):
            return False, (f'CMSIS-SVD Schema Version {schema_ver_validation}'
                           f': {xmlschema.error_log}')

        return True, ''

    @classmethod
    def validate_xml_file(
        cls, file_path: Union[str, os.PathLike], *args, **kwargs
    ) -> Tuple[bool, str]:
        return cls.validate_xml_tree(etree.parse(file_path), *args, **kwargs)

    @classmethod
    def validate_xml_str(cls, xml_str: str, *args, **kwargs) -> Tuple[bool, str]:
        return cls.validate_xml_tree(
            lxml.etree.fromstring(xml_str).getroottree(), *args, **kwargs)

    @classmethod
    def for_xml_file(cls, path: Union[str, os.PathLike]) -> 'SVDParser':
        """Create a new parser for the provided SVD XML file

        These files often have either the .xml or .svd extension and may
        be found as part of CMSIS packs or as part of the data provided
        by the cmsis-svd project.
        """
        return cls(etree.parse(path))

    @classmethod
    def for_packaged_svd(
        cls, package_root: Union[str, os.PathLike], vendor: str, filename: str
    ) -> Union['SVDParser', None]:
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
        path = os.path.join(package_root, vendor, os.path.basename(filename))
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
    def for_mcu(
        cls, package_root: Union[str, os.PathLike], mcu: str
    ) -> Union['SVDParser', None]:
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

    def __init__(self, tree: ElementTree, remove_reserved: bool = False):
        self.remove_reserved: bool = remove_reserved
        self._tree: ElementTree = tree
        self._root: Element = self._tree.getroot()

    @staticmethod
    def _parse_dim_index(text_value: str) -> Tuple[str, List[str]]:
        if ',' in text_value:
            dim_index = text_value.split(',')
            return ',', dim_index
        elif '-' in text_value:
            # some files use <dimIndex>0-3</dimIndex> as an inclusive inclusive
            # range
            start, stop = text_value.split('-')
            dim_index = []

            if start.isalpha() and stop.isalpha():
                start_val = ord(start)
                stop_val = ord(stop)
                dim_index = [chr(val) for val in range(start_val, stop_val + 1)]

            elif start.isdigit() and stop.isdigit():
                start_val = int(start)
                stop_val = int(stop)
                dim_index = [str(val) for val in range(start_val, stop_val + 1)]

            return '-', dim_index
        else:
            raise ValueError(f'Unexpected dim_index_text: "{text_value}"')

    @staticmethod
    def _parse_access_type(text_value: str) -> Union[SVDAccessType, None]:
        access_text = text_value.strip()

        if access_text in [v.value for v in SVDAccessType]:
            access_value = SVDAccessType(access_text)
        elif access_text == SVDAccessType.WRITE_ONCE.value.lower():  # fix
            access_value = SVDAccessType(SVDAccessType.WRITE_ONCE)
        elif access_text == SVDAccessType.READ_WRITE_ONCE.value.lower():  # fix
            access_value = SVDAccessType(SVDAccessType.READ_WRITE_ONCE)
        elif access_text == 'write':  # fix
            access_value = SVDAccessType(SVDAccessType.WRITE_ONLY)
        else:
            print(f'[WARNING] Invalid access type "{access_text}"')
            access_value = None

        return access_value

    @staticmethod
    def _parse_enumerated_value(
        enumerated_value_node: Element
    ) -> SVDEnumeratedValue:
        return SVDEnumeratedValue(
            name=_get_text(enumerated_value_node, 'name'),
            description=_get_text(enumerated_value_node, 'description'),
            value=_get_int(enumerated_value_node, 'value'),
            is_default=_get_bool(enumerated_value_node, 'isDefault')
        )

    def _parse_dim_array_index(
        self, dim_array_node: Element
    ) -> SVDDimArrayIndex:
        enum_values = [self._parse_enumerated_value(ev)
                       for ev in dim_array_node.findall('./enumeratedValue')]

        return SVDDimArrayIndex(
            header_enum_name=_get_text(dim_array_node, 'headerEnumName'),
            enumerated_value=enum_values
        )

    def _parse_dim_element_group(self, node: Element) -> DimElementGroupType:
        dim = _get_int(node, 'dim')

        if dim_index_str := _get_text(node, 'dimIndex'):
            dim_index_sep, dim_index = self._parse_dim_index(dim_index_str)
        else:
            dim_index_sep, dim_index = None, None

        # fix some files omitting dimIndex
        if dim is not None and dim_index is None:
            dim_index = list(range(0, dim))
            dim_index_sep = '-'

        dim_array_idx = None
        if (dim_array_idx_node := node.find('dimArrayIndex')) is not None:
            dim_array_idx = self._parse_dim_array_index(dim_array_idx_node)

        return DimElementGroupType(
            dim=dim,
            dim_increment=_get_int(node, 'dimIncrement'),
            dim_index=dim_index,
            dim_name=_get_text(node, 'dimName'),
            dim_array_index=dim_array_idx,
            dim_index_separator=dim_index_sep,
        )

    def _parse_register_properties_group(
        self, node: Element
    ) -> RegisterPropertiesGroupType:
        if access := _get_text(node, 'access'):
            access = self._parse_access_type(access)

        if protection := _get_text(node, 'protection'):
            protection = SVDProtectionType(protection)

        return RegisterPropertiesGroupType(
            size=_get_int(node, 'size'),
            access=access,
            protection=protection,
            reset_value=_get_int(node, 'resetValue'),
            reset_mask=_get_int(node, 'resetMask'),
        )

    @staticmethod
    def _parse_address_block_usage_type(
        text_value: str
    ) -> Union[SVDAddressBlockUsageType, None]:
        usage_text = text_value.strip()

        if usage_text in [v.value for v in SVDAddressBlockUsageType]:
            usage = SVDAddressBlockUsageType(usage_text)
        else:
            usage = None

        return usage

    def _parse_address_block(
        self, address_block_node: Element
    ) -> Union[SVDAddressBlock, None]:
        usage = None
        if usage_text := _get_text(address_block_node, 'usage'):
            usage = self._parse_address_block_usage_type(usage_text)

        if protection := _get_text(address_block_node, 'protection'):
            protection = SVDProtectionType(protection)

        return SVDAddressBlock(
            offset=_get_int(address_block_node, 'offset'),
            size=_get_int(address_block_node, 'size'),
            usage=usage,
            protection=protection
        )

    @staticmethod
    def _parse_interrupt(interrupt_node: Element) -> SVDInterrupt:
        return SVDInterrupt(
            name=_get_text(interrupt_node, 'name'),
            description=_get_text(interrupt_node, 'description'),
            value=_get_int(interrupt_node, 'value'),
        )

    @staticmethod
    def _parse_write_constraint(
        write_constraint_node: Element
    ) -> SVDWriteConstraint:
        write_constraint_range = None
        if (range_node := write_constraint_node.find('./range')) is not None:
            write_constraint_range = SVDWriteConstraintRange(
                minimum=_get_bool(range_node, 'minimum'),
                maximum=_get_bool(range_node, 'maximum')
            )

        return SVDWriteConstraint(
            write_as_read=_get_bool(write_constraint_node, 'writeAsRead'),
            use_enumerated_values=_get_bool(write_constraint_node, 'useEnumeratedValues'),
            range=write_constraint_range
        )

    @staticmethod
    def _parse_usage_type(text_value: str) -> SVDEnumUsageType:
        usage_text = text_value.strip().lower()
        return SVDEnumUsageType(usage_text)

    def _parse_enumerated_values(
        self, enumerated_values_node: Element
    ) -> SVDEnumeratedValues:
        enum_values = [self._parse_enumerated_value(ev)
                       for ev in enumerated_values_node.findall('./enumeratedValue')]

        if usage := _get_text(enumerated_values_node, 'usage'):
            usage = self._parse_usage_type(usage)

        return SVDEnumeratedValues(
            name=_get_text(enumerated_values_node, 'name'),
            header_enum_name=_get_text(enumerated_values_node, 'headerEnumName'),
            usage=usage,
            enumerated_values=enum_values
        )

    def _parse_field(self, field_node: Element) -> Union[SVDField, SVDFieldArray]:
        dim_element_group = self._parse_dim_element_group(field_node)

        enum_values = None
        if (enum_values_nodes := field_node.findall('./enumeratedValues')) is not None:
            enum_values = [self._parse_enumerated_values(ev) for ev in enum_values_nodes]

        mod_w_value = _get_text(field_node, 'modifiedWriteValues')
        mod_w_value = SVDModifiedWriteValuesType(mod_w_value) if mod_w_value else None

        read_action = _get_text(field_node, 'readAction')
        read_action = SVDReadActionType(read_action) if read_action else None

        write_constraint = None
        if (write_constraint_node := field_node.find('writeConstraint')) is not None:
            write_constraint = self._parse_write_constraint(write_constraint_node)

        access = None
        if (access_text := _get_text(field_node, 'access')) is not None:
            access = self._parse_access_type(access_text)

        field = SVDField(
            name=_get_text(field_node, 'name'),
            description=_get_text(field_node, 'description'),
            lsb=_get_int(field_node, 'lsb'),
            msb=_get_int(field_node, 'msb'),
            bit_offset=_get_int(field_node, 'bitOffset'),
            bit_width=_get_int(field_node, 'bitWidth'),
            bit_range=_get_text(field_node, 'bitRange'),
            access=access,
            modified_write_values=mod_w_value,
            write_constraint=write_constraint,
            read_action=read_action,
            enumerated_values=enum_values or None,
            derived_from=field_node.get('derivedFrom'),
            **dim_element_group
        )

        if field.bit_range is not None:
            m = re.search('\\[([0-9]+):([0-9]+)\\]', field.bit_range)
            field.bit_offset = int(m.group(2))
            field.bit_width = 1 + (int(m.group(1)) - int(m.group(2)))
        elif field.msb is not None:
            field.bit_offset = field.lsb
            field.bit_width = 1 + (field.msb - field.lsb)

        if field.dim is not None:
            return SVDFieldArray(meta_field=field)
        else:
            return field

    def _parse_register(
        self, register_node: Element
    ) -> Union[SVDRegister, SVDRegisterArray]:
        fields = [self._parse_field(f) for f in register_node.findall('./fields/field')
                  if not self.remove_reserved or not _is_reserved_name(f.name)]

        dim_element_group = self._parse_dim_element_group(register_node)
        properties_group = self._parse_register_properties_group(register_node)

        data_type = _get_text(register_node, 'dataType')
        data_type = SVDDataTypeType(data_type) if data_type else None

        mod_w_value = _get_text(register_node, 'modifiedWriteValues')
        mod_w_value = (SVDModifiedWriteValuesType(mod_w_value) if mod_w_value
                       else None)

        read_action = _get_text(register_node, 'readAction')
        read_action = SVDReadActionType(read_action) if read_action else None

        write_constraint = None
        if (w_c_node := register_node.find('./writeConstraint')) is not None:
            write_constraint = self._parse_write_constraint(w_c_node)

        register = SVDRegister(
            name=_get_text(register_node, 'name'),
            display_name=_get_text(register_node, 'displayName'),
            description=_get_text(register_node, 'description'),
            alternate_group=_get_text(register_node, 'alternateGroup'),
            alternate_register=_get_text(register_node, 'alternateRegister'),
            address_offset=_get_int(register_node, 'addressOffset'),
            data_type=data_type,
            modified_write_values=mod_w_value,
            write_constraint=write_constraint,
            read_action=read_action,
            fields=fields,
            derived_from=register_node.get('derivedFrom'),
            **dim_element_group,
            **properties_group
        )

        if register.dim is not None:
            return SVDRegisterArray(meta_register=register)
        else:
            return register

    def _parse_cluster(
        self, cluster_node: Element
    ) -> Union[SVDRegisterCluster, SVDRegisterClusterArray]:
        dim_element_group = self._parse_dim_element_group(cluster_node)
        properties_group = self._parse_register_properties_group(cluster_node)

        sub_cluster = [self._parse_cluster(c)
                       for c in cluster_node.findall('./cluster')]

        registers = [self._parse_register(r)
                     for r in cluster_node.findall('register')]

        cluster = SVDRegisterCluster(
            name=_get_text(cluster_node, 'name'),
            description=_get_text(cluster_node, 'description'),
            alternate_cluster=_get_text(cluster_node, 'alternateCluster'),
            header_struct_name=_get_text(cluster_node, 'headerStructName'),
            address_offset=_get_int(cluster_node, 'addressOffset'),
            derived_from=cluster_node.get('derivedFrom'),
            clusters=sub_cluster,
            registers=registers,
            **dim_element_group,
            **properties_group
        )

        if cluster.dim is not None:
            return SVDRegisterClusterArray(meta_cluster=cluster)
        else:
            return cluster

    def _parse_peripheral(
        self, peripheral_node: Element
    ) -> Union[SVDPeripheral, SVDPeripheralArray]:
        dim_element_group = self._parse_dim_element_group(peripheral_node)
        properties_group = self._parse_register_properties_group(peripheral_node)

        address_blocks = [self._parse_address_block(ad)
                          for ad in peripheral_node.findall('./addressBlock')]

        interrupts = [self._parse_interrupt(i)
                      for i in peripheral_node.findall('./interrupt')]

        registers = [self._parse_register(r)
                     for r in peripheral_node.findall('./registers/register')]

        registers += [self._parse_cluster(r)
                      for r in peripheral_node.findall('./registers/cluster')]

        peripheral = SVDPeripheral(
            name=_get_text(peripheral_node, 'name'),
            version=_get_text(peripheral_node, 'version'),
            description=_get_text(peripheral_node, 'description'),
            alternate_peripheral=_get_text(peripheral_node, 'alternaPeripheral'),
            group_name=_get_text(peripheral_node, 'groupName'),
            prepend_to_name=_get_text(peripheral_node, 'prependToName'),
            append_to_name=_get_text(peripheral_node, 'appendToName'),
            header_struct_name=_get_text(peripheral_node, 'headerStructName'),
            disable_condition=_get_text(peripheral_node, 'disableCondition'),
            base_address=_get_int(peripheral_node, 'baseAddress'),
            address_blocks=address_blocks or None,
            interrupts=interrupts or None,
            registers=registers or None,
            derived_from=peripheral_node.get('derivedFrom'),
            **dim_element_group,
            **properties_group,
        )

        if peripheral.dim is not None:
            return SVDPeripheralArray(meta_peripheral=peripheral)
        else:
            return peripheral

    @staticmethod
    def _parse_sau_regions_config_region(
        region_node: Element
    ) -> SVDSauRegionsConfigRegion:
        return SVDSauRegionsConfigRegion(
            base=_get_int(region_node, 'base'),
            limit=_get_int(region_node, 'limit'),
            access=SVDSauAccessType(_get_text(region_node, 'access')),
            enabled=_parse_bool(region_node.get('enabled')),
            name=region_node.get('name')
        )

    def _parse_sau_regions_config(
        self, sau_region_config_node: Element
    ) -> SVDSauRegionsConfig:
        regions = [self._parse_sau_regions_config_region(r)
                   for r in sau_region_config_node.findall('./region')]

        if protection := sau_region_config_node.get('protectionWhenDisabled'):
            protection = SVDProtectionType(protection)

        return SVDSauRegionsConfig(
            enabled=_parse_bool(sau_region_config_node.get('enabled')),
            protection_when_disabled=protection,
            regions=regions
        )

    def _parse_cpu(self, cpu_node: Element) -> SVDCpu:
        endian = _get_text(cpu_node, 'endian')
        endian = SVDEndianType(endian) if endian is not None else None

        sau_region_config = None
        if (sau_region_config_node := cpu_node.find('./sauRegionsConfig')) is not None:
            sau_region_config = self._parse_sau_regions_config(
                    sau_region_config_node)

        cpu_dict = {e.name: e.value for e in SVDCPUNameType}
        if (cpu_name := _get_text(cpu_node, 'name')) in cpu_dict.values():
            cpu_name = SVDCPUNameType(cpu_name)
        else:
            cpu_dict.update({'CUSTOM': cpu_name})
            cpu_name = Enum('SVDCPUNameType', names=cpu_dict)(cpu_name)

        return SVDCpu(
            name=cpu_name,
            revision=_get_text(cpu_node, 'revision'),
            endian=endian,
            mpu_present=_get_bool(cpu_node, 'mpuPresent'),
            fpu_present=_get_bool(cpu_node, 'fpuPresent'),
            fpu_dp=_get_bool(cpu_node, 'fpuDP'),
            icache_present=_get_bool(cpu_node, 'icachePresent'),
            dcache_present=_get_bool(cpu_node, 'dcachePresent'),
            itcm_present=_get_bool(cpu_node, 'itcmPresent'),
            dtcm_present=_get_bool(cpu_node, 'dtcmPresent'),
            vtor_present=_get_bool(cpu_node, 'vtorPresent'),
            nvic_prio_bits=_get_int(cpu_node, 'nvicPrioBits'),
            vendor_systick_config=_get_bool(cpu_node, 'vendorSystickConfig'),
            device_num_interrupts=_get_int(cpu_node, 'deviceNumInterrupts'),
            sau_num_regions=_get_int(cpu_node, 'sauNumRegions'),
            sau_regions_config=sau_region_config
        )

    def _parse_device(self, device_node: Element) -> SVDDevice:
        properties_group = self._parse_register_properties_group(device_node)

        peripherals = [self._parse_peripheral(p)
                       for p in device_node.findall('./peripherals/peripheral')]

        cpu = None
        if (cpu_node := device_node.find('./cpu')) is not None:
            cpu = self._parse_cpu(cpu_node)

        nsmap_xs = device_node.nsmap.get('xs')
        if nsmap_xs:
            attr_name = f'{{{device_node.nsmap["xs"]}}}noNamespaceSchemaLocation'
            xs_no_namespace_schema_location = device_node.get(attr_name)
        else:
            xs_no_namespace_schema_location = None

        return SVDDevice(
            vendor=_get_text(device_node, 'vendor'),
            vendor_id=_get_text(device_node, 'vendorID'),
            name=_get_text(device_node, 'name'),
            series=_get_text(device_node, 'series'),
            version=_get_text(device_node, 'version'),
            description=_get_text(device_node, 'description'),
            license_text=_get_text(device_node, 'licenseText'),
            cpu=cpu,
            header_system_filename=_get_text(device_node, 'headerSystemFilename'),
            header_definitions_prefix=_get_text(device_node, 'headerDefinitionsPrefix'),
            address_unit_bits=_get_int(device_node, 'addressUnitBits'),
            width=_get_int(device_node, 'width'),
            peripherals=peripherals,
            schema_version=device_node.get('schemaVersion'),
            namespace_xs=nsmap_xs,
            xs_no_namespace_schema_location=xs_no_namespace_schema_location,
            **properties_group
        )

    def get_device(
        self, xml_validation: bool = False, schema_version: str = 'latest',
        schema_version_detection: bool = True
    ) -> SVDDevice:
        """Get the device described by this SVD

        To validate the loaded SVD XML file before parsing, specify the
        `xml_validation` boolean flag. In this case the `SVDParser` try to
        retrieve the XML schema version used by the file via the `schemaVersion`
        attribute of the `device` tag, otherwise if not found the version
        specified by the `schema_version` argument is used, which is the last
        SVD schema version by default. Also, the auto-detection of the schema
        version can be deactivated via the  `schema_version_detection` boolean
        flag, in this case the schema version used is the version provided by the
        `schema_version` argument.
        """
        if xml_validation:
            is_valid, err_str = self.validate_xml_tree(
                self._tree, schema_version, schema_version_detection)
            if not is_valid:
                raise SVDParserValidationError(err_str)

        SVDXmlPreprocessing(self._root).preprocess_xml()
        return self._parse_device(self._root)
