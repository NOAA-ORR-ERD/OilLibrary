# OilLibrary #

**OilLibrary** is The NOAA library of oils and their properties.
It is developed by the National Oceanic and Atmospheric Administration (**NOAA**),
Office of Response and Restoration (**ORR**), Emergency Response Division.


## Installation Instructions ##

- cd <directory containing this file>

- $venv/bin/python setup.py develop

or

- $venv/bin/python setup.py install


## Using the package ##

The simplest way of using the oil library is through the functions
get_oil() and get_oil_props():

```
> ipython
Python 2.7.11 |Anaconda 2.4.1 (x86_64)| (default, Dec  6 2015, 18:57:58) 
Type "copyright", "credits" or "license" for more information.

In [1]: from oil_library import get_oil

In [2]: oil_obj = get_oil('BAHIA')

In [3]: oil_obj
Out[3]: <Oil("BAHIA")>

```

However, the underlying mechanism of the oil library is a SQL database using
SQLAlchemy.  So one can do more sophisticated things like:

```
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
```

