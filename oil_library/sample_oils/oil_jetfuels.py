'''
    The oil properties for the sample oil named oil_gas
    (Note: we put these things in their own separate file because
           some oil properties records can get quite large)
'''
import unit_conversion as uc

json_data = {'name': 'oil_jetfuels',
             'api': uc.convert('Density',
                               'gram per cubic centimeter',
                               'API degree', 0.81),
             'pour_point_min_k': 225.0,
             'k0y': 0.000002024,
             'kvis': [{'m_2_s': 6.9e-6,
                       'ref_temp_k': 255.0},
                      {'m_2_s': 2.06e-6,
                       'ref_temp_k': 273.0},
                      {'m_2_s': 2.08e-6,
                       'ref_temp_k': 288.0},
                      {'m_2_s': 1.3e-6,
                       'ref_temp_k': 313.0}],
             }
