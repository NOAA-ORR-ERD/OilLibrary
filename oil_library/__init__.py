from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import logging

from pkg_resources import get_distribution

from sqlalchemy import create_engine
from sqlalchemy.exc import UnboundExecutionError
from sqlalchemy.orm.exc import NoResultFound

from .models import DBSession

#import sample_oils

try:
    __version__ = get_distribution('oil_library').version
except Exception:
    __version__ = 'not_found'


#
# currently, the DB is created and located when package is installed
#
_oillib_path = os.path.dirname(__file__)
__module_folder__ = __file__.split(os.sep)[-2]
_db_file = 'OilLib.db'
_db_file_path = os.path.join(_oillib_path, _db_file)


def _get_db_session():
    'we can call this from scripts to access valid DBSession'
    # not sure we want to do it this way - but let's use for now
    session = DBSession()

    try:
        eng = session.get_bind()

        if eng.url.database.split(os.path.sep)[-2:] != [__module_folder__,
                                                        _db_file]:
            raise UnboundExecutionError

    except UnboundExecutionError:
        session.bind = create_engine('sqlite:///' + _db_file_path)

    return session


#_sample_oils = {}

log_levels = {"debug": logging.DEBUG,
              "info": logging.INFO,
              "warning": logging.WARNING,
              "error": logging.ERROR,
              "critical": logging.CRITICAL,
              }
logger_format = '%(levelname)s - %(module)8s - line:%(lineno)d - %(message)s'


# utility for setting up console logging
def initialize_console_log(level='debug'):
    '''
    Initializes the logger to simply log everything to the console (stdout)

    Likely what you want for scripting use

    :param level='debug': the level you want your log to show. options are,
                          in order of importance: "debug", "info", "warning",
                          "error", "critical"

    You will only get the logging messages at or above the level you set.

    '''

    level = log_levels[level.lower()]

    ver = sys.version_info
    # only call force for py 3.8 or greater
    if ver.major == 3 and ver.minor >= 8:
        logging.basicConfig(force=True,  # make sure this gets set up
                            stream=sys.stdout,
                            level=level,
                            format=logger_format)
    else:
        logging.basicConfig(stream=sys.stdout,
                            level=level,
                            format=logger_format)


def add_file_log(filename, level='info'):
    """
    sets up the logger to dump to a new, clean file

    in addition to wherever else it's going
    """
    level = log_levels[level.lower()]
    handler = logging.FileHandler(filename, mode='w', encoding=None, delay=0)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(logger_format))
    logging.getLogger('').addHandler(handler)


# Set default logging handler to avoid "No handler found" warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())


from .factory import get_oil, get_oil_props

#_sample_oils.update({k: get_oil(v, max_cuts=2)
#                     for k, v in sample_oils._sample_oils.iteritems()})
