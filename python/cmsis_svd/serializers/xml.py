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

from typing import Union, Callable, Any, Type
import enum

import lxml
from lxml import etree

from ..model import (
    SVDDevice, SVDCpu, SVDPeripheral, SVDInterrupt, SVDAddressBlock,
    SVDRegister, SVDRegisterArray, SVDRegisterCluster, SVDRegisterClusterArray,
    SVDField, SVDEnumeratedValue, SVDWriteConstraint, SVDPeripheralArray,
    SVDFieldArray, SVDDimArrayIndex, SVDSauRegionsConfig,
    SVDWriteConstraintRange, SVDSauRegionsConfigRegion, SVDEnumeratedValues,
    SvdRegisterPropertiesGroupParentElements, SVDElement)


################################################################################
# XML Serializer Base Classes
################################################################################

def get_mem_addr_formatter(bit_with: int) -> Callable[[int], str]:
    formatter = '{:#x}'
    if bit_with <= 32:
        formatter = '0x{:08x}'
    elif 32 < bit_with <= 64:
        formatter = '0x{:016x}'
    elif 64 < bit_with <= 128:
        formatter = '0x{:032x}'

    return formatter.format


HEXA_FORMAT = '{:#x}'.format


class XMLSerializationError(Exception):
    pass


class XMLSerializerBase:
    SVD_SERIALIZER_TYPE: Type[SVDElement]

    @classmethod
    def _to_text(cls, value: Union[str, int, bool, enum.Enum, list]) -> str:
        if isinstance(value, (str, int, list)):
            return str(value)
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, enum.Enum):
            return cls._to_text(value.value)
        else:
            raise XMLSerializationError(
                f'Data type serialization not implemented for "{type(value)}".')

    def __init__(self, name: str, nsmap=None) -> None:
        self.root = lxml.etree.Element(name, nsmap=nsmap)

    def to_xml(self) -> lxml.etree._Element:
        raise NotImplementedError('to_xml() not implemented')

    def _append_element(self, element: lxml.etree._Element) -> None:
        self.root.append(element)

    def new_element(
        self, name: str, value: Union[str, int, bool, enum.Enum, None] = None,
        formatter: Callable[[Any], str] = None
    ) -> lxml.etree._Element:
        element = lxml.etree.Element(name)

        if value is not None:
            text = self._to_text(value)
            if formatter is not None:
                text = formatter(value)
            element.text = text

        self.root.append(element)
        return element

    def new_element_if_text(
        self, name: str, value: Union[str, int, bool, enum.Enum, list, None],
        formatter: Callable[[Any], str] = None
    ) -> Union[lxml.etree._Element, None]:
        if value is not None:
            return self.new_element(name, value, formatter)

    def new_attr_if_text(
        self, name: str, value: Union[str, int, bool, enum.Enum, None]
    ) -> None:
        if value is not None:
            self.root.attrib[name] = self._to_text(value)


################################################################################
# SVD Serializers
################################################################################

class SVDRegisterPropertiesGroupXmlSerializer:
    def __init__(self, serializer: XMLSerializerBase,
                 svd_object: SvdRegisterPropertiesGroupParentElements) -> None:
        self._serializer = serializer
        self.svd_object = svd_object

    def attach_register_properties_group(self) -> None:
        self._serializer.new_element_if_text('size', self.svd_object.size)
        self._serializer.new_element_if_text('access', self.svd_object.access)
        self._serializer.new_element_if_text('protection', self.svd_object.protection)
        self._serializer.new_element_if_text('resetValue', self.svd_object.reset_value, HEXA_FORMAT)
        self._serializer.new_element_if_text('resetMask', self.svd_object.reset_mask, HEXA_FORMAT)


class SVDDimElementGroupXmlSerializer:
    SVD_SERIALIZER_TYPE = SvdRegisterPropertiesGroupParentElements

    def __init__(self, serializer: XMLSerializerBase,
                 svd_object: SvdRegisterPropertiesGroupParentElements) -> None:
        self._serializer = serializer
        self.svd_object = svd_object

    def _dim_index_serializer(self) -> Union[str, None]:
        if self.svd_object.dim_index and self.svd_object.dim_index_separator:
            if self.svd_object.dim_index_separator == ',':
                return ','.join([str(e) for e in self.svd_object.dim_index])
            elif self.svd_object.dim_index_separator == '-':
                return (f'{str(self.svd_object.dim_index[0])}'
                        f'-{str(self.svd_object.dim_index[-1])}')

    def attach_dim_element_group(self) -> None:
        self._serializer.new_element_if_text('dim', self.svd_object.dim)
        self._serializer.new_element_if_text('dimIncrement', self.svd_object.dim_increment)
        self._serializer.new_element_if_text('dimIndex', self._dim_index_serializer())
        self._serializer.new_element_if_text('dimName', self.svd_object.dim_name)

        if (array := getattr(self.svd_object, 'dim_array_index', None)) is not None:
            self._serializer._append_element(SVDDimArrayIndexXmlSerializer(array).to_xml())


class SVDEnumeratedValueXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDEnumeratedValue

    def __init__(self, enumerated_value: SVDEnumeratedValue) -> None:
        XMLSerializerBase.__init__(self, 'enumeratedValue')
        self.enumerated_value = enumerated_value

    def to_xml(self) -> lxml.etree._Element:
        self.new_element_if_text('name', self.enumerated_value.name)
        self.new_element_if_text('description', self.enumerated_value.description)
        self.new_element_if_text('value', self.enumerated_value.value, HEXA_FORMAT)
        self.new_element_if_text('is_default', self.enumerated_value.is_default)
        return self.root


class SVDEnumeratedValuesXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDEnumeratedValues

    def __init__(self, enumerated_values: SVDEnumeratedValues) -> None:
        XMLSerializerBase.__init__(self, 'enumeratedValues')
        self.enumerated_values = enumerated_values

    def to_xml(self) -> lxml.etree._Element:
        for ev in self.enumerated_values.enumerated_values:
            self._append_element(SVDEnumeratedValueXmlSerializer(ev).to_xml())

        return self.root


class SVDDimArrayIndexXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDDimArrayIndex

    def __init__(self, dim_array_index: SVDDimArrayIndex) -> None:
        XMLSerializerBase.__init__(self, 'dimArrayIndex')
        self.dim_array_index = dim_array_index

    def to_xml(self) -> lxml.etree._Element:
        self.new_element_if_text('headerEnumName', self.dim_array_index.header_enum_name)
        for ev in self.dim_array_index.enumerated_value:
            self._append_element(SVDEnumeratedValueXmlSerializer(ev).to_xml())
        return self.root


class SVDWriteConstraintRangeXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDWriteConstraintRange

    def __init__(self, write_constraint_range: SVDWriteConstraintRange) -> None:
        XMLSerializerBase.__init__(self, 'range')
        self.write_constraint_range = write_constraint_range

    def to_xml(self) -> lxml.etree._Element:
        self.new_element('minimum', self.write_constraint_range.minimum)
        self.new_element('maximum', self.write_constraint_range.maximum)
        return self.root


class SVDWriteConstraintXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDWriteConstraint

    def __init__(self, write_constraint: SVDWriteConstraint) -> None:
        XMLSerializerBase.__init__(self, 'writeConstraint')
        self.write_constraint = write_constraint

    def to_xml(self) -> lxml.etree._Element:
        self.new_element_if_text('writeAsRead', self.write_constraint.write_as_read)
        self.new_element_if_text('useEnumeratedValues', self.write_constraint.use_enumerated_values)

        if self.write_constraint.range is not None:
            self._append_element(SVDWriteConstraintRangeXmlSerializer(
                self.write_constraint.range).to_xml())

        return self.root


class SVDFieldXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDField

    def __init__(self, field: SVDField) -> None:
        XMLSerializerBase.__init__(self, 'field')
        self.field = field

    def to_xml(self) -> lxml.etree._Element:
        self.new_element('name', self.field.name)
        self.new_element_if_text('description', self.field.description)
        self.new_element_if_text('description', self.field.access)

        if self.field.bit_offset is not None and self.field.bit_width is not None:
            self.new_element('bitOffset', self.field.bit_offset)
            self.new_element('bitWidth', self.field.bit_width)

        if self.field.lsb is not None and self.field.msb is not None:
            self.new_element('lsb', self.field.lsb)
            self.new_element('msb', self.field.msb)

        self.new_element_if_text('bitRange', self.field.bit_range)
        self.new_element_if_text('access', self.field.access)
        self.new_element_if_text('modifiedWriteValues', self.field.modified_write_values)

        if self.field.write_constraint is not None:
            self._append_element(SVDWriteConstraintXmlSerializer(
                self.field.write_constraint).to_xml())

        self.new_element_if_text('readAction', self.field.read_action)

        for ev in (self.field.enumerated_values or []):
            self._append_element(SVDEnumeratedValuesXmlSerializer(ev).to_xml())

        return self.root


class SVDRegisterXmlSerializer(XMLSerializerBase, SVDDimElementGroupXmlSerializer,
                               SVDRegisterPropertiesGroupXmlSerializer):
    SVD_SERIALIZER_TYPE = SVDRegister

    def __init__(self, register: SVDRegister) -> None:
        XMLSerializerBase.__init__(self, 'register')
        SVDDimElementGroupXmlSerializer.__init__(self, self, register)
        SVDRegisterPropertiesGroupXmlSerializer.__init__(self, self, register)
        self.register = register

    def to_xml(self) -> lxml.etree._Element:
        self.attach_dim_element_group()

        peripheral = self.register.get_parent_peripheral()
        reg_name = self.register.name
        if peripheral.prepend_to_name is not None and self.register.dim is None:
            reg_name = reg_name[len(peripheral.prepend_to_name):]

        if peripheral.append_to_name is not None and self.register.dim is None:
            reg_name = reg_name[:len(reg_name)-len(peripheral.append_to_name)]

        self.new_element('name', reg_name)
        self.new_element_if_text('displayName', self.register.display_name)
        self.new_element_if_text('description', self.register.description)
        self.new_element_if_text('alternateGroup', self.register.alternate_group)
        self.new_element_if_text('alternateRegister', self.register.alternate_register)
        addr_format = get_mem_addr_formatter(self.register.get_parent_device().width)
        self.new_element('addressOffset', self.register.address_offset, addr_format)
        self.attach_register_properties_group()
        self.new_element_if_text('dataType', self.register.data_type)
        self.new_element_if_text('modifiedWriteValues', self.register.modified_write_values)

        if self.register.write_constraint is not None:
            self._append_element(SVDWriteConstraintXmlSerializer(
                self.register.write_constraint).to_xml())

        self.new_element_if_text('readAction', self.register.read_action)

        fields_node = self.new_element('fields')
        for field in self.register.fields:
            field_to_serialize = field
            if isinstance(field, SVDFieldArray):
                field_to_serialize = field.meta_field
            fields_node.append(SVDFieldXmlSerializer(field_to_serialize).to_xml())

        return self.root


class SVDRegisterClusterXmlSerializer(XMLSerializerBase, SVDDimElementGroupXmlSerializer,
                                      SVDRegisterPropertiesGroupXmlSerializer):
    SVD_SERIALIZER_TYPE = SVDRegisterCluster

    def __init__(self, cluster: SVDRegisterCluster) -> None:
        XMLSerializerBase.__init__(self, 'cluster')
        SVDDimElementGroupXmlSerializer.__init__(self, self, cluster)
        SVDRegisterPropertiesGroupXmlSerializer.__init__(self, self, cluster)
        self.cluster = cluster

    def to_xml(self) -> lxml.etree._Element:
        self.attach_dim_element_group()
        self.new_element('name', self.cluster.name)
        self.new_element_if_text('description', self.cluster.description)
        self.new_element_if_text('alternateCluster', self.cluster.alternate_cluster)
        self.new_element_if_text('headerStructName', self.cluster.header_struct_name)
        addr_format = get_mem_addr_formatter(self.cluster.get_parent_device().width)
        self.new_element('addressOffset', self.cluster.address_offset, addr_format)
        self.attach_register_properties_group()

        for register in self.cluster.registers:
            if isinstance(register, SVDRegister):
                self._append_element(SVDRegisterXmlSerializer(register).to_xml())
            elif isinstance(register, SVDRegisterArray):
                self._append_element(SVDRegisterXmlSerializer(register.meta_register).to_xml())

        for cluster in self.cluster.clusters:
            cluster_to_serialize = cluster
            if isinstance(cluster, SVDRegisterClusterArray):
                cluster_to_serialize = cluster.meta_cluster
            self._append_element(SVDRegisterClusterXmlSerializer(cluster_to_serialize).to_xml())

        return self.root


class SVDAddressBlockXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDAddressBlock

    def __init__(self, address_block: SVDAddressBlock) -> None:
        XMLSerializerBase.__init__(self, 'addressBlock')
        self.address_block = address_block

    def to_xml(self) -> lxml.etree._Element:
        self.new_element('offset', self.address_block.offset)
        self.new_element('size', self.address_block.size, HEXA_FORMAT)
        self.new_element('usage', self.address_block.usage)
        self.new_element_if_text('protection', self.address_block.protection)
        return self.root


class SVDInterruptBlockXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDInterrupt

    def __init__(self, interrupt: SVDInterrupt) -> None:
        XMLSerializerBase.__init__(self, 'interrupt')
        self.interrupt = interrupt

    def to_xml(self) -> lxml.etree._Element:
        self.new_element('name', self.interrupt.name)
        self.new_element_if_text('description', self.interrupt.description)
        self.new_element('value', self.interrupt.value)
        return self.root


class SVDPeripheralXmlSerializer(XMLSerializerBase, SVDDimElementGroupXmlSerializer,
                                 SVDRegisterPropertiesGroupXmlSerializer):
    SVD_SERIALIZER_TYPE = SVDPeripheral

    def __init__(self, peripheral: SVDPeripheral) -> None:
        XMLSerializerBase.__init__(self, 'peripheral')
        SVDDimElementGroupXmlSerializer.__init__(self, self, peripheral)
        SVDRegisterPropertiesGroupXmlSerializer.__init__(self, self, peripheral)
        self.peripheral = peripheral

    def to_xml(self) -> lxml.etree._Element:
        self.attach_dim_element_group()
        self.new_element('name', self.peripheral.name)
        self.new_element_if_text('version', self.peripheral.version)
        self.new_element_if_text('description', self.peripheral.description)
        self.new_element_if_text('alternatePeripheral', self.peripheral.alternate_peripheral)
        self.new_element_if_text('groupName', self.peripheral.group_name)
        self.new_element_if_text('prependToName', self.peripheral.prepend_to_name)
        self.new_element_if_text('appendToName', self.peripheral.append_to_name)
        self.new_element_if_text('headerStructName', self.peripheral.header_struct_name)
        self.new_element_if_text('disableCondition', self.peripheral.disable_condition)
        addr_format = get_mem_addr_formatter(self.peripheral.get_parent_device().width)
        self.new_element('baseAddress', self.peripheral.base_address, addr_format)
        self.attach_register_properties_group()

        for address_block in (self.peripheral.address_blocks or []):
            self._append_element(SVDAddressBlockXmlSerializer(address_block).to_xml())

        for interrupt in (self.peripheral.interrupts or []):
            self._append_element(SVDInterruptBlockXmlSerializer(interrupt).to_xml())

        registers_node = self.new_element('registers')
        for register in self.peripheral.registers or []:
            if isinstance(register, SVDRegister):
                registers_node.append(SVDRegisterXmlSerializer(register).to_xml())
            elif isinstance(register, SVDRegisterArray):
                registers_node.append(SVDRegisterXmlSerializer(register.meta_register).to_xml())
            elif isinstance(register, SVDRegisterCluster):
                registers_node.append(SVDRegisterClusterXmlSerializer(register).to_xml())

        return self.root


class SVDSauRegionsConfigRegionXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDSauRegionsConfigRegion

    def __init__(self, region: SVDSauRegionsConfigRegion):
        XMLSerializerBase.__init__(self, 'region')
        self.region = region

    def to_xml(self) -> lxml.etree._Element:
        self.new_attr_if_text('enabled', self.region.enabled)
        self.new_attr_if_text('name', self.region.name)
        self.new_element('base', self.region.base)
        self.new_element('limit', self.region.limit)
        self.new_element('access', self.region.access)
        return self.root


class SVDSauRegionsConfigXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDSauRegionsConfig

    def __init__(self, sau_regions_config: SVDSauRegionsConfig):
        XMLSerializerBase.__init__(self, 'sauRegionsConfig')
        self.sau_regions_config = sau_regions_config

    def to_xml(self) -> lxml.etree._Element:
        self.new_attr_if_text('enabled', self.sau_regions_config.enabled)
        self.new_attr_if_text('protectionWhenDisabled', self.sau_regions_config.protection_when_disabled)

        for region in self.sau_regions_config.regions:
            self._append_element(SVDSauRegionsConfigRegionXmlSerializer(region).to_xml())

        return self.root


class SVDCpuXmlSerializer(XMLSerializerBase):
    SVD_SERIALIZER_TYPE = SVDCpu

    def __init__(self, cpu: SVDCpu):
        XMLSerializerBase.__init__(self, 'cpu')
        self.cpu = cpu

    def to_xml(self) -> lxml.etree._Element:
        self.new_element('name', self.cpu.name)
        self.new_element('revision', self.cpu.revision)
        self.new_element('endian', self.cpu.endian)
        self.new_element_if_text('mpuPresent', self.cpu.mpu_present)
        self.new_element_if_text('fpuPresent', self.cpu.fpu_present)
        self.new_element_if_text('fpuDP', self.cpu.fpu_dp)
        self.new_element_if_text('dspPresent', self.cpu.fpu_dp)
        self.new_element_if_text('icachePresent', self.cpu.icache_present)
        self.new_element_if_text('dcachePresent', self.cpu.icache_present)
        self.new_element_if_text('dcachePresent', self.cpu.dcache_present)
        self.new_element_if_text('itcmPresent', self.cpu.itcm_present)
        self.new_element_if_text('dtcmPresent', self.cpu.dtcm_present)
        self.new_element_if_text('vtorPresent', self.cpu.vtor_present)
        self.new_element('nvicPrioBits', self.cpu.nvic_prio_bits)
        self.new_element('vendorSystickConfig', self.cpu.vendor_systick_config)
        self.new_element_if_text('deviceNumInterrupts', self.cpu.device_num_interrupts)
        self.new_element_if_text('sauNumRegions', self.cpu.sau_num_regions)

        if self.cpu.sau_regions_config is not None:
            self.root.append(SVDSauRegionsConfigXmlSerializer(
                self.cpu.sau_regions_config).to_xml())

        return self.root


class SVDDeviceXmlSerializer(XMLSerializerBase, SVDRegisterPropertiesGroupXmlSerializer):
    SVD_SERIALIZER_TYPE = SVDDevice

    def __init__(self, device: SVDDevice):
        self.device = device
        nsmap = None
        if self.device.namespace_xs:
            nsmap = {'xs': self.device.namespace_xs}
        XMLSerializerBase.__init__(self, 'device', nsmap=nsmap)
        SVDRegisterPropertiesGroupXmlSerializer.__init__(self, self, self.device)

    def to_xml(self) -> lxml.etree._Element:
        if self.device.namespace_xs:
            qname = lxml.etree.QName(self.device.namespace_xs, 'noNamespaceSchemaLocation')
            if self.device.xs_no_namespace_schema_location:
                self.root.attrib[qname] = self.device.xs_no_namespace_schema_location

        self.new_attr_if_text('schemaVersion', self.device.schema_version)
        self.new_element_if_text('vendor', self.device.vendor)
        self.new_element_if_text('vendorID', self.device.vendor_id)
        self.new_element('name', self.device.name)
        self.new_element_if_text('series', self.device.series)
        self.new_element('version', self.device.version)
        self.new_element('description', self.device.description)
        self.new_element_if_text('licenseText', self.device.license_text)

        if self.device.cpu is not None:
            self._append_element(SVDCpuXmlSerializer(self.device.cpu).to_xml())

        self.new_element_if_text('headerSystemFilename', self.device.header_system_filename)
        self.new_element_if_text('headerDefinitionsPrefix', self.device.header_definitions_prefix)
        self.new_element('addressUnitBits', self.device.address_unit_bits)
        self.new_element('width', self.device.width)
        self.new_element_if_text('size', self.device.size)
        self.new_element_if_text('access', self.device.access)
        self.new_element_if_text('protection', self.device.protection)

        peripherals_node = self.new_element('peripherals')
        for peripheral in self.device.peripherals:
            to_serialize = peripheral
            if isinstance(peripheral, SVDPeripheralArray):
                to_serialize = peripheral.meta_peripheral
            peripherals_node.append(SVDPeripheralXmlSerializer(to_serialize).to_xml())

        return self.root


SVD_XML_SERIALIZERS = [
    SVDDimElementGroupXmlSerializer,
    SVDEnumeratedValueXmlSerializer,
    SVDEnumeratedValuesXmlSerializer,
    SVDDimArrayIndexXmlSerializer,
    SVDWriteConstraintRangeXmlSerializer,
    SVDWriteConstraintXmlSerializer,
    SVDFieldXmlSerializer,
    SVDRegisterXmlSerializer,
    SVDRegisterClusterXmlSerializer,
    SVDAddressBlockXmlSerializer,
    SVDInterruptBlockXmlSerializer,
    SVDPeripheralXmlSerializer,
    SVDSauRegionsConfigRegionXmlSerializer,
    SVDSauRegionsConfigXmlSerializer,
    SVDCpuXmlSerializer,
    SVDDeviceXmlSerializer,
]


class SVDXmlSerializer:
    def __init__(self, svd_item: SVDElement):
        self.svd_item = svd_item

    def _get_serializer(self) -> XMLSerializerBase:
        for serializer in SVD_XML_SERIALIZERS:
            if type(self.svd_item) == serializer.SVD_SERIALIZER_TYPE:
                return serializer(self.svd_item)
        raise XMLSerializationError(f'Serializer not found for {self.svd_item}.')

    def to_xml_node(self) -> lxml.etree._Element:
        return self._get_serializer().to_xml()

    def to_xml(self, pretty_print: bool = True,
               xml_declaration: bool = True) -> str:
        encoding = 'utf-8'
        return lxml.etree.tostring(
            self.to_xml_node(),
            pretty_print=pretty_print,
            xml_declaration=xml_declaration,
            encoding=encoding,
        ).decode(encoding)

    def to_xml_file(self, path: str, pretty_print: bool = True,
                    xml_declaration: bool = True) -> None:
        with open(path, 'w') as f:
            f.write(self.to_xml(pretty_print, xml_declaration))
