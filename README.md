CMSIS-SVD Repository and Parsers
================================

[![CI Results](https://github.com/posborne/cmsis-svd/workflows/test/badge.svg)](https://github.com/posborne/cmsis-svd/actions)

What is this?
-------------

This repository seeks to provide value to developers targetting ARM
platforms in two main ways:

1. Provide a convenient place to access and aggregate CMSIS-SVD
   hardware descriptions from multiple sources.
2. Provide parsers that make code generation and tooling based on SVD
   easier to build.  Most parsers simply parse a provided SVD file and
   turn it into a data structure more easily used in that language.

What is CMSIS-SVD
-----------------

ARM provides the following description of
[CMSIS-SVD (System View Description)](http://www.keil.com/pack/doc/CMSIS/SVD/html/index.html)

> The CMSIS System View Description format(CMSIS-SVD) formalizes the
> description of the system contained in ARM Cortex-M processor-based
> microcontrollers, in particular, the memory-mapped registers of
> peripherals. The detail contained in system view descriptions is
> comparable to the data in device reference manuals. The information
> ranges from high-level functional descriptions of a peripheral all the
> way down to the definition and purpose of an individual bit field in a
> memory-mapped register.

The original vision of ARM appears to have been to aggregate SVDs from
various sources into a single repository accessible via
[ARM's CMSIS Website](http://www.arm.com/products/processors/cortex-m/cortex-microcontroller-software-interface-standard.php).
Currently, however, this site fails to provide a comprehensive
repository of CMSIS SVDs.  The SVDs in this repository have been
previously aggregated as part of the Eclipse
[Embedded Systems Register View](http://embsysregview.sourceforge.net/)
plugin.  This repo builds on the shoulders of the developers of
EmbSysRegView and seeks to provide a repository of SVDs that is more
accessible to a greater number of other projects.

How Can the CMSIS-SVD Be Used
-----------------------------

The generic description of each MCUs CPU and hardware registers is
very valuable when generating code that can be used for talking to
specific target hardware.  In fact, much of the code in parts of CMSIS
itself are generated based on the SVD.  ARM distributes an executable
that does this transformation (SVDConvert.exe).

The information can also be used for building debug tooling, test
infrastructure, or whatever else.

Contributing
------------

Contributions from Silicon Vendors, as well as community members, are
greatly appreciated.  Please feel free to create an issue on Github
and/or submit Pull Requests with proposed changes to the repository.
These will be reviewed and pulled in if deemed appropriate.

License
-------

The licensing for the contents of this repository is dependent on the
directory in which files are located as well as the contents of the
files themselves.  If in doubt, the first parent directory of a file
having license information is the license that applies.  In all cases,
if the file itself has a license specified, that applies.

In general, the following rules apply:

* Under data, the license from each Vendor is provided along with the
  SVDs from that vendor.  Please review this license before use of the
  SVDs contained therein.  Look for files named the following for
  license information:
* All other code is licensed under the terms of the Apache License
  v2.0 (See [LICENSE-APACHE](LICENSE-APACHE)).

If you encounter an issue with the content of this repository or have
a question, please do not hesitate to create an issue on Github.
