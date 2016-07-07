'''
    test the oil_library sample oils
'''
import numpy as np
from numbers import Number

import pytest

from oil_library import _sample_oils

oil_gas = _sample_oils['oil_gas']
oil_jetfuels = _sample_oils['oil_jetfuels']
oil_diesel = _sample_oils['oil_diesel']
oil__4 = _sample_oils['oil_4']
oil_crude = _sample_oils['oil_crude']
oil_6 = _sample_oils['oil_6']
benzene = _sample_oils['benzene']
# oil_conservative = _sample_oils['oil_conservative']
# chemical = _sample_oils['chemical']


@pytest.mark.parametrize(('oil', 'prop', 'value'),
                         [(oil_gas, 'name', 'oil_gas'),
                          (oil_gas, 'api', 57.0),
                          (oil_gas, 'pour_point_min_k', 180.0),
                          (benzene, 'api', 28.6),
                          (benzene, 'saturates_fraction', 0.0),
                          (benzene, 'aromatics_fraction', 1.0),
                          (benzene, 'resins_fraction', 0.0),
                          (benzene, 'asphaltenes_fraction', 0.0),
                          (benzene, 'pour_point_min_k', 278.68),
                          (benzene, 'flash_point_min_k', 262.1),
                          (benzene,
                           'oil_water_interfacial_tension_n_m', 0.035),
                          (benzene,
                           'oil_water_interfacial_tension_ref_temp_k', 293.15),
                          (benzene, 'solubility', 1.78),
                          ])
def test_property(oil, prop, value):
    '''
        Generalized test of direct oil properties
    '''
    if isinstance(getattr(oil, prop), Number):
        assert np.isclose(getattr(oil, prop), value, rtol=0.0001)
    else:
        assert getattr(oil, prop) == value


@pytest.mark.parametrize(('oil', 'prop', 'sub_prop', 'values'),
                         [
                          (oil_gas, 'kvis', 'm_2_s', [1.32e-6,
                                                      9.98e-7,
                                                      8.6e-7]),
                          (oil_gas, 'kvis', 'ref_temp_k', [273.15,
                                                           288.15,
                                                           311.0]),
                          (benzene, 'densities', 'kg_m_3', [886.30,
                                                            883.26,
                                                            880.37,
                                                            877.33,
                                                            874.29,
                                                            871.40,
                                                            868.36,
                                                            865.48,
                                                            862.43,
                                                            859.55,
                                                            856.51,
                                                            853.62,
                                                            850.58,
                                                            847.70,
                                                            844.65,
                                                            841.61,
                                                            838.73,
                                                            835.68,
                                                            832.80,
                                                            829.76,
                                                            826.87,
                                                            823.83,
                                                            820.95,
                                                            817.90,
                                                            814.86]),
                          (benzene, 'densities', 'ref_temp_k', [285.93,
                                                                288.71,
                                                                291.48,
                                                                294.26,
                                                                297.04,
                                                                299.82,
                                                                302.59,
                                                                305.37,
                                                                308.15,
                                                                310.93,
                                                                313.71,
                                                                316.48,
                                                                319.26,
                                                                322.04,
                                                                324.82,
                                                                327.59,
                                                                330.37,
                                                                333.15,
                                                                335.93,
                                                                338.71,
                                                                341.48,
                                                                344.26,
                                                                347.04,
                                                                349.82,
                                                                352.59]),
                          (benzene, 'kvis', 'm_2_s', [8.513e-07,
                                                      8.1688e-07,
                                                      7.8459e-07,
                                                      7.5536e-07,
                                                      7.357e-07,
                                                      7.2721e-07,
                                                      6.9999e-07,
                                                      6.7477e-07,
                                                      6.5180e-07,
                                                      6.2855e-07,
                                                      6.0758e-07,
                                                      5.8751e-07,
                                                      5.6858e-07,
                                                      5.5059e-07,
                                                      5.3257e-07,
                                                      5.1669e-07,
                                                      5.415e-07,
                                                      3.89e-07]),
                          (benzene, 'kvis', 'ref_temp_k', [283.15,
                                                           285.93,
                                                           288.71,
                                                           291.48,
                                                           293.15,
                                                           294.26,
                                                           297.04,
                                                           299.82,
                                                           302.59,
                                                           305.37,
                                                           308.15,
                                                           310.93,
                                                           313.71,
                                                           316.48,
                                                           319.26,
                                                           322.04,
                                                           323.15,
                                                           353.15]),
                          (benzene, 'cuts', 'liquid_temp_k', [353.05]),
                          (benzene, 'cuts', 'vapor_temp_k', [353.23]),
                          (benzene, 'cuts', 'fraction', [1.0]),
                          (benzene, 'molecular_weights', 'ref_temp_k',
                           [353.23]),
                          (benzene, 'molecular_weights', 'g_mol',
                           [225.146]),
                          (benzene, 'sara_densities', 'ref_temp_k', [353.23]),
                          (benzene, 'sara_densities', 'density', [814.0]),
                          (benzene, 'sara_fractions', 'ref_temp_k', [353.23]),
                          (benzene, 'sara_fractions', 'fraction', [1.0]),
                          ])
def test_sub_property(oil, prop, sub_prop, values):
    '''
        Generalized test of oil sub-properties.  These
        are objects that have a one-to-many relationship with the Oil
        object, and can be basically viewed as a list of items bound
        to one of the Oil object direct properties.
    '''
    for sp_obj, v in zip(getattr(oil, prop), values):
        if isinstance(getattr(sp_obj, sub_prop), Number):
            assert np.isclose(getattr(sp_obj, sub_prop), v, rtol=0.0001)
        else:
            assert getattr(sp_obj, sub_prop) == v
