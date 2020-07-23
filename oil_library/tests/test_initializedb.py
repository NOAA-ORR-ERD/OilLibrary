"""
test of the full build of the database

really more of a integration test

"""

import pytest
pytestmark = pytest.mark.skip("skipping 'cause this messes up the DB")

from pathlib import Path

import oil_library
from oil_library import initializedb


test_file = str(Path(oil_library.__file__).parent / "OilLibTest")


def test_make_db():
    """
    one big ol' test -- all it does it make sure it doesn't fail

    It would be good to test more, but ...
    """
    initializedb.make_db(oillib_files=test_file,
                         db_file='TestOilLib.db',
                         blacklist_file=None)

    assert True


if __name__ == "__main__":
    test_make_db()

