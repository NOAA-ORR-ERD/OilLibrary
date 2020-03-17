#!/usr/bin/env python

"""
test code for the catagorization process

largely put here toso I can re-factor it safely

NOTE: This isn't testing the initilization of teh DB,
etc, as I'm not sure how to test that wihtout messing
with the actual DB -- but it should
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil
import pytest

from sqlalchemy import engine_from_config
from zope.sqlalchemy import ZopeTransactionExtension

import oil_library
from oil_library.models import DBSession
from oil_library.models import Oil, Category

from oil_library.init_categories import (list_categories,
                                         clear_categories,
                                         )


@pytest.fixture(scope="module")
def session():
    """
    makes a copy of the oil database, and creates a session object to it

    When done, closes the session and deletes the DB file

    This is kind kludgy, but hopefully works
    """

    orig = os.path.join(os.path.split(oil_library.__file__)[0], "OilLib.db")
    # NOTE: this should probably be in a temp dir...
    db_file = "./OilLibCopy.db"
    # make a copy:
    shutil.copy(orig, db_file)

    settings = {"sqlalchemy.url": 'sqlite:///{0}'.format(db_file)}
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    DBSession.configure(extension=ZopeTransactionExtension())

    yield DBSession

    DBSession.close()
    os.remove(db_file)


def test_list_categories(session):
    q = session.query(Category).filter(Category.parent == None)
    all_cats = {category.name: tuple(list_categories(category)) for category in q}

    print(all)

    assert list(all_cats.keys()) == [u'Crude', u'Refined', u'Other']
    # maybe test more here at some point...


def test_clear_categories(session):
    """
    makes sure clearing teh catagories works
    """
    clear_categories(session)

    q = session.query(Category).filter(Category.parent == None)

    assert len(tuple(q)) == 0




