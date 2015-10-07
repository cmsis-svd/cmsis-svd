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
from cmsis_svd.model import SVDCpu
import pkg_resources
import re


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
        elif text_value.startswith('true'):
            return 1
        elif text_value.startswith('false'):
            return 0
        else:
            return int(text_value)  # decimal
    return default


class SVDParser(object):
    """THe SVDParser is responsible for mapping the SVD XML to Python Objects"""
    
    remove_reserved = 0
    expand_arrays_of_registers = 0

    @classmethod
    def for_xml_file(cls, path, remove_reserved = 0, expand_arrays_of_registers = 0):
        return cls(ET.parse(path),remove_reserved,expand_arrays_of_registers)

    @classmethod
    def for_packaged_svd(cls, vendor, filename, remove_reserved = 0, expand_arrays_of_registers = 0):
        resource = "data/{vendor}/{filename}".format(
            vendor=vendor,
            filename=filename
        )
        return cls.for_xml_file(pkg_resources.resource_filename("cmsis_svd", resource, remove_reserved, expand_arrays_of_registers))

    def __init__(self, tree, remove_reserved = 0, expand_arrays_of_registers = 0):
        self.remove_reserved = remove_reserved
        self.expand_arrays_of_registers = expand_arrays_of_registers
        self._tree = tree
        self._root = self._tree.getroot()

    def _parse_enumerated_value(self, enumerated_value_node):
        return SVDEnumeratedValue(
            name=_get_text(enumerated_value_node, 'name'),
            description=_get_text(enumerated_value_node, 'description'),
            value=_get_int(enumerated_value_node, 'value'),
            is_default=_get_int(enumerated_value_node, 'isDefault')
        )

    def _parse_field(self, field_node):
        enumerated_values = []
        for enumerated_value_node in field_node.findall("./enumeratedValues/enumeratedValue"):
            enumerated_values.append(self._parse_enumerated_value(enumerated_value_node))
			
        bit_range=_get_text(field_node, 'bitRange')
        bit_offset=_get_int(field_node, 'bitOffset')
        bit_width=_get_int(field_node, 'bitWidth')
        msb=_get_int(field_node, 'msb')
        lsb=_get_int(field_node, 'lsb')
        if bit_range is not None:
            m=re.search('\[([0-9]+):([0-9]+)\]', bit_range)
            bit_offset=int(m.group(2))
            bit_width=1+(int(m.group(1))-int(m.group(2)))     
        elif msb is not None:
            bit_offset=lsb
            bit_width=1+(msb-lsb)

        return SVDField(
            name=_get_text(field_node, 'name'),
            description=_get_text(field_node, 'description'),
            bit_offset=bit_offset,
            bit_width=bit_width,
            access=_get_text(field_node, 'access'),
            enumerated_values=enumerated_values or None,
        )

    def _parse_register(self, register_node):
        fields = []
        for field_node in register_node.findall('.//field'):
            node = self._parse_field(field_node)
            if self.remove_reserved is 0 or 'reserved' not in node.name.lower():
                fields.append(node)
        dim = _get_int(register_node, 'dim')
        dim_index_text = _get_text(register_node, 'dimIndex')
        if dim is not None:
            if dim_index_text is None:
                dim_index = range(0,dim)                        #some files omit dimIndex 
            elif ',' in dim_index_text:
                dim_index = dim_index_text.split(',')
            elif '-' in dim_index_text:                              #some files use <dimIndex>0-3</dimIndex> as an inclusive inclusive range
                m=re.search('([0-9]+)-([0-9]+)', dim_index_text)
                dim_index = range(int(m.group(1)),int(m.group(2))+1)
        else:
            dim_index = None
        return SVDRegister(
            name=_get_text(register_node, 'name'),
            description=_get_text(register_node, 'description'),
            address_offset=_get_int(register_node, 'addressOffset'),
            size=_get_int(register_node, 'size'),
            access=_get_text(register_node, 'access'),
            reset_value=_get_int(register_node, 'resetValue'),
            reset_mask=_get_int(register_node, 'resetMask'),
            fields=fields,
            dim=dim, 
            dim_increment=_get_int(register_node, 'dimIncrement'), 
            dim_index=dim_index
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
        registers = None
        if peripheral_node.find('registers'):       #it may be importat to distinguish an empty array of registers from the registers tag missing completly 
            registers = []
        for register_node in peripheral_node.findall('./registers/register'):
            reg = self._parse_register(register_node)
            if reg.dim and self.expand_arrays_of_registers is 1:
                for r in duplicate_array_of_registers(reg):
                    registers.append(r)
            elif self.remove_reserved is 0 or 'reserved' not in reg.name.lower() :
                registers.append(reg)

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
            derived_from = peripheral_node.get("derivedFrom"),
            description=_get_text(peripheral_node, 'description'),
            prepend_to_name=_get_text(peripheral_node, 'prependToName'),
            base_address=_get_int(peripheral_node, 'baseAddress'),
            address_block=address_block,
            interrupts=interrupts,
            registers=registers,
            size = _get_int(peripheral_node,"size"),                      
            access = _get_text(peripheral_node, 'access'),                    
            protection = _get_text(peripheral_node, 'protection'),            
            reset_value = _get_int(peripheral_node,"resetValue"),          
            reset_mask = _get_int(peripheral_node,"resetMask")
        )

    def _parse_device(self, device_node):
        peripherals = []
        for peripheral_node in device_node.findall('.//peripheral'):
            peripherals.append(self._parse_peripheral(peripheral_node))
        cpu_node = device_node.find('./cpu')
        cpu = SVDCpu(
            name = _get_text(cpu_node, 'name'),
            revision = _get_text(cpu_node, 'revision'),
            endian = _get_text(cpu_node, 'endian'),
            mpu_present = _get_int(cpu_node, 'mpuPresent'),
            fpu_present = _get_int(cpu_node, 'fpuPresent'),
            fpu_dp = _get_int(cpu_node, 'fpuDP'),
            icache_present = _get_int(cpu_node, 'icachePresent'),
            dcache_present = _get_int(cpu_node, 'dcachePresent'),
            itcm_present = _get_int(cpu_node, 'itcmPresent'),
            dtcm_present = _get_int(cpu_node, 'dtcmPresent'),
            vtor_present = _get_int(cpu_node, 'vtorPresent'),
            nvic_prio_bits = _get_int(cpu_node, 'nvicPrioBits'),
            vendor_systick_config = _get_int(cpu_node, 'vendorSystickConfig'),
            device_num_interrupts = _get_int(cpu_node, 'vendorSystickConfig'),
            sau_num_regions = _get_int(cpu_node, 'vendorSystickConfig'),
            sau_regions_config = _get_text(cpu_node, 'sauRegionsConfig')
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
            size = _get_int(device_node,"size"),                      
            access = _get_text(device_node, 'access'),                    
            protection = _get_text(device_node, 'protection'),            
            reset_value = _get_int(device_node,"resetValue"),          
            reset_mask = _get_int(device_node,"resetMask")
        )

    def get_device(self):
        """Get the device described by this SVD"""
        return self._parse_device(self._root)
        
def duplicate_array_of_registers(input):    #expects a SVDRegister which is an array of registers    
    output = []
    assert(input.dim == len(input.dim_index))
    for i in range(input.dim):
        output.append(SVDRegister(
                name=input.name % input.dim_index[i],
                description=input.description,
                address_offset=input.address_offset+input.dim_increment*i,
                size=input.size,
                access=input.access,
                reset_value=input.reset_value,
                reset_mask=input.reset_mask,
                fields=input.fields,
                dim=None, 
                dim_increment=None, 
                dim_index=None
            )
        )
    return output

def inherit_register_defaults(source,dest):
    if source.size is not None:
        if dest.size is None:
            dest.size = source.size
    if source.access is not None:
        if dest.access is None:
            dest.access = source.access
    if source.protection is not None:
        if dest.protection is None:
            dest.protection = source.protection
    if source.reset_value is not None:
        if dest.reset_value is None:
            dest.reset_value = source.reset_value
    if source.reset_mask is not None:
        if dest.reset_mask is None:
            dest.reset_mask = source.reset_mask

def propagate_defaults(device):
    if device.peripherals:
        for peripheral in device.peripherals:
            if peripheral.derived_from:
                parent = None;
                for p in device.peripherals:
                    if p.name == peripheral.derived_from:
                        parent = p      #TODO support dot see http://www.keil.com/pack/doc/CMSIS/SVD/html/svd__outline_pg.html
                if peripheral.description is None:
                    peripheral.description = parent.description
                if peripheral.prepend_to_name is None:
                    peripheral.prepend_to_name = parent.prepend_to_name
                if peripheral.address_block is None:
                    peripheral.address_block = parent.address_block
                #if peripheral.interrupts is None:
                #    peripheral.interrupts = parent.interrupts
                if peripheral.registers is None:     
                    peripheral.registers = parent.registers
                inherit_register_defaults(parent,peripheral)

            inherit_register_defaults(device,peripheral)

            if peripheral.registers:
                for register in peripheral.registers:
                    inherit_register_defaults(peripheral,register)

    return device
        
        

