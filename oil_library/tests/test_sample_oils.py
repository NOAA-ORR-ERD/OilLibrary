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
# oil_conservative = _sample_oils['oil_conservative']
# chemical = _sample_oils['chemical']


@pytest.mark.parametrize(('oil', 'prop', 'value'),
                         [(oil_gas, 'name', 'oil_gas'),
                          (oil_gas, 'api', 57.0),
                          (oil_gas, 'pour_point_min_k', 180.0),
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
