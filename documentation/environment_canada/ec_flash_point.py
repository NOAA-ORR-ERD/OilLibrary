
from ec_models import FlashPoint

from ec_xl_parse import get_oil_properties_by_category
from ec_oil_props import get_oil_weathering
from ec_oil_misc import get_min_temp, get_max_temp


def get_oil_flash_points(oil_columns, field_indexes):
    '''
        Getting the flash point is similar to Adios2 in that the values
        contain '>' and '<' symbols.  This indicates we need to interpret the
        content to come up with minimum and maximum values.
        Dimensional parameters are simply (weathering).
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    flash_points = get_flash_points_by_weathering(oil_columns,
                                                  field_indexes,
                                                  weathering)

    return flash_points


def get_flash_points_by_weathering(oil_columns, field_indexes, weathering):
    flash_points = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'flash_point_c')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        flash_point_obj = build_flash_point_kwargs(prop_names, vals,
                                                   weathering[idx])
        flash_points.append(flash_point_obj)

    return [FlashPoint(**f) for f in flash_points
            if f['min_temp_k'] is not None or f['max_temp_k'] is not None]


def build_flash_point_kwargs(prop_names, values, weathering):
    '''
        Build a flash point properties dictionary suitable to be passed in as
        keyword args.
        - prop_names: The list of property names
        - values: A list of Excel cell objects representing the properties.
        - weathering: The fractional oil weathering amount.
    '''
    flash_point_obj = dict(list(zip(prop_names, [v[0].value for v in values])))

    flash_point_obj['weathering'] = weathering

    flash_point_obj['min_temp_k'] = get_min_temp(flash_point_obj['flash_point'])
    flash_point_obj['max_temp_k'] = get_max_temp(flash_point_obj['flash_point'])

    return flash_point_obj
