"""
tests of importing a record

So we can test without doing the whole database

note that test_imported_record tests the Imported Record functionality,
but doesn't seem to test the importing process itself.
"""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pytest

from pathlib import Path

from oil_library.oil_library_parse import OilLibraryFile

data_dir = Path(__file__).resolve().parent / "sample_data"


@pytest.fixture
def olf():
    return OilLibraryFile(str(data_dir / "A00005_record.tsv"))


def test_load_file(olf):
    """
    this asserts that you can load a file at all

    loading the file checks the version number, so at least that works.
    """

    assert olf.__version__ == ['6', '2019-05-09', 'adios']


def test_load_record(olf):
    record = olf.readline()

    assert len(record) == olf.num_columns
    assert len(record) == 159
    # record should be only unicode or None
    for i, item in enumerate(record):
        if item is None:
            continue
        else:
            assert type(item) == type(u"") # with unicode_literals, the u isn't required, but


def test_file_columns(olf):
    cols = olf.file_columns

    assert len(cols) == olf.num_columns

    for item in cols:
        assert type(item) == type(u"")


def test_file_columns_lu(olf):
    cols_lu = olf.file_columns_lu

    # not sure how to thoroughly test this ....

    assert len(cols_lu) == olf.num_columns
    for col_num in cols_lu.values():
        assert col_num >= 0
        assert col_num <= olf.num_columns

    for col_name in cols_lu.keys():
        assert type(col_name) == type(u"")

    # just a couple -- maybe the order isn't fixed?
    assert cols_lu[u"Oil_Name"] == 0
    assert cols_lu[u"ADIOS_Oil_ID"] == 1


def test_api(olf):
    """
    make sure the API field is a number
    """

    cols_lu = olf.file_columns_lu
    record_0 = olf.readline()
    record_1 = olf.readline()

    API = record_0[cols_lu["API"]]
    print(cols_lu["API"])
    print(API)
    assert API is None

    API = record_1[cols_lu["API"]]
    print(cols_lu["API"])
    print(API)
    assert float(API) == 26.8  # for Alaska North slope -- change if sample data changes
