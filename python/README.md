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
