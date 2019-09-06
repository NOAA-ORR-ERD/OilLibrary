
from ec_models import PourPoint

from ec_xl_parse import get_oil_properties_by_category
from ec_oil_props import get_oil_weathering
from ec_oil_misc import get_min_temp, get_max_temp


def get_oil_pour_points(oil_columns, field_indexes):
    '''
        Getting the pour point is similar to Adios2 in that the values
        contain '>' and '<' symbols.  This indicates we need to interpret the
        content to come up with minimum and maximum values.
        Dimensional parameters are simply (weathering).
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    pour_points = get_pour_points_by_weathering(oil_columns,
                                                field_indexes,
                                                weathering)

    return pour_points


def get_pour_points_by_weathering(oil_columns, field_indexes, weathering):
    pour_points = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'pour_point_c')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        pour_point_obj = build_pour_point_kwargs(prop_names, vals,
                                                 weathering[idx])
        pour_points.append(pour_point_obj)

    return [PourPoint(**p) for p in pour_points
            if p['min_temp_k'] is not None or p['max_temp_k'] is not None]


def build_pour_point_kwargs(prop_names, values, weathering):
    '''
        Build a flash point properties dictionary suitable to be passed in as
        keyword args.
        - prop_names: The list of property names
        - values: A list of Excel cell objects representing the properties.
        - weathering: The fractional oil weathering amount.
    '''
    pour_point_obj = dict(list(zip(prop_names, [v[0].value for v in values])))

    pour_point_obj['weathering'] = weathering

    pour_point_obj['min_temp_k'] = get_min_temp(pour_point_obj['pour_point'])
    pour_point_obj['max_temp_k'] = get_max_temp(pour_point_obj['pour_point'])

    return pour_point_obj
