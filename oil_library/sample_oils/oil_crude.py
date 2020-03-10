'''
    The oil properties for the sample oil named oil_crude
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

json_data = {'name': 'oil_crude',
             'api': uc.convert('Density',
                               'gram per cubic centimeter',
                               'API degree', 0.90),
             'pour_point_min_k': 245.0,
             'k0y': 0.000002024,
             'kvis': [{'m_2_s': 0.0005, 'ref_temp_k': 273.0},
                      {'m_2_s': 0.0006, 'ref_temp_k': 288.0},
                      {'m_2_s': 8.3e-5, 'ref_temp_k': 293.0},
                      {'m_2_s': 8.53e-5, 'ref_temp_k': 311.0}],
             }
