
from oil_library.models import Density

from ec_xl_parse import (get_oil_properties_by_name,
                         get_oil_properties_by_category)
from ec_oil_props import get_oil_weathering


def get_oil_densities(oil_columns, field_indexes):
    '''
        Getting densities out of this datasheet is more tricky than it should
        be.  There are two categories, density at 15C, and density at 0/5C.
        I dunno, I would have organized the data in a more orthogonal way.
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    densities_at_0c = get_oil_densities_at_0c(oil_columns,
                                              field_indexes,
                                              weathering)
    densities_at_5c = get_oil_densities_at_5c(oil_columns,
                                              field_indexes,
                                              weathering)
    densities_at_15c = get_oil_densities_at_15c(oil_columns,
                                                field_indexes,
                                                weathering)

    return densities_at_0c + densities_at_5c + densities_at_15c


def get_oil_densities_at_15c(oil_columns, field_indexes, weathering):
    densities = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'density_at_15_c_g_ml_astm_d5002')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        density_obj = dict(list(zip(prop_names, [v[0].value for v in vals])))

        # add some properties to the oil that we expect
        density_obj['idx'] = idx
        density_obj['weathering'] = weathering[idx]
        density_obj['ref_temp_k'] = 273.15 + 15.0

        density_obj['kg_m_3'] = density_obj['density_15_c_g_ml']
        if density_obj['kg_m_3'] is not None:
            density_obj['kg_m_3'] *= 1000.0

        # prune some properties that we don't want in our object
        del density_obj['density_15_c_g_ml']

        densities.append(density_obj)

    return [Density(**d) for d in densities
            if d['kg_m_3'] not in (None, 0.0)]


def get_oil_densities_at_0c(oil_columns, field_indexes, weathering):
    densities = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'density_at_0_5_c_g_ml_astm_d5002')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        density_obj = dict(list(zip(prop_names, [v[0].value for v in vals])))

        # add some properties to the oil that we expect
        density_obj['idx'] = idx
        density_obj['weathering'] = weathering[idx]
        density_obj['ref_temp_k'] = 273.15

        density_obj['kg_m_3'] = density_obj['density_0_c_g_ml']
        if density_obj['kg_m_3'] is not None:
            density_obj['kg_m_3'] *= 1000.0

        # prune some properties that we don't want in our object
        del density_obj['density_0_c_g_ml']
        del density_obj['density_5_c_g_ml']

        densities.append(density_obj)

    return [Density(**d) for d in densities
            if d['kg_m_3'] not in (None, 0.0)]


def get_oil_densities_at_5c(oil_columns, field_indexes, weathering):
    densities = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'density_at_0_5_c_g_ml_astm_d5002')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        density_obj = dict(list(zip(prop_names, [v[0].value for v in vals])))

        # add some properties to the oil that we expect
        density_obj['idx'] = idx
        density_obj['weathering'] = weathering[idx]
        density_obj['ref_temp_k'] = 273.15 + 5.0

        density_obj['kg_m_3'] = density_obj['density_5_c_g_ml']
        if density_obj['kg_m_3'] is not None:
            density_obj['kg_m_3'] *= 1000.0

        # prune some properties that we don't want in our object
        del density_obj['density_0_c_g_ml']
        del density_obj['density_5_c_g_ml']

        densities.append(density_obj)

    return [Density(**d) for d in densities
            if d['kg_m_3'] not in (None, 0.0)]


def get_oil_api(oil_columns, field_indexes):
    '''
        Get the oil API gravity.
    '''
    cells = get_oil_properties_by_name(oil_columns, field_indexes,
                                       'api_gravity', 'calculated_api_gravity')
    return [c[0].value for c in cells if c[0].value is not None]
