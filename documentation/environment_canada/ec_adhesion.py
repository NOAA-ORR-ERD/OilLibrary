
from ec_models import Adhesion

from ec_xl_parse import get_oil_properties_by_category
from ec_oil_props import get_oil_weathering
from ec_oil_misc import g_cm_2_to_kg_m_2


def get_oil_adhesions(oil_columns, field_indexes):
    '''
        Getting the adhesion is fairly straightforward.  We simply get the
        value in g/cm^2 and convert to kg/m^2.
        Dimensional parameters are simply (weathering).
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    adhesions = get_adhesions_by_weathering(oil_columns,
                                            field_indexes,
                                            weathering)

    return adhesions


def get_adhesions_by_weathering(oil_columns, field_indexes, weathering):
    adhesions = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'adhesion_g_cm2_ests_1996')
    prop_names = props.keys()

    for idx, vals in enumerate(zip(*props.values())):
        adhesion_kwargs = build_adhesion_kwargs(prop_names, vals,
                                                weathering[idx])
        adhesions.append(adhesion_kwargs)

    return [Adhesion(**a) for a in adhesions
            if a['kg_m_2'] is not None]


def build_adhesion_kwargs(prop_names, values, weathering):
    '''
        Build adhesion properties dictionary suitable to be passed in as
        keyword args.
        - prop_names: The list of property names
        - values: A list of Excel cell objects representing the properties.
        - weathering: The fractional oil weathering amount.
    '''
    adhesion_kwargs = dict(list(zip(prop_names, [v[0].value for v in values])))

    adhesion_kwargs['weathering'] = weathering

    adhesion_kwargs['kg_m_2'] = g_cm_2_to_kg_m_2(adhesion_kwargs['adhesion'])

    return adhesion_kwargs
