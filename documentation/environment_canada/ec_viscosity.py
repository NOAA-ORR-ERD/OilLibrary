
from oil_library.models import DVis

from ec_xl_parse import get_oil_properties_by_category
from ec_oil_props import get_oil_weathering
from ec_oil_misc import get_op_and_value


def get_oil_viscosities(oil_columns, field_indexes):
    '''
        Getting viscosities out of this datasheet is more tricky than it should
        be.  There are two categories, viscosity at 15C, and viscosity at 0/5C.
        I dunno, I would have organized the data in a more orthogonal way.
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    viscosities_at_0c = get_oil_viscosities_at_0c(oil_columns,
                                                  field_indexes,
                                                  weathering)

    viscosities_at_5c = get_oil_viscosities_at_5c(oil_columns,
                                                  field_indexes,
                                                  weathering)

    viscosities_at_15c = get_oil_viscosities_at_15c(oil_columns,
                                                    field_indexes,
                                                    weathering)

    return viscosities_at_0c + viscosities_at_5c + viscosities_at_15c


def get_oil_viscosities_at_15c(oil_columns, field_indexes, weathering):
    viscosities = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'viscosity_at_15_c_mpa_s')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        dvis_kwargs = build_dvis_kwargs(prop_names, vals,
                                        'viscosity_at_15_c_mpa_s',
                                        weathering[idx],
                                        273.15 + 15.0)

        viscosities.append(dvis_kwargs)

    return [DVis(**v) for v in viscosities
            if v['kg_ms'] not in (None, 0.0)]


def get_oil_viscosities_at_0c(oil_columns, field_indexes, weathering):
    viscosities = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'viscosity_at_0_5_c_mpa_s')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        dvis_kwargs = build_dvis_kwargs(prop_names, vals,
                                        'viscosity_at_0_c_mpa_s',
                                        weathering[idx],
                                        273.15)

        viscosities.append(dvis_kwargs)

    return [DVis(**v) for v in viscosities
            if v['kg_ms'] not in (None, 0.0)]


def get_oil_viscosities_at_5c(oil_columns, field_indexes, weathering):
    viscosities = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'viscosity_at_0_5_c_mpa_s')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        dvis_kwargs = build_dvis_kwargs(prop_names, vals,
                                        'viscosity_at_5_c_mpa_s',
                                        weathering[idx],
                                        273.15 + 5.0)

        viscosities.append(dvis_kwargs)

    return [DVis(**v) for v in viscosities
            if v['kg_ms'] not in (None, 0.0)]


def build_dvis_kwargs(prop_names, values, dvis_label, weathering, ref_temp_k):
    '''
        Build the argument list for creating a DVis database object.  The data
        is mostly what we expect, with only a few deviations.

        Note: Sometimes there is a greater than ('>') indication for a
              viscosity value.  I don't really know what else to do in
              this case but parse the float value and ignore the operator.
    '''
    dvis_kwargs = dict(list(zip(prop_names, [v[0].value for v in values])))

    dvis_kwargs['weathering'] = weathering

    dvis_kwargs['ref_temp_k'] = ref_temp_k

    _op, dvis_kwargs['kg_ms'] = get_op_and_value(dvis_kwargs[dvis_label])
    if dvis_kwargs['kg_ms'] is not None:
        dvis_kwargs['kg_ms'] *= 1e-3

    return dvis_kwargs
