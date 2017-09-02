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
from itertools import count

REGISTER_PROPERTY_KEYS = {"size", "access", "protection", "reset_value", "reset_mask"}
LIST_TYPE_KEYS = {"register_arrays", "registers", "fields", "peripherals", "interrupts"}

class Element(object):
    """Base class for all SVD Elements"""

    def __init__(self, node, parent, name, elements=None, **kwargs):
        self.node = node
        self.name = name
        self.parent = parent

        self.__dict__.update(kwargs)
        self._xml_fields = ['name', *kwargs.keys()]

        self._elements = {}
        if parent is not None:
            parent._register_element(self)

        if elements is not None:
            setattr(self, elements, self._elements)

    def _register_element(self, elem):
        self._elements[elem.name] = elem

    def __getitem__(self, name):
        return self._elements[name]

    def __iter__(self):
        return iter(self._elements.values())

        # FIXME
        # for some attributes, try to grab from parent
        if attr in REGISTER_PROPERTY_KEYS:
            value = getattr(self.parent, attr, value_self)
        # if value is None and this is a list type, transform to empty list
        if value is None and attr in LIST_TYPE_KEYS:
            value = []

    def to_dict(self):
        def dictify(v):
            if isinstance(v, Element):
                return v.to_dict()
            elif isinstance(v, list):
                return [ dictify(e) for e in v ]
            elif isinstance(v, dict):
                return { k: dictivy(e) for k, e in v.items() }
            else:
                return v
        return { k: dictify(getattr(self, v)) for k in self._xml_fields }

class EnumeratedValue(Element):
    pass

class Field(Element):
    def __init__(self, **kwargs):
        super().__init__(elements='enumerated_values', **kwargs)

    @property
    def is_enumerated_type(self):
        """Return True if the field is an enumerated type"""
        return bool(self.enumerated_values)

    @property
    def is_reserved(self):
        return 'reserved' in self.name.lower()

    def __repr__(self):
        return '<Field {self.name} ({self.description}) {self.bit_width}bit@0x{addr:0{width}x}+{self.bit_offset}>'.format(
                self=self,
                addr=self.parent.address_offset,
                width=self.parent.size//4)

class Register(Element):
    def __init__(self, is_array=False, **kwargs):
        # When deriving a register, it is mandatory to specify at least the name, the description, and the addressOffset
        super().__init__(elements='fields', is_array=is_array, **kwargs)

    @property
    def is_reserved(self):
        return 'reserved' in self.name.lower()

    def __repr__(self):
        access = self.access.replace('read', 'R').replace('write', 'W').replace('-', '') if self.access else ''
        fields = '[{}]'.format(', '.join('{}:{}'.format(field.name, field.bit_width) for field in self)) if self.fields else ''
        return '<Reg {self.name} ({self.description}) @0x{self.address_offset:0{width}x} {access} {fields}>'.format(
                self=self,
                width=self.size//4,
                access=access,
                fields=fields)

class RegisterArray(Register):
    """Represent a register array in the tree"""

    def __init__(self, name, dim_indices, **kwargs):
        super().__init__(name=name.replace('%s', ''), **kwargs)

        self.registers = {}
        for idx, offx in zip(dim_indices, count(self.address_offset, self.dim_increment)):
            reg = Register(name=name.replace('%s', str(idx)), is_array=True, parent=self, address_offset=offx, **kwargs)
            reg._xml_fields = ['name', 'address_offset']
            self.registers[idx] = reg

class AddressBlock(Element):
    def __repr__(self):
        return '<Address block: {self.size} bytes @{self.offset:0{width}x}>'.format(self=self, width=self.parent.size//4)

class Interrupt(Element):
    def __repr__(self):
        return '<Interrupt {self.name} (IRQn {self.value})>'.format(self=self)

class Peripheral(Element):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interrupts = {}
        self.address_blocks = {}
        self.registers = {}

    def _register_element(self, elem):
        super()._register_element(elem)
        {Interrupt:     self.interrupts,
         Register:      self.registers,
         AddressBlock:  self.address_blocks}[type(elem)][elem.name] = elem

    def __iter__(self):
        return iter(self.registers.values())

    def __repr__(self):
        return '<{name} peripheral @0x{addr:0{width}x}>'.format(name=self.name, addr=self.base_address, width=self.size//4)

class Cpu(Element):
    pass

class Device(Element):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.peripherals = self._elements

    def __repr__(self):
        return '<Device: {} ({}-bit), {} peripherals>'.format(self.name, self.size, len(self.peripherals))

