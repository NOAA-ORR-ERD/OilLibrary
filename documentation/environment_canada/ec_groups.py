
from ec_xl_parse import get_oil_properties_by_category
from ec_oil_props import get_oil_weathering
from ec_oil_misc import get_op_and_value, percent_to_fraction


def get_oil_sulfur_content(oil_columns, field_indexes):
    '''
        Getting the sulfur content is very straightforward.  Just get the
        float value.
        Dimensional parameters are (weathering).
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    sulfur_contents = get_sulfur_content_by_weathering(oil_columns,
                                                       field_indexes,
                                                       weathering)

    return sulfur_contents


def get_oil_water_content(oil_columns, field_indexes):
    '''
        Dimensional parameters are (weathering).
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    water_contents = get_water_content_by_weathering(oil_columns,
                                                     field_indexes,
                                                     weathering)

    return water_contents


def get_oil_wax_content(oil_columns, field_indexes):
    '''
        Dimensional parameters are (weathering).
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    wax_contents = get_wax_content_by_weathering(oil_columns,
                                                 field_indexes,
                                                 weathering)

    return wax_contents


def get_oil_sara_total_fractions(oil_columns, field_indexes):
    '''
        Dimensional parameters are (weathering).
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    saturates = get_saturates_fraction_by_weathering(oil_columns,
                                                     field_indexes,
                                                     weathering)
    aromatics = get_aromatics_fraction_by_weathering(oil_columns,
                                                     field_indexes,
                                                     weathering)
    resins = get_resins_fraction_by_weathering(oil_columns,
                                               field_indexes,
                                               weathering)
    asphaltenes = get_asphaltenes_fraction_by_weathering(oil_columns,
                                                         field_indexes,
                                                         weathering)

    return list(zip(saturates, aromatics, resins, asphaltenes))


def get_sulfur_content_by_weathering(oil_columns, field_indexes, weathering):
    sulfur_contents = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'sulfur_content_astm_d4294')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        kwargs = build_kwargs(prop_names, vals, weathering[idx])
        sulfur_contents.append(kwargs)

    return [percent_to_fraction(f['sulfur_content'])
            for f in sulfur_contents
            if f['sulfur_content'] is not None]


def get_water_content_by_weathering(oil_columns, field_indexes, weathering):
    water_contents = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'water_content_astm_e203')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        kwargs = build_kwargs(prop_names, vals, weathering[idx])
        water_contents.append(kwargs)

    return [percent_to_fraction(get_op_and_value(f['water_content'])[1])
            for f in water_contents
            if f['water_content'] is not None]


def get_wax_content_by_weathering(oil_columns, field_indexes, weathering):
    wax_contents = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'wax_content_ests_1994')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        kwargs = build_kwargs(prop_names, vals, weathering[idx],
                              props_to_rename={'waxes': 'wax_content'})
        wax_contents.append(kwargs)

    return [percent_to_fraction(f['wax_content'])
            for f in wax_contents
            if f['wax_content'] is not None]


def get_saturates_fraction_by_weathering(oil_columns, field_indexes,
                                         weathering):
    saturates_fractions = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'hydrocarbon_group_content')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        props_to_rename = {'saturates': 'saturates_fraction'}
        kwargs = build_kwargs(prop_names, vals, weathering[idx],
                              props_to_rename=props_to_rename)
        saturates_fractions.append(kwargs)

    return [percent_to_fraction(f['saturates_fraction'])
            for f in saturates_fractions
            if f['saturates_fraction'] is not None]


def get_aromatics_fraction_by_weathering(oil_columns, field_indexes,
                                         weathering):
    aromatics_fractions = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'hydrocarbon_group_content')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        props_to_rename = {'aromatics': 'aromatics_fraction'}
        kwargs = build_kwargs(prop_names, vals, weathering[idx],
                              props_to_rename=props_to_rename)
        aromatics_fractions.append(kwargs)

    return [percent_to_fraction(f['aromatics_fraction'])
            for f in aromatics_fractions
            if f['aromatics_fraction'] is not None]


def get_resins_fraction_by_weathering(oil_columns, field_indexes,
                                      weathering):
    resins_fractions = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'hydrocarbon_group_content')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        props_to_rename = {'resin': 'resins_fraction'}
        kwargs = build_kwargs(prop_names, vals, weathering[idx],
                              props_to_rename=props_to_rename)
        resins_fractions.append(kwargs)

    return [percent_to_fraction(f['resins_fraction'])
            for f in resins_fractions
            if f['resins_fraction'] is not None]


def get_asphaltenes_fraction_by_weathering(oil_columns, field_indexes,
                                           weathering):
    asphaltenes_fractions = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'hydrocarbon_group_content')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        props_to_rename = {'asphaltene': 'asphaltenes_fraction'}
        kwargs = build_kwargs(prop_names, vals, weathering[idx],
                              props_to_rename=props_to_rename)
        asphaltenes_fractions.append(kwargs)

    return [percent_to_fraction(f['asphaltenes_fraction'])
            for f in asphaltenes_fractions
            if f['asphaltenes_fraction'] is not None]


def build_kwargs(prop_names, values, weathering,
                 props_to_rename=None):
    '''
        Build a content properties dictionary suitable to be passed in
        as keyword args.
        - prop_names: The list of property names
        - values: A list of Excel cell objects representing the properties.
        - weathering: The fractional oil weathering amount.
    '''
    kwargs = dict(list(zip(prop_names, [v[0].value for v in values])))

    kwargs['weathering'] = weathering

    if props_to_rename is not None:
        for old_prop, new_prop in props_to_rename.items():
            rename_prop(kwargs, old_prop, new_prop)

    return kwargs


def rename_prop(kwargs, old_prop, new_prop):
    kwargs[new_prop] = kwargs[old_prop]
    del kwargs[old_prop]
