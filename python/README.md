Python CMSIS SVD Parser
=======================

This directory contains the code for a CMSIS SVD parser in Python.
The parser is able to read in an input SVD and provide Python objects
containing the information from the SVD.  This frees the developer
(you) from having to worry about the SVD XML and each vendor's little
quirks.

Install It
----------

You can install the latest stable version from pypi:

```sh
pip install -U cmsis-svd
```

To install the latest development version by doing.  If this fails,
you may need to update the version of pip you are using.

```sh
pip install -U -e 'git+https://github.com/posborne/cmsis-svd.git#egg=cmsis-svd&subdirectory=python'
````

Example
-------

There's a lot of information you can glean from the SVDs for various
platforms.  Let's say, for instance, that I wanted to see the names
and base address of each peripheral on the Freescale K20 (D7).  Since the
K20 SVD is packaged with the library, I can do the following:

```python
from cmsis_svd.parser import SVDParser

parser = SVDParser.for_packaged_svd('Freescale', 'MK20D7.xml')
for peripheral in parser.get_device().peripherals:
    print("%s @ 0x%08x" % (peripheral.name, peripheral.base_address))
```

This generates the following output:

```
FTFL_FlashConfig @ 0x00000400
AIPS0 @ 0x40000000
AIPS1 @ 0x40080000
AXBS @ 0x40004000
DMA @ 0x40008000
FB @ 0x4000c000
FMC @ 0x4001f000
FTFL @ 0x40020000
DMAMUX @ 0x40021000
CAN0 @ 0x40024000
SPI0 @ 0x4002c000
SPI1 @ 0x4002d000
...
```

Example 2: Convert to JSON
--------------------------

The data structures representing the SVD data have the ability to
convert themselves to a dictionary suitable for serialization as
JSON.  This works recursively.  To generate JSON data and pretty print
it you can do something like the following:

```python
from cmsis_svd.parser import SVDParser

parser = SVDParser.for_packaged_svd('Freescale', 'MK20D7.xml')
svd_dict = parser.get_device().to_dict()
print(json.dumps(svd_dict, sort_key=True,
                 indent=4, separators=(',', ': ')))
```

Development
-----------

Once you have the code checked out, you can run the following from
this directory to install dependencies:

```sh
virtualenv env
source env/bin/activate
pip install -r dev-requirements.txt
```

Then, to run the tests:

```sh
nosetests .
```

There are quite a few SVD files, so the tests take a bit.  If you have
some extra CPUs to throw at the problem, you can do the following:

```sh
nosetes --process=8 .
```

Where `8` can be replaced with as many processes as you see fit.
Generally, 2x the number of processors in your machine is a good
starting place.

Contributing
------------

Please open issues and submit pull requests on Github.
