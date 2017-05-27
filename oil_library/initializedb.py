import os
import sys
import logging

import transaction
from sqlalchemy import engine_from_config

from .oil_library_parse import OilLibraryFile

from .models import DBSession, Base

from .init_imported_record import purge_old_records, add_oil_object
from .init_categories import process_categories
from .init_oil import process_oils

from zope.sqlalchemy import ZopeTransactionExtension

logger = logging.getLogger(__name__)


def initialize_sql(settings):
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    # Here, we configure our transaction manager to keep the session open
    # after a commit.
    # - This of course means that we need to manually close the session when
    #   we are done.
    DBSession.configure(extension=ZopeTransactionExtension())

    Base.metadata.create_all(engine)


def load_database(settings):
    with transaction.manager:
        session = DBSession()

        logger.info('Purging old records in database')
        imported_recs_purged, oil_recs_purged = purge_old_records(session)
        logger.info('finished!!!\n'
                    '    {0} imported records purged.\n'
                    '    {0} oil records purged.'
                    .format(imported_recs_purged, oil_recs_purged))

        for fn in settings['oillib.files'].split('\n'):
            logger.info('opening file: {0} ...'.format(fn))
            fd = OilLibraryFile(fn)
            logger.info('file version: {}'.format(fd.__version__))

            print('Adding new records to database')
            rowcount = 0
            for r in fd.readlines():
                if len(r) < 10:
                    logger.info('got record: {}'.format(r))

                r = [unicode(f, 'utf-8') if f is not None else f
                     for f in r]
                add_oil_object(session, fd.file_columns, r)

                if rowcount % 100 == 0:
                    sys.stderr.write('.')

                rowcount += 1

            print('finished!!!  {0} rows processed.'.format(rowcount))
            session.close()

        # we need to open a session for each record here because we want
        # the option of transactionally rolling back rejected records.
        # So we just pass the session class instead of an open session.
        process_oils(DBSession)

        session = DBSession()
        process_categories(session, settings)


def make_db(oillib_files=None, db_file=None, blacklist_file=None):
    '''
    Entry point for console_script installed by setup
    '''
    logging.basicConfig(level=logging.INFO)

    pck_loc = os.path.dirname(os.path.realpath(__file__))

    if not db_file:
        db_file = os.path.join(pck_loc, 'OilLib.db')

    if not oillib_files:
        oillib_files = '\n'.join([os.path.join(pck_loc, fn)
                                  for fn in ('OilLib',
                                             'OilLibTest',
                                             'OilLibNorway')])

    if not blacklist_file:
        blacklist_file = os.path.join(pck_loc, 'blacklist_whitelist.txt')

    sqlalchemy_url = 'sqlite:///{0}'.format(db_file)
    settings = {'sqlalchemy.url': sqlalchemy_url,
                'oillib.files': oillib_files,
                'blacklist.file': blacklist_file}
    try:
        initialize_sql(settings)
        load_database(settings)
    except:
        logger.info("FAILED TO CREATED OIL LIBRARY DATABASE \n")
        raise
