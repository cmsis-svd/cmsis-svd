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

from cmsis_svd.parser import SVDParser
import os
import unittest

THIS_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(THIS_DIR, "..", "..", "..", "data")


def make_svd_validator(svd_path):
    def verify_svd_validity():
        parser = SVDParser.for_xml_file(svd_path)
        device = parser.get_device()
        assert device is not None

    mcu = os.path.basename(svd_path).replace('.svd', '').replace('_svd', '').replace('.', '-').lower()
    vendor = os.path.split(os.path.dirname(svd_path))[-1].lower()
    verify_svd_validity.__name__ = "test_{vendor}_{mcu}".format(vendor=vendor, mcu=mcu)
    return verify_svd_validity


#
# Generate a test function for each SVD file that exists
#
for dirpath, _dirnames, filenames in os.walk(DATA_DIR):
    for filename in (f for f in filenames if f.endswith('.svd')):
        svd_path = os.path.join(dirpath, filename)
        test = make_svd_validator(svd_path)
        globals()[test.__name__] = test


class TestParserFreescale(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.svd_path = os.path.join(DATA_DIR, "Freescale", "MKL25Z4.svd")
        cls.json_path = os.path.join(THIS_DIR, "MKL25Z4.json")
        cls.parser = SVDParser.for_xml_file(cls.svd_path)
        cls.device = cls.parser.get_device()

    def _regenerate_json(self, d):
        # Call this on some changes and inspect the JSON manually to verify (updating by hand too painful)
        with open(self.json_path, "w") as f:
            json.dump(d, f, sort_keys=True, indent=4, separators=(',', ': '))

    def _get_json(self):
        with open(self.json_path) as f:
            return json.load(f)

    def test_to_dict(self):
        device = self.device
        d = device.to_dict()
        # self._regenerate_json(d)  # uncomment to regenerate (temporarily)
        self.assertDictEqual(d, self._get_json())

    def test_device_attributes(self):
        device = self.device
        self.assertEqual(device.vendor, "Freescale Semiconductor, Inc.")
        self.assertEqual(device.vendor_id, "Freescale")
        self.assertEqual(device.name, "MKL25Z4")
        self.assertEqual(device.version, "1.6")
        self.assertEqual(device.address_unit_bits, 8)
        self.assertEqual(device.width, 32)
        self.assertEqual(device.cpu.name, "CM0PLUS")
        self.assertEqual(device.cpu.revision, "r0p0")
        self.assertEqual(device.cpu.endian, "little")
        self.assertEqual(device.cpu.mpu_present, 0)
        self.assertEqual(device.cpu.fpu_present, 0)
        self.assertEqual(device.cpu.vtor_present, 1)
        self.assertEqual(device.cpu.nvic_prio_bits, 2)
        self.assertEqual(device.cpu.vendor_systick_config, 0)

    def test_peripherals_high_level(self):
        # Ensure we got all of them
        device = self.device
        self.assertEqual(list(sorted([p.name for p in device.peripherals])),
                         ['ADC0', 'CMP0', 'DAC0', 'DMA', 'DMAMUX0',
                          'FGPIOA', 'FGPIOB', 'FGPIOC', 'FGPIOD',
                          'FGPIOE', 'FTFA', 'FTFA_FlashConfig', 'GPIOA',
                          'GPIOB', 'GPIOC', 'GPIOD', 'GPIOE', 'I2C0',
                          'I2C1', 'LLWU', 'LPTMR0', 'MCG', 'MCM', 'MTB',
                          'MTBDWT', 'OSC0', 'PIT', 'PMC', 'PORTA', 'PORTB',
                          'PORTC', 'PORTD', 'PORTE', 'RCM', 'ROM', 'RTC',
                          'SIM', 'SMC', 'SPI0', 'SPI1','TPM0', 'TPM1',
                          'TPM2', 'TSI0', 'UART0', 'UART1', 'UART2', 'USB0'])

    def test_peripheral_details(self):
        device = self.device
        uart0 = [p for p in device.peripherals if p.name == "UART0"][0]
        self.assertEqual(uart0.name, "UART0")
        self.assertEqual(uart0.description, "Universal Asynchronous Receiver/Transmitter")
        self.assertEqual(uart0.prepend_to_name, "UART0_")
        self.assertEqual(uart0.base_address, 0x4006A000)

        # address block verification
        block = uart0.address_blocks[0]
        self.assertEqual(block.usage, 'registers')
        self.assertEqual(block.size, 0x0C)
        self.assertEqual(block.offset, 0)

        self.assertEqual(list(sorted([r.name for r in uart0.registers])),
                         ['BDH', 'BDL', 'C1', 'C2', 'C3', 'C4',
                          'C5', 'D', 'MA1', 'MA2', 'S1', 'S2'])
        self.assertEqual([(i.name, i.value) for i in uart0.interrupts], [('UART0', 12)])

    def test_peripheral_multiple_interrupts(self):
        device = self.device
        dma = [p for p in device.peripherals if p.name == "DMA"][0]
        self.assertEqual([(i.name, i.value) for i in dma.interrupts],
                         [('DMA0', 0),
                          ('DMA1', 1),
                          ('DMA2', 2),
                          ('DMA3', 3), ])

    def test_register_details(self):
        device = self.device
        uart0 = [p for p in device.peripherals if p.name == "UART0"][0]
        bdh = [r for r in uart0.registers if r.name == "BDH"][0]
        self.assertEqual(bdh.name, "BDH")
        self.assertEqual(bdh.description, "UART Baud Rate Register High")
        self.assertEqual(bdh.address_offset, 0)
        self.assertEqual(bdh.size, 8)
        self.assertEqual(bdh.reset_value, 0)
        self.assertEqual(bdh.reset_mask, 0xFF)
        self.assertEqual(bdh.access, "read-write")
        self.assertEqual(list(sorted([f.name for f in bdh.fields])),
                         ['LBKDIE', 'RXEDGIE', 'SBNS', 'SBR'])

    def test_register_dim_duplicate_single(self):
        device = self.device
        dmamux0 = [p for p in device.peripherals if p.name == "DMAMUX0"][0]
        ret = [r for r in dmamux0.registers if r.name.startswith("CHCFG")]
        self.assertEqual(len(ret), 4)
        self.assertEqual(ret[1].name, 'CHCFG1')

    def test_field_details(self):
        device = self.device
        uart0 = [p for p in device.peripherals if p.name == "UART0"][0]
        bdh = [r for r in uart0.registers if r.name == "BDH"][0]
        lbkdie = [f for f in bdh.fields if f.name == "LBKDIE"][0]
        self.assertEqual(lbkdie.name, "LBKDIE")
        self.assertEqual(lbkdie.description, "LIN Break Detect Interrupt Enable (for LBKDIF)")
        self.assertEqual(lbkdie.bit_offset, 7)
        self.assertEqual(lbkdie.bit_width, 1)
        self.assertEqual(lbkdie.access, "read-write")
        self.assertTrue(lbkdie.is_enumerated_type)

        enumerated_values = list(sorted([(e.name, e.description, e.value) for e in lbkdie.enumerated_values]))
        self.assertEqual(enumerated_values, [
            ('0', 'Hardware interrupts from UART _S2[LBKDIF] disabled (use polling).', 0),
            ('1', 'Hardware interrupt requested when UART _S2[LBKDIF] flag is 1.', 1)
        ])


class TestParserNordic(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        svd = os.path.join(DATA_DIR, "Nordic", "nrf51.svd")
        cls.parser = SVDParser.for_xml_file(svd)
        cls.device = cls.parser.get_device()

    def test_missing_attribute(self):
        device = self.device
        self.assertRaises(AttributeError, lambda: device.dim)

    def test_device_attributes(self):
        device = self.device
        self.assertEqual(device.vendor, "Nordic Semiconductor")
        self.assertEqual(device.vendor_id, "Nordic")
        self.assertEqual(device.name, "nrf51")
        self.assertEqual(device.version, "522")
        self.assertEqual(device.address_unit_bits, 8)
        self.assertEqual(device.width, 32)
        self.assertEqual(device.size, 32)
        self.assertEqual(device.cpu.name, "CM0")
        self.assertEqual(device.cpu.revision, "r3p1")
        self.assertEqual(device.cpu.endian, "little")
        self.assertEqual(device.cpu.mpu_present, 0)
        self.assertEqual(device.cpu.fpu_present, 0)
        self.assertEqual(device.cpu.nvic_prio_bits, 2)
        self.assertEqual(device.cpu.vendor_systick_config, 0)

    def test_peripherals_high_level(self):
        # Ensure we got all of them
        device = self.device
        self.assertEqual(list(sorted([p.name for p in device.peripherals])),
                         ['AAR', 'ADC', 'CCM', 'CLOCK', 'ECB', 'FICR', 'GPIO', 'GPIOTE', 'LPCOMP', 'MPU',
                          'NVMC', 'POWER', 'PPI', 'QDEC', 'RADIO', 'RNG', 'RTC0', 'RTC1', 'SPI0', 'SPI1',
                          'SPIS1','SWI', 'TEMP', 'TIMER0', 'TIMER1', 'TIMER2', 'TWI0', 'TWI1', 'UART0', 'UICR',
                          'WDT'
                          ])

    def test_peripheral_details(self):
        device = self.device
        spi1 = [p for p in device.peripherals if p.name == "SPI1"][0]
        self.assertEqual(spi1.name, "SPI1")
        self.assertEqual(spi1.description, "SPI master 1.")
        self.assertEqual(spi1.base_address, 0x40004000)

        # address block verification
        block = spi1.address_blocks[0]
        self.assertEqual(block.usage, 'registers')
        self.assertEqual(block.size, 0x1000)
        self.assertEqual(block.offset, 0)

        self.assertEqual(list(sorted([r.name for r in spi1.registers])),
                         ['CONFIG', 'ENABLE', 'EVENTS_READY', 'FREQUENCY', 'INTENCLR', 'INTENSET',
                          'POWER', 'PSELMISO', 'PSELMOSI', 'PSELSCK', 'RXD', 'TXD'
                          ])
        self.assertEqual([(i.name, i.value) for i in spi1.interrupts], [('SPI1_TWI1', 4)])

    def test_peripheral_multiple_interrupts(self):
        device = self.device
        swi = [p for p in device.peripherals if p.name == "SWI"][0]
        self.assertEqual([(i.name, i.value) for i in swi.interrupts],
                         [('SWI0', 20),
                          ('SWI1', 21),
                          ('SWI2', 22),
                          ('SWI3', 23),
                          ('SWI4', 24),
                          ('SWI5', 25), ])

    def test_register_details(self):
        device = self.device
        spi1 = [p for p in device.peripherals if p.name == "SPI1"][0]
        intenset = [r for r in spi1.registers if r.name == "INTENSET"][0]
        self.assertEqual(intenset.name, "INTENSET")
        self.assertEqual(intenset.description, "Interrupt enable set register.")
        self.assertEqual(intenset.address_offset, 0x304)
        self.assertEqual(intenset.size, 32)
        self.assertEqual(intenset.reset_value, 0)
        self.assertEqual(intenset.reset_mask, 0xFFFFFFFF)
        self.assertEqual(intenset.access, "read-write")
        self.assertEqual(list(sorted([f.name for f in intenset.fields])),
                         ['READY'])

    def test_register_arrays(self):
        radio = [p for p in self.device.peripherals if p.name == "RADIO"][0]
        self.assertEqual([(r.name, r.dim, list(r.dim_indices), r.dim_increment)
                          for r in radio.register_arrays],
                         [('DAB[%s]', 8, [0, 1, 2, 3, 4, 5, 6, 7], 4),
                          ('DAP[%s]', 8, [0, 1, 2, 3, 4, 5, 6, 7], 4)])

    def test_register_cluster_array(self):
        ppi = [p for p in self.device.peripherals if p.name == "PPI"][0]
        regs = list(ppi.registers)
        register_names = [r.name for r in regs]
        self.assertIn("CH[0]_EEP", register_names)
        self.assertIn("CH[0]_TEP", register_names)
        self.assertIn("CH[15]_EEP", register_names)
        self.assertIn("CH[15]_TEP", register_names)
        reg = [r for r in regs if r.name == "CH[15]_TEP"][0]
        self.assertEqual(reg.address_offset, 0x58C)

class TestParserSpansion(unittest.TestCase):
    def test_derived_register_attributes(self):
        parser = SVDParser.for_packaged_svd('Spansion', 'MB9BF46xx.svd')
        mft0_regs = [p.registers for p in parser.get_device().peripherals if p.name == "MFT0"][0]
        reg_map = {r.name: r for r in mft0_regs}

        # Test to see if the derived register has the attributes of the base register
        base_reg = reg_map['FRT_TCCP0']
        derived_reg = reg_map['FRT_TCCP1']

        self.assertEqual(derived_reg.size, base_reg.size)
        self.assertEqual(derived_reg.access, base_reg.access)
        self.assertEqual(derived_reg.reset_value, base_reg.reset_value)
        self.assertEqual(derived_reg.reset_mask, base_reg.reset_mask)

class TestParserExample(unittest.TestCase):
    def test_derived_from_registers(self):
        parser = SVDParser.for_packaged_svd('ARM_SAMPLE', 'ARM_Sample.svd')
        regs = {p.name: p.registers for p in parser.get_device().peripherals}
        self.assertEqual(len(regs["TIMER0"]), len(regs["TIMER1"]))
        self.assertEqual(len(regs["TIMER0"]), len(regs["TIMER2"]))
        self.assertEqual(len(regs["TIMER1"]), len(regs["TIMER2"]))

    def test_derived_from_peripheral_attributes(self):
        parser = SVDParser.for_packaged_svd("ARM_SAMPLE", "ARM_Sample.svd")
        timer0 = parser.get_device().peripherals[0]
        timer1 = parser.get_device().peripherals[1]

        # Check if we have selected the correct peripherals
        self.assertEqual(timer0.name, "TIMER0")
        self.assertEqual(timer1.name, "TIMER1")

        # Check the derived attributes
        self.assertEqual(timer0.version, timer1.version)
        self.assertEqual(timer0.description, timer1.description)
        self.assertEqual(timer0.prepend_to_name, timer1.prepend_to_name)
        self.assertEqual(timer0.append_to_name, timer1.append_to_name)
        self.assertEqual(timer0.disable_condition, timer1.disable_condition)
        self.assertEqual(timer0.group_name, timer1.group_name)
        self.assertNotEqual(timer0.base_address, timer1.base_address)
        self.assertEqual(timer0.size, timer1.size)
        self.assertEqual(timer0.access, timer1.access)
        self.assertEqual(timer0.address_blocks[0].offset, timer1.address_blocks[0].offset)
        self.assertEqual(timer0.address_blocks[0].size, timer1.address_blocks[0].size)
        self.assertEqual(timer0.address_blocks[0].usage, timer1.address_blocks[0].usage)
        self.assertEqual(timer0.protection, timer1.protection)
        self.assertEqual(timer0.reset_value, timer1.reset_value)
        self.assertEqual(timer0.reset_mask, timer1.reset_mask)

class TestParserPackagedData(unittest.TestCase):
    def test_packaged_xml(self):
        parser = SVDParser.for_packaged_svd('Freescale', 'MK20D7.svd')
        device = parser.get_device()
        self.assertTrue(len(device.peripherals) > 0)

    def test_packaged_xml_for_mcu(self):
        parser = SVDParser.for_mcu('STM32F103C8T6')
        self.assertTrue(parser is not None)
        device = parser.get_device()
        self.assertTrue(len(device.peripherals) > 0)
