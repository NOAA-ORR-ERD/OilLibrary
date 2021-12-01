##########
OilLibrary
##########

**NOTE:**
=========

This OilLibrary Package is not longer under development. If a simple bug like this one crops up, we'll try to fix it, but it won't see any further development.

Our development efforts are now focused on a new system -- in teh end, similar functionality, but new structure.

The data itself is available via an online database:

https://adios.orr.noaa.gov

(note: we will be publishing the raw data in JSON format on gitHub soon)

The code to process the data is in the ``adios_db`` package in the adios_oil_database project:

https://github.com/NOAA-ORR-ERD/adios_oil_database

And some of the computation specific to the oil weathering in now in PyGNOME:

https://github.com/NOAA-ORR-ERD/PyGnome

If you need oil-processing functionality outside of PyGNOME, let us know, we may be able to move some code around.

Overview
========


**OilLibrary** is The NOAA library of oils and their properties.
It is developed by the National Oceanic and Atmospheric Administration (**NOAA**),
Office of Response and Restoration (**ORR**), Emergency Response Division.


Installation Instructions
=========================

Requirements
------------

The best way to get the requirements is via conda::

  conda install --file conda_requirements.txt

Note that some of the packages are only available in conda-forge channels.

To make it easy for your install to find the conda-forge packages, it should be added to your conda configuration:

    > conda config --add channels conda-forge

When you add a channel to conda, it puts it at the top of the list.
So now when you install a package, conda will first look in conda-forge,
and then in the default channel.
This order should work well for PyGNOME.

Be sure to add the channels in the order we specify.

You can see what channels you have with::

    > conda config --get channels

It should return something like this::

    --add channels 'defaults'   # lowest priority
    --add channels 'conda-forge'   # highest priority

In that order -- the order is important


Installing from source
----------------------

Activate the environment::

  conda activate gnome

::

  cd <directory containing this file>

Install the dependencies::

  conda install --file conda_requirements.txt


Build / intall the pacakge::

  python setup.py develop

or::

  python setup.py install

NOTE: if anything goes wrong, or you've updated the source, you will want to clean out the old installation::

  python setup.py cleanall


Using the package
=================

The simplest way of using the oil library is through the functions
get_oil() and get_oil_props()::

    > ipython
    Python 2.7.11 |Anaconda 2.4.1 (x86_64)| (default, Dec  6 2015, 18:57:58)
    Type "copyright", "credits" or "license" for more information.

    In [1]: from oil_library import get_oil

    In [2]: oil_obj = get_oil('BAHIA')

    In [3]: oil_obj
    Out[3]: <Oil("BAHIA")>


However, the underlying mechanism of the oil library is a SQL database using
SQLAlchemy.  So one can do more sophisticated things like::

    > ipython
    Python 2.7.11 |Anaconda 2.4.1 (x86_64)| (default, Dec  6 2015, 18:57:58)
    Type "copyright", "credits" or "license" for more information.

    In [1]: from oil_library import get_oil, get_oil_props, _get_db_session

    In [2]: from oil_library.models import Oil

    In [3]: session = _get_db_session()

    In [4]: session.query(Oil.name).all()
    Out[4]:
    [(u'ABOOZAR, OIL & GAS'),
     (u'ABU SAFAH'),
     (u'ALASKA NORTH SLOPE (MIDDLE PIPELINE)'),
     ...
     ...
     (u'ZETA NORTH'),
     (u'ZUATA SWEET, OIL & GAS JOURNAL'),
     (u'ZUEITINA, OIL & GAS')]

    In [5]:

