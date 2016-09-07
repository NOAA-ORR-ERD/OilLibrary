'''
    The oil properties for the sample oil named oil_gas
    (Note: we put these things in their own separate file because
           some oil properties records can get quite large)
'''
import unit_conversion as uc

json_data = {'name': 'oil_gas',
             'api': uc.convert('Density',
                               'gram per cubic centimeter',
                               'API degree', 0.75),
             'pour_point_min_k': 180.0,
             'k0y': 0.000002024,
             'kvis': [{'m_2_s': 1.32e-6, 'ref_temp_k': 273.15},
                      {'m_2_s': 9.98e-7, 'ref_temp_k': 288.15},
                      {'m_2_s': 8.6e-7, 'ref_temp_k': 311.0}],
             }
