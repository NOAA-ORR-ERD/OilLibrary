'''
Tests for oil_props module in gnome.db.oil_library
'''

import copy

import numpy as np

import pytest
from pytest import raises

import unit_conversion as uc

from .. import get_oil_props, get_oil

from sqlalchemy.orm.exc import NoResultFound


def test_OilProps_exceptions():
    with pytest.raises(NoResultFound):
        get_oil_props('test')


@pytest.mark.parametrize(("search", "isNone"),
                         [('LUCKENBACH FUEL OIL', False), (51, True)])
def test_get_oil(search, isNone):
    if isNone:
        with raises(NoResultFound):
            o = get_oil(search)
    else:
        o = get_oil(search)
        if isinstance(search, str):
            assert o.name == search


@pytest.mark.parametrize(("adios_id", "name"),
                         [("AD00051", "ARABIAN LIGHT"),
                          (" ad00051   ", "ARABIAN LIGHT"),
                          ("A02434", None),
                          ("Jibberish", None),
                          ])
def test_get_oil_id(adios_id, name):
    if name is None:  # shouldn't be found
        with raises(NoResultFound):
            o = get_oil(adios_id)
    else:
        o = get_oil(adios_id)

        assert o.name == name
        assert o.adios_oil_id == adios_id.strip().upper()


# Record number 51: "AUTOMOTIVE GASOLINE, EXXON" is found in database
# but mass fractions do not sum up to one so valid OilProps object not created.
# In this case return None
@pytest.mark.parametrize(("search", "isNone"),
                         [('LUCKENBACH FUEL OIL', False), (51, True)])
def test_get_oil_props(search, isNone):
    if isNone:
        with raises(NoResultFound):
            op = get_oil_props(search)
    else:
        op = get_oil_props(search)

        assert op is not None


# just double check values for _sample_oil are entered correctly
oil_density_units = [
    ('oil_gas', 0.75065, 'g/cm^3'),
    ('oil_jetfuels', 0.8107, 'g/cm^3'),
    ('oil_4', 0.90078, 'g/cm^3'),
    ('oil_crude', 0.90078, 'g/cm^3'),
    ('oil_6', 0.99086, 'g/cm^3'),
    ]


@pytest.mark.parametrize(('oil', 'density', 'units'), oil_density_units)
def test_OilProps_sample_oil(oil, density, units):
    """ compare expected values with values stored in OilProps - make sure
    data entered correctly and unit conversion is correct """

    o = get_oil_props(oil)
    d = uc.convert('density', units, 'kg/m^3', density)

    assert o.name == oil
    assert np.isclose(o.density_at_temp(273.15 + 15), d)
    # assert abs(o.get_density() - d) < 1e-3


@pytest.mark.parametrize(('oil', 'api'), [('LUCKENBACH FUEL OIL', 12.90)])
def test_OilProps_DBquery(oil, api):
    """ test dbquery worked for an example like FUEL OIL NO.6 """
    o = get_oil_props(oil)
    assert np.isclose(o.api, api, atol=0.01)


class TestProperties:
    def __init__ (self):
        self.op = get_oil_props('ALASKA NORTH SLOPE (MIDDLE PIPELINE, 1997)')

        self.s_comp = sorted(self.op.record.sara_fractions, key=lambda s: s.ref_temp_k)
        self.s_dens = sorted(self.op.record.sara_densities, key=lambda s: s.ref_temp_k)

        # only keep density records + sara_fractions which fraction > 0.
        # OilProps prunes SARA to keep data for fractions > 0.
        self.s_dens = [d_comp for ix, d_comp in enumerate(self.s_dens)
                if self.s_comp[ix].fraction > 0.]
        self.s_comp = [comp for comp in self.s_comp if comp.fraction > 0.]

    def test_num_components(self):
        assert self.op.num_components == len(self.s_comp)

    def test_sara(self):
        # boiling points
        assert np.all(self.op.boiling_point ==
                      [comp.ref_temp_k for comp in self.s_comp])

        # mass fraction
        assert np.all(self.op.mass_fraction ==
                      [comp.fraction for comp in self.s_comp])

        # sara type
        assert np.all(self.op._sara['type'] ==
                      [comp.sara_type for comp in self.s_comp])

        # density
        assert np.all(self.op.boiling_point ==
                      [comp.ref_temp_k for comp in self.s_dens])

        assert np.all(self.op.component_density ==
                      dens for dens in self.s_dens)

        assert np.allclose(self.op.mass_fraction.sum(), 1.0)


def test_eq():
    op = get_oil_props('ARABIAN MEDIUM, PHILLIPS')
    op1 = get_oil_props('ARABIAN MEDIUM, PHILLIPS')

    assert op == op1


def test_ne():
    assert (get_oil_props('ARABIAN MEDIUM, PHILLIPS') !=
            get_oil_props('ARABIAN MEDIUM, EXXON'))


class TestCopy():
    def test_copy(self):
        '''
        do a shallow copy and test that it is a shallow copy
        '''
        op = get_oil_props('ARABIAN MEDIUM, PHILLIPS')
        cop = copy.copy(op)
        assert op == cop
        assert op is not cop
        assert op.record is cop.record

        for item in op.__dict__:
            try:
                assert getattr(op, item) == getattr(cop, item)
            except ValueError:
                assert np.all(getattr(op, item) == getattr(cop, item))

            assert getattr(op, item) is getattr(cop, item)

    def test_deepcopy(self):
        '''
        do a shallow copy and test that it is a shallow copy
        '''
        op = get_oil_props('ARABIAN MEDIUM, PHILLIPS')
        dcop = copy.deepcopy(op)

        assert op == dcop
        assert op is not dcop

        for item in op.__dict__:
            try:
                assert getattr(op, item) == getattr(dcop, item)
            except ValueError:
                assert np.all(getattr(op, item) == getattr(dcop, item))

            if item == 'record' or getattr(op, item) is None:
                assert getattr(op, item) is getattr(dcop, item)
            else:
                assert getattr(op, item) is not getattr(dcop, item)
