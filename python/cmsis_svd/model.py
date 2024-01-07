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

from typing import (List, Optional, Any, Union, TypedDict, Generator, Type, cast,
                    Callable, Dict)
from dataclasses import dataclass, field, fields
from enum import Enum
import inspect
import copy

import six
import lxml
from lxml import etree


################################################################################
# Utils
################################################################################

def _none_as_empty(v: Any) -> Generator[Any, None, None]:
    if v is not None:
        for e in v:
            yield e


def isinstance_by_str(instance: Any, type_name: str) -> bool:
    if (cls := globals().get(type_name, None)) and inspect.isclass(cls):
        return isinstance(instance, cls)
    return False


################################################################################
# CMSIS-SVD Model Base class
################################################################################

class SVDModelSerializersBinder:
    __serializer_classes__: Dict[str, Type] = {}

    def __init__(self) -> None:
        # Serializers Dependencies Injection
        # Since serializers and model are tightly coupled this dependencies
        # injection avoid circular Python import dependencies.
        if len(self.__serializer_classes__) == 0:
            from .serializers.json import SVDJsonSerializer
            self.__serializer_classes__['json'] = SVDJsonSerializer
            from .serializers.xml import SVDXmlSerializer
            self.__serializer_classes__['xml'] = SVDXmlSerializer

        json_serializer = self.__serializer_classes__['json'](self)
        self.to_dict: Callable[..., dict] = json_serializer.to_dict
        self.to_json: Callable[..., str] = json_serializer.to_json
        self.to_json_file: Callable[..., None] = json_serializer.to_json_file
        xml_serializer = self.__serializer_classes__['xml'](self)
        self.to_xml_node: Callable[..., lxml.etree._Element] = xml_serializer.to_xml_node
        self.to_xml: Callable[..., str] = xml_serializer.to_xml
        self.to_xml_file: Callable[..., None] = xml_serializer.to_xml_file


class SVDElementError(Exception):
    pass


@dataclass
class SVDElement(SVDModelSerializersBinder):
    """Base class for all SVD Elements"""
    parent: Optional['SVDElement'] = field(default=None)

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        SVDModelSerializersBinder.__init__(obj)
        return obj

    def get_parent(self, svd_class: Type['SVDElement']) -> 'SVDElement':
        current_svd_item = self
        while parent := getattr(current_svd_item, 'parent', None):
            if isinstance(parent, svd_class):
                return parent
            else:
                current_svd_item = parent

        raise SVDElementError(f'Parent of type {svd_class} not found for '
                              f'{str(self)}')

    def get_parent_device(self) -> 'SVDDevice':
        if isinstance(self, SVDDevice):
            return self
        return cast(SVDDevice, self.get_parent(SVDDevice))

    def get_parent_peripheral(self) -> 'SVDPeripheral':
        if isinstance(self, SVDPeripheral):
            return self
        return cast(SVDPeripheral, self.get_parent(SVDPeripheral))


################################################################################
# CMSIS-SVD Model Data Type
################################################################################

class SVDCPUNameType(Enum):
    CM0 = 'CM0'          # Arm Cortex-M0
    CM0PLUS = 'CM0PLUS'  # Arm Cortex-M0+
    CM0_PLUS = 'CM0+'    # Arm Cortex-M0+
    CM1 = 'CM1'          # Arm Cortex-M1
    CM3 = 'CM3'          # Arm Cortex-M3
    CM4 = 'CM4'          # Arm Cortex-M4
    CM7 = 'CM7'          # Arm Cortex-M7
    CM23 = 'CM23'        # Arm Cortex-M23
    CM33 = 'CM33'        # Arm Cortex-M33
    CM35P = 'CM35P'      # Arm Cortex-M35P
    CM52 = 'CM52'        # Arm Cortex-M52
    CM55 = 'CM55'        # Arm Cortex-M55
    CM85 = 'CM85'        # Arm Cortex-M85
    SC000 = 'SC000'      # Arm Secure Core SC000
    SC300 = 'SC300'      # Arm Secure Core SC300
    CA5 = 'CA5'          # Arm Cortex-A5
    CA7 = 'CA7'          # Arm Cortex-A7
    CA8 = 'CA8'          # Arm Cortex-A8
    CA9 = 'CA9'          # Arm Cortex-A9
    CA15 = 'CA15'        # Arm Cortex-A15
    CA17 = 'CA17'        # Arm Cortex-A17
    CA53 = 'CA53'        # Arm Cortex-A53
    CA57 = 'CA57'        # Arm Cortex-A57
    CA72 = 'CA72'        # Arm Cortex-A72
    SMC1 = 'SMC1'        # Arm China STAR-MC1
    OTHER = 'other'      # other processor architectures


class SVDProtectionType(Enum):
    SECURE = 's'      # secure permission required for access
    NON_SECURE = 'n'  # non-secure or secure permission required for access
    PRIVILEGED = 'p'  # privileged permission required for access


class SVDSauAccessType(Enum):
    NON_SECURE = 'n'       # non-secure
    SECURE_CALLABLE = 'c'  # secure callable


class SVDAccessType(Enum):
    READ_ONLY = 'read-only'
    WRITE_ONLY = 'write-only'
    READ_WRITE = 'read-write'
    WRITE_ONCE = 'writeOnce'
    READ_WRITE_ONCE = 'read-writeOnce'


class SVDAddressBlockUsageType(Enum):
    REGISTERS = 'registers'
    BUFFER = 'buffer'
    RESERVED = 'reserved'


class SVDDataTypeType(Enum):
    UINT8_T = 'uint8_t'
    UINT16_T = 'uint16_t'
    UINT32_T = 'uint32_t'
    UINT64_T = 'uint64_t'
    INT8_T = 'int8_t'
    INT16_T = 'int16_t'
    INT32_T = 'int32_t'
    INT64_T = 'int64_t'
    UINT8_T_1 = 'uint8_t *'
    UINT16_T_1 = 'uint16_t *'
    UINT32_T_1 = 'uint32_t *'
    UINT64_T_1 = 'uint64_t *'
    INT8_T_1 = 'int8_t *'
    INT16_T_1 = 'int16_t *'
    INT32_T_1 = 'int32_t *'
    INT64_T_1 = 'int64_t *'


class SVDEndianType(Enum):
    LITTLE = 'little'
    BIG = 'big'
    SELECTABLE = 'selectable'
    OTHER = 'other'


class SVDEnumUsageType(Enum):
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read-write"


class SVDModifiedWriteValuesType(Enum):
    ONE_TO_CLEAR = 'oneToClear'
    ONE_TO_SET = 'oneToSet'
    ONE_TO_TOGGLE = 'oneToToggle'
    ZERO_TO_CLEAR = 'zeroToClear'
    ZERO_TO_SET = 'zeroToSet'
    ZERO_TO_TOGGLE = 'zeroToToggle'
    CLEAR = 'clear'
    SET = 'set'
    MODIFY = 'modify'


class SVDReadActionType(Enum):
    CLEAR = 'clear'
    SET = 'set'
    MODIFY = 'modify'
    MODIFY_EXTERNAL = 'modifyExternal'


SvdRegistersListType = List[Union[
    'SVDRegister', 'SVDRegisterCluster', 'SVDRegisterArray',
    'SVDRegisterClusterArray'
]]


################################################################################
# CMSIS-SVD Model Special Elements
################################################################################

@dataclass
class SVDDimArrayIndex(SVDElement):
    header_enum_name: Optional[str] = field(default=None)
    enumerated_value: List['SVDEnumeratedValue'] = field(default_factory=list)


@dataclass
class SVDDimElementGroup:
    dim: Optional[int] = field(default=None)
    dim_increment: Optional[int] = field(default=None)
    dim_index: Optional[List[str]] = field(default=None)
    dim_name: Optional[str] = field(default=None)
    dim_array_index: Optional[SVDDimArrayIndex] = field(default=None)
    dim_index_separator: Optional[str] = field(default=None)


class DimElementGroupType(TypedDict):
    dim: int
    dim_increment: int
    dim_index: Optional[List[str]]
    dim_name: Optional[str]
    dim_array_index: Optional[SVDDimArrayIndex]
    dim_index_separator: Optional[str]


@dataclass
class SVDRegisterPropertiesGroup:
    size: Optional[int] = field(default=None)
    access: Optional[SVDAccessType] = field(default=None)
    protection: Optional[SVDProtectionType] = field(default=None)
    reset_value: Optional[int] = field(default=None)
    reset_mask: Optional[int] = field(default=None)


class RegisterPropertiesGroupType(TypedDict):
    size: Optional[int]
    access: Optional[SVDAccessType]
    protection: Optional[SVDProtectionType]
    reset_value: Optional[int]
    reset_mask: Optional[int]


################################################################################
# CMSIS-SVD Model Main Elements
################################################################################

@dataclass
class SVDEnumeratedValue(SVDElement):
    name: Optional[str] = field(default=None)
    description: Optional[str] = field(default=None)
    value: Optional[int] = field(default=None)
    is_default: Optional[bool] = field(default=None)


@dataclass
class SVDWriteConstraintRange(SVDElement):
    minimum: Optional[int] = field(default=None, metadata={'required': True})
    maximum: Optional[int] = field(default=None, metadata={'required': True})


@dataclass
class SVDWriteConstraint(SVDElement):
    write_as_read: Optional[bool] = field(default=None)
    use_enumerated_values: Optional[bool] = field(default=None)
    range: Optional[SVDWriteConstraintRange] = field(default=None)


@dataclass
class SVDEnumeratedValues(SVDElement):
    name: Optional[str] = field(default=None)
    header_enum_name: Optional[str] = field(default=None)
    usage: Optional[SVDEnumUsageType] = field(default=None)
    enumerated_values: List[SVDEnumeratedValue] = field(default_factory=list)
    derived_from: Optional[str] = field(default=None, metadata={'type': 'attribute'})

    def __post_init__(self) -> None:
        self._set_parent_association()

    def _set_parent_association(self) -> None:
        if self.enumerated_values:
            for enumerated_value in self.enumerated_values:
                enumerated_value.parent = self


@dataclass
class SVDField(SVDElement, SVDDimElementGroup):
    name: Optional[str] = field(default=None, metadata={'required': True})
    description: Optional[str] = field(default=None)
    bit_offset: Optional[int] = field(default=None)
    bit_width: Optional[int] = field(default=None)
    lsb: Optional[int] = field(default=None)
    msb: Optional[int] = field(default=None)
    bit_range: Optional[str] = field(default=None)
    access: Optional[SVDAccessType] = field(default=None)
    modified_write_values: Optional[SVDModifiedWriteValuesType] = field(default=None)
    write_constraint: Optional[SVDWriteConstraint] = field(default=None)
    read_action: Optional[SVDReadActionType] = field(default=None)
    enumerated_values: Optional[List[SVDEnumeratedValues]] = field(default=None)
    derived_from: Optional[str] = field(default=None, metadata={'type': 'attribute'})

    def __post_init__(self) -> None:
        self._set_parent_association()

    def _set_parent_association(self) -> None:
        if self.write_constraint:
            self.write_constraint.parent = self

        if self.enumerated_values:
            for enum_values in self.enumerated_values:
                enum_values.parent = self

    @property
    def is_enumerated_type(self) -> bool:
        """Return True if the field is an enumerated type"""
        return self.enumerated_values is not None

    @property
    def is_reserved(self) -> bool:
        return self.name.lower() == 'reserved'


@dataclass
class SVDRegister(SVDElement, SVDDimElementGroup, SVDRegisterPropertiesGroup):
    name: Optional[str] = field(default=None, metadata={'required': True})
    display_name: Optional[str] = field(default=None)
    description: Optional[str] = field(default=None)
    alternate_group: Optional[str] = field(default=None)
    alternate_register: Optional[str] = field(default=None)
    address_offset: Optional[int] = field(default=None, metadata={'required': True})
    data_type: Optional[SVDDataTypeType] = field(default=None)
    modified_write_values: Optional[SVDModifiedWriteValuesType] = field(default=None)
    write_constraint: Optional[SVDWriteConstraint] = field(default=None)
    read_action: Optional[SVDReadActionType] = field(default=None)
    fields: List[Union[SVDField, 'SVDFieldArray']] = field(default_factory=list)
    derived_from: Optional[str] = field(default=None, metadata={'type': 'attribute'})

    def __post_init__(self) -> None:
        self._set_parent_association()

    def _set_parent_association(self) -> None:
        if self.write_constraint:
            self.write_constraint.parent = self

        if self.fields:
            for register_field in self.fields:
                register_field.parent = self

    def get_fields(self) -> List[SVDField]:
        collect = []

        for f in self.fields:
            if isinstance(f, SVDField):
                collect.append(f)
            elif isinstance_by_str(f, 'SVDFieldArray'):
                collect.extend(f.fields)

        return collect

    @property
    def is_reserved(self) -> bool:
        return 'reserved' in self.name.lower()


@dataclass
class SVDRegisterCluster(SVDElement, SVDDimElementGroup, SVDRegisterPropertiesGroup):
    name: Optional[str] = field(default=None, metadata={'required': True})
    description: Optional[str] = field(default=None)
    alternate_cluster: Optional[str] = field(default=None)
    header_struct_name: Optional[str] = field(default=None)
    address_offset: Optional[int] = field(default=None, metadata={'required': True})
    registers: List[Union[SVDRegister, 'SVDRegisterArray']] = field(default_factory=list)
    clusters: List[Union['SVDRegisterCluster', 'SVDRegisterClusterArray']] = field(default_factory=list)
    derived_from: Optional[str] = field(default=None, metadata={'type': 'attribute'})

    def __post_init__(self: 'SVDRegisterCluster') -> None:
        self._set_parent_association()
        self._registers_address_relocation()

    def _registers_address_relocation(self) -> None:
        if self.dim is None:
            for register in self.registers:
                if isinstance(register, SVDRegister):
                    register.name = f'{self.name}_{register.name}'
                    register.address_offset = (self.address_offset
                                               + register.address_offset)
                elif isinstance_by_str(register, 'SVDRegisterArray'):
                    for sub_register in register.registers:
                        sub_register.name = f'{self.name}_{sub_register.name}'
                        sub_register.address_offset = (self.address_offset
                                                       + sub_register.address_offset)

    def _set_parent_association(self) -> None:
        if self.clusters:
            for cluster in self.clusters:
                cluster.parent = self
                if isinstance(cluster, SVDRegisterClusterArray):
                    cluster.meta_cluster.parent = self

        if self.registers:
            for register in self.registers:
                register.parent = self
                if isinstance(register, SVDRegisterArray):
                    register.meta_register.parent = self

    @property
    def is_reserved(self) -> bool:
        return 'reserved' in self.name.lower()


@dataclass
class SVDAddressBlock(SVDElement):
    offset: Optional[int] = field(default=None, metadata={'required': True})
    size: Optional[int] = field(default=None, metadata={'required': True})
    usage: Optional[SVDAddressBlockUsageType] = field(default=None, metadata={'required': True})
    protection: Optional[SVDProtectionType] = field(default=None)


@dataclass
class SVDInterrupt(SVDElement):
    name: Optional[str] = field(default=None, metadata={'required': True})
    description: Optional[str] = field(default=None)
    value: Optional[int] = field(default=None, metadata={'required': True})


@dataclass
class SVDPeripheral(SVDElement, SVDDimElementGroup, SVDRegisterPropertiesGroup):
    name: Optional[str] = field(default=None, metadata={'required': True})
    version: Optional[str] = field(default=None)
    description: Optional[str] = field(default=None)
    alternate_peripheral: Optional[str] = field(default=None)
    group_name: Optional[str] = field(default=None)
    prepend_to_name: Optional[str] = field(default=None)
    append_to_name: Optional[str] = field(default=None)
    header_struct_name: Optional[str] = field(default=None)
    disable_condition: Optional[str] = field(default=None)
    base_address: Optional[int] = field(default=None, metadata={'required': True})
    address_blocks: Optional[List[SVDAddressBlock]] = field(default=None)
    interrupts: Optional[List[SVDInterrupt]] = field(default=None)
    registers: Optional[SvdRegistersListType] = field(default=None)
    derived_from: Optional[str] = field(default=None, metadata={'type': 'attribute'})

    def __post_init__(self) -> None:
        self._set_parent_association()
        self._set_prepend_append_to_name()

    def _set_prepend_append_to_name(self) -> None:
        if self.prepend_to_name is None and self.append_to_name is None:
            return

        for reg in self.get_registers():
            if self.prepend_to_name is not None:
                reg.name = self.prepend_to_name + reg.name
            if self.append_to_name is not None:
                reg.name += self.append_to_name

    def _set_parent_association(self) -> None:
        for interrupt in _none_as_empty(self.interrupts):
            interrupt.parent = self

        for address_block in _none_as_empty(self.address_blocks):
            address_block.parent = self

        for reg in _none_as_empty(self.registers):
            reg.parent = self
            if isinstance(reg, SVDRegisterArray):
                reg.meta_register.parent = self

    def _get_cluster_registers(
        self, cluster: Union[SVDRegisterCluster, 'SVDRegisterClusterArray']
    ) -> List['SVDRegister']:
        registers = []

        if isinstance(cluster, SVDRegisterCluster):
            for reg in cluster.registers:
                if isinstance(reg, SVDRegister):
                    registers.append(reg)
                elif isinstance_by_str(reg, 'SVDRegisterArray'):
                    registers.extend(reg.registers)
                elif (isinstance(reg, SVDRegisterCluster)
                      or isinstance_by_str(reg, 'SVDRegisterClusterArray')):
                    self._get_cluster_registers(reg)

            for sub_cluster in cluster.clusters:
                registers.extend(self._get_cluster_registers(sub_cluster))

        elif isinstance_by_str(cluster, 'SVDRegisterClusterArray'):
            for sub_cluster in cluster.clusters:
                registers.extend(self._get_cluster_registers(sub_cluster))

        return registers

    def get_registers(self) -> List[SVDRegister]:
        registers = []

        for reg in _none_as_empty(self.registers):
            if isinstance(reg, SVDRegister):
                registers.append(reg)
            elif isinstance_by_str(reg, 'SVDRegisterArray'):
                registers.extend(reg.registers)
            elif (isinstance(reg, SVDRegisterCluster)
                  or isinstance_by_str(reg, 'SVDRegisterClusterArray')):
                registers.extend(self._get_cluster_registers(reg))

        return registers


@dataclass
class SVDSauRegionsConfigRegion(SVDElement):
    base: Optional[int] = field(default=None, metadata={'required': True})
    limit: Optional[int] = field(default=None, metadata={'required': True})
    access: Optional[SVDSauAccessType] = field(default=None, metadata={'required': True})
    enabled: bool = field(default=True, metadata={'type': 'attribute'})
    name: Optional[str] = field(default=None, metadata={'type': 'attribute'})


@dataclass
class SVDSauRegionsConfig(SVDElement):
    regions: List[SVDSauRegionsConfigRegion] = field(default_factory=list)
    enabled: Optional[bool] = field(default=None, metadata={'type': 'attribute'})
    protection_when_disabled: Optional[SVDProtectionType] = field(default=None, metadata={'type': 'attribute'})


@dataclass
class SVDCpu(SVDElement):
    name: Optional[Union[SVDCPUNameType, str]] = field(default=None, metadata={'required': True})
    revision: Optional[str] = field(default=None, metadata={'required': True})
    endian: Optional[SVDEndianType] = field(default=None, metadata={'required': True})
    mpu_present: Optional[bool] = field(default=None, metadata={'required': True})
    fpu_present: Optional[bool] = field(default=None, metadata={'required': True})
    fpu_dp: Optional[bool] = field(default=None)
    dsp_present: Optional[bool] = field(default=None)
    icache_present: Optional[bool] = field(default=None)
    dcache_present: Optional[bool] = field(default=None)
    itcm_present: Optional[bool] = field(default=None)
    dtcm_present: Optional[bool] = field(default=None)
    vtor_present: Optional[bool] = field(default=None)
    nvic_prio_bits: Optional[int] = field(default=None, metadata={'required': True})
    vendor_systick_config: Optional[bool] = field(default=None, metadata={'required': True})
    device_num_interrupts: Optional[int] = field(default=None)
    sau_num_regions: Optional[int] = field(default=None)
    sau_regions_config: Optional[SVDSauRegionsConfig] = field(default=None)

    def __post_init__(self) -> None:
        self._set_parent_association()

    def _set_parent_association(self) -> None:
        if self.sau_regions_config:
            self.sau_regions_config.parent = self


@dataclass
class SVDDevice(SVDElement, SVDRegisterPropertiesGroup):
    vendor: Optional[str] = field(default=None)
    vendor_id: Optional[str] = field(default=None)
    name: Optional[str] = field(default=None, metadata={'required': True})
    series: Optional[str] = field(default=None)
    version: Optional[str] = field(default=None, metadata={'required': True})
    description: Optional[str] = field(default=None, metadata={'required': True})
    license_text: Optional[str] = field(default=None)
    cpu: Optional[SVDCpu] = field(default=None)
    header_system_filename: Optional[str] = field(default=None)
    header_definitions_prefix: Optional[str] = field(default=None)
    address_unit_bits: Optional[int] = field(default=None, metadata={'required': True})
    width: Optional[int] = field(default=None, metadata={'required': True})
    peripherals: List[Union[SVDPeripheral, 'SVDPeripheralArray']] = field(default_factory=list)
    vendor_extensions: Optional[Any] = field(default=None)
    schema_version: Optional[str] = field(default=None, metadata={'type': 'attribute', 'required': True})
    namespace_xs: Optional[str] = field(default=None, metadata={'type': 'attribute', 'required': True})
    xs_no_namespace_schema_location: Optional[str] = field(default=None, metadata={'type': 'attribute', 'required': True})

    def __post_init__(self) -> None:
        self._set_parent_association()

    def _set_parent_association(self) -> None:
        if self.cpu:
            self.cpu.parent = self

        for peripheral in self.peripherals:
            peripheral.parent = self
            if isinstance(peripheral, SVDPeripheralArray):
                peripheral.meta_peripheral.parent = self

    def get_peripherals(self) -> List[SVDPeripheral]:
        collect = []
        for peripheral in self.peripherals:
            if isinstance(peripheral, SVDPeripheral):
                collect.append(peripheral)
            elif isinstance_by_str(peripheral, 'SVDPeripheralArray'):
                collect.extend(peripheral.peripherals)
        return collect


SvdRegisterPropertiesGroupParentElements = Union[
    SVDDevice, SVDPeripheral, SVDRegister, SVDRegisterCluster
]


################################################################################
# Model Array
################################################################################

def _expand_svd_array(
    meta_def: Union[SVDPeripheral, SVDRegister, SVDRegisterCluster, SVDField]
) -> Union[List[SVDPeripheral], List[SVDRegister], List[SVDRegisterCluster], List[SVDField]]:
    expansion = []
    for i in six.moves.range(meta_def.dim):
        params = {f.name: getattr(meta_def, f.name) for f in fields(meta_def)}
        params = copy.deepcopy(params)
        params['dim'] = None

        if meta_def.name and '%s' in meta_def.name and meta_def.dim_index:
            params['name'] = meta_def.name % meta_def.dim_index[i]

        if (isinstance(meta_def, SVDRegister) and meta_def.display_name
                and '%s' in meta_def.display_name and meta_def.dim_index):
            params['display_name'] = meta_def.display_name % meta_def.dim_index[i]

        if isinstance(meta_def, SVDPeripheral):
            params['base_address'] = (meta_def.base_address
                                      + meta_def.dim_increment * i)
        elif isinstance(meta_def, SVDField):
            params['bit_offset'] = (meta_def.bit_offset
                                    + meta_def.dim_increment * i)
        elif isinstance(meta_def, (SVDRegister, SVDRegisterCluster)):
            params['address_offset'] = (meta_def.address_offset
                                        + meta_def.dim_increment * i)

        expansion.append(meta_def.__class__(**params))
    return expansion


@dataclass
class SVDPeripheralArray(SVDElement):
    meta_peripheral: Optional[SVDPeripheral] = None
    peripherals: List[SVDPeripheral] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.peripherals = _expand_svd_array(self.meta_peripheral)


@dataclass
class SVDRegisterArray(SVDElement):
    meta_register: Optional[SVDRegister] = None
    registers: List[SVDRegister] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.registers = _expand_svd_array(self.meta_register)

    @property
    def is_reserved(self) -> bool:
        return 'reserved' in self.meta_register.name.lower()


@dataclass
class SVDRegisterClusterArray(SVDElement):
    meta_cluster: Optional[SVDRegisterCluster] = None
    clusters: List[SVDRegisterCluster] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.clusters = _expand_svd_array(self.meta_cluster)

    def is_reserved(self) -> bool:
        return 'reserved' in self.meta_cluster.name.lower()


@dataclass
class SVDFieldArray(SVDElement):
    meta_field: Optional[SVDField] = None
    fields: List[SVDField] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.fields = _expand_svd_array(self.meta_field)
