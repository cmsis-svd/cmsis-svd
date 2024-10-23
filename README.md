CMSIS-SVD Parsers
=================

[![CI Results](https://github.com/posborne/cmsis-svd/workflows/test/badge.svg)](https://github.com/posborne/cmsis-svd/actions)

This repository seeks to provide value to developers targeting ARM
platforms.
It provides parsers that make code generation and tooling based on SVD
easier to build. Most parsers simply parse a provided SVD file and
turn it into a data structure more easily used in that language.

- [Python Package](https://github.com/cmsis-svd/cmsis-svd)

What is CMSIS-SVD
-----------------

ARM provides the following description of
[CMSIS-SVD (System View Description)](https://open-cmsis-pack.github.io/svd-spec/main/index.html)

> The CMSIS System View Description format(CMSIS-SVD) formalizes the
> description of the system contained in ARM Cortex-M processor-based
> microcontrollers, in particular, the memory-mapped registers of
> peripherals. The detail contained in system view descriptions is
> comparable to the data in device reference manuals. The information
> ranges from high-level functional descriptions of a peripheral all the
> way down to the definition and purpose of an individual bit field in a
> memory-mapped register.

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

Please feel free to create an issue on Github and/or submit Pull Requests with
proposed changes to the repository. These will be reviewed and pulled in if
deemed appropriate.

License
-------

All the code is licensed under the terms of the Apache License v2.0
(See [LICENSE-APACHE](LICENSE-APACHE)).

If you encounter an issue with the content of this repository or have
a question, please do not hesitate to create an issue on Github.
