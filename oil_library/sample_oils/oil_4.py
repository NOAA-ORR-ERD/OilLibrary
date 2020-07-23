'''
    The oil properties for the sample oil named oil_4
    (Note: we put these things in their own separate file because
           some oil properties records can get quite large)
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
import unit_conversion as uc

json_data = {'name': 'oil_4',
             'api': uc.convert('Density',
                               'gram per cubic centimeter',
                               'API degree', 0.90),
             'pour_point_min_k': 328.0,
             'k0y': 0.000002024,
             'kvis': [{'m_2_s': 0.06, 'ref_temp_k': 273.0},
                      {'m_2_s': 0.03, 'ref_temp_k': 278.0},
                      {'m_2_s': 0.0175, 'ref_temp_k': 283.0},
                      {'m_2_s': 0.0057, 'ref_temp_k': 288.0}],
             }
