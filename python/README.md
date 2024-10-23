# Python CMSIS-SVD

This directory contains the code for a CMSIS SVD Python parser and serializers.
The parser is able to read in an input SVD and provide a Python data structures
containing the information from the SVD.  This frees the developer
(you) from having to worry about the SVD XML and each vendor's little
quirks. The serializers are able to dump the CMSIS SVD Python data structures to
the SVD XML file format or to the JSON format.

## Install

You can install the latest stable version from pypi:

```text
pip install -U cmsis-svd
```

To install the latest development version by doing.

```text
pip install -U -e 'git+https://github.com/cmsis-svd/cmsis-svd.git#egg=cmsis-svd&subdirectory=python'
```

If this fails, you may need to update the version of pip you are using.

## Note: Changes from Version 0.4

For a very long period of time (2016-2023), the pypi package for cmsis-svd was out
of data and included a large number of "bundled" SVD files.  This has only grown and
with the 0.5 release, those are no longer included as part of the python
distributable.  Other means of providing access to the SVD definitions may be
revisited in the future.


## Download CMSIS-SVD Files from the cmsis-svd Project

The cmsis-svd project provides an aggregation of CMSIS-SVD files collected from
silicon vendors in the [cmsis-svd-data](https://github.com/cmsis-svd/cmsis-svd-data)
git repository. The next examples use CMSIS-SVD files from the CMSIS SVD data
repository to illustrate usages of the cmsis-svd Python package. Clone the
CMSIS SVD data repository to follow the next examples.

```text
git clone --depth=1 -b main https://github.com/cmsis-svd/cmsis-svd-data.git
```


## Usage

There's a lot of information you can glean from the SVDs for various
platforms. Let's say, for instance, that I wanted to parse and create a CMSIS
SVD Python data structure for the Atmel SAM9CN11. Since the SAM9CN11 SVD is
packaged in the CMSIS SVD data repository, I can do the following:

```pycon
>>> SVD_DATA_DIR = "cmsis-svd-data/data"
>>>
>>> from cmsis_svd import SVDParser
>>> parser = SVDParser.for_packaged_svd(SVD_DATA_DIR, 'Atmel', 'AT91SAM9CN11.svd')
>>> SAM9CN11_device = parser.get_device()
>>> type(SAM9CN11_device)
<class 'cmsis_svd.model.SVDDevice'>
```

Alternatively, It is possible to validate the SAM9CN11 SVD XML file before
parsing, specifying the `xml_validation` boolean flag to `get_device()`. In this
case the `SVDParser` try to retrieve the XML schema version used by the file via
the `schemaVersion` attribute of the `device` xml tag, otherwise if not found the
last SVD XML schema version is used. Moreover, the validation step can be
tailored to feet your need via the `schema_version` and
`schema_version_detection` parameters, see the doc `help(SVDParser.get_device)`.

```pycon
>>> SAM9CN11_device = parser.get_device(xml_validation=True)
```

Below, an example to retrieve the names and base address of each peripheral for
the Atmel SAM9CN11.

```pycon
>>> for peripheral in SAM9CN11_device.get_peripherals():
...     print("%s @ 0x%08x" % (peripheral.name, peripheral.base_address))
...
SPI0 @ 0xf0000000
SPI1 @ 0xf0004000
HSMCI @ 0xf0008000
AES @ 0xf000c000
...
```

The Python data structures representing the SVD data provides a XML serializer
via the `to_xml()` method:

```pycon
>>> print(SAM9CN11_device.to_xml())
<?xml version='1.0' encoding='utf-8'?>
<device xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xs:noNamespaceSchemaLocation="CMSIS-SVD_Schema_1_1.xsd" schemaVersion="1.1">
  <vendor>Atmel</vendor>
  <name>AT91SAM9CN11</name>
  <series>SAM9CN</series>
  <version>20130208</version>
...
```

In addition, It is possible to produce an `lxml` element to customise the
XML tree directly via the `to_xml_node()` method:

```pycon
>>> device_element = SAM9CN11_device.to_xml_node()
>>> type(device_element)
<class 'lxml.etree._Element'>
>>> device_element.tag
'device'
>>> device_element.find('name').text
'AT91SAM9CN11'
```

The Python data structures representing the SVD data provides a JSON serializer
via the `to_json()` method:

```pycon
>>> print(SAM9CN11_device.to_json())
{
    "access": null,
    "address_unit_bits": 8,
    "cpu": null,
    "description": "Atmel AT91SAM9CN11 device: ARM926EJ Embedded Microprocessor Unit, 400MHz, Crypto engine, LCD, USB, LPDDR/DDR2/MLC NAND support, 217 Pins (refer to http://www.atmel.com/devices/SAM9CN11.aspx for more)",
    "header_definitions_prefix": null,
    "header_system_filename": null,
    "license_text": null,
    "name": "AT91SAM9CN11",
...
```

In addition, It is possible to produce a JSON serializable dictionary to
customise the dict directly via the `to_dict()` method:

```pycon
>>> device_dict = SAM9CN11_device.to_dict()
>>> type(device_dict)
<class 'dict'>
>>> device_dict['name']
'AT91SAM9CN11'
```

## Development

Once you have the code checked out, you can run the following command from
the `python` directory to install the `cmsis-svd` Python package in editable
mode with the development dependencies:

```text
cd cmsis-svd/python && pip install --editable .[DEV]
```

Then, to run the tests:

```text
cd cmsis-svd/
git clone --depth=1 https://github.com/cmsis-svd/cmsis-svd-data.git
cd python/
nose2
```

By default, tests will run in parallel according to the number of
processors available on the system.

## Contributing

Please open [issues](https://github.com/cmsis-svd/cmsis-svd/issues) and submit [pull requests](https://github.com/cmsis-svd/cmsis-svd/pulls) on Github.
