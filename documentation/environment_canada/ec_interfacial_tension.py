
from ec_models import InterfacialTension

from ec_xl_parse import get_oil_properties_by_category
from ec_oil_props import get_oil_weathering


def get_oil_interfacial_tensions(oil_columns, field_indexes):
    '''
        Getting interfacial tensions out of this datasheet is a bit tricky,
        but understandably so since we are dealing with a number of dimensional
        parameters (temperature, interface, weathering).
        There are two categories, surface/interfacial tension at 15C, and
        surface/interfacial tension at 0/5C.
        I still think it could have been organized more orthogonally.
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    tensions_at_0c = get_oil_tensions_at_0c(oil_columns,
                                            field_indexes,
                                            weathering)

    tensions_at_5c = get_oil_tensions_at_5c(oil_columns,
                                            field_indexes,
                                            weathering)

    tensions_at_15c = get_oil_tensions_at_15c(oil_columns,
                                              field_indexes,
                                              weathering)

    return tensions_at_0c + tensions_at_5c + tensions_at_15c


def get_oil_tensions_at_15c(oil_columns, field_indexes, weathering):
    tensions = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'surface_interfacial_tension_'
                                           'at_15_c_mn_m_or_dynes_cm')
    prop_names = props.keys()

    for idx, vals in enumerate(zip(*props.values())):
        tension_obj = build_tension_kwargs(prop_names, vals,
                                           'surface_tension_15_c_oil_air',
                                           weathering[idx],
                                           273.15 + 15.0, 'air')
        tensions.append(tension_obj)

        tension_obj = build_tension_kwargs(prop_names, vals,
                                           'interfacial_tension_'
                                           '15_c_oil_water',
                                           weathering[idx],
                                           273.15 + 15.0, 'water')
        tensions.append(tension_obj)

        tension_obj = build_tension_kwargs(prop_names, vals,
                                           'interfacial_tension_'
                                           '15_c_oil_salt_water_3_3_nacl',
                                           weathering[idx],
                                           273.15 + 15.0, 'seawater')
        tensions.append(tension_obj)

    return [InterfacialTension(**t) for t in tensions
            if t['n_m'] not in (None, 0.0)]


def get_oil_tensions_at_0c(oil_columns, field_indexes, weathering):
    tensions = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'surface_interfacial_tension_'
                                           'at_0_5_c_mn_m_or_dynes_cm')
    prop_names = props.keys()

    for idx, vals in enumerate(zip(*props.values())):
        tension_obj = build_tension_kwargs(prop_names, vals,
                                           'surface_tension_0_c_oil_air',
                                           weathering[idx],
                                           273.15, 'air')
        tensions.append(tension_obj)

        tension_obj = build_tension_kwargs(prop_names, vals,
                                           'interfacial_tension_0_c_oil_water',
                                           weathering[idx],
                                           273.15, 'water')
        tensions.append(tension_obj)

        tension_obj = build_tension_kwargs(prop_names, vals,
                                           'interfacial_tension_'
                                           '0_c_oil_salt_water_3_3_nacl',
                                           weathering[idx],
                                           273.15, 'seawater')
        tensions.append(tension_obj)

    return [InterfacialTension(**t) for t in tensions
            if t['n_m'] not in (None, 0.0)]


def get_oil_tensions_at_5c(oil_columns, field_indexes, weathering):
    tensions = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'surface_interfacial_tension_'
                                           'at_0_5_c_mn_m_or_dynes_cm')
    prop_names = props.keys()

    for idx, vals in enumerate(zip(*props.values())):
        tension_obj = build_tension_kwargs(prop_names, vals,
                                           'surface_tension_5_c_oil_air',
                                           weathering[idx],
                                           273.15 + 5.0, 'air')
        tensions.append(tension_obj)

        tension_obj = build_tension_kwargs(prop_names, vals,
                                           'interfacial_tension_5_c_oil_water',
                                           weathering[idx],
                                           273.15 + 5.0, 'water')
        tensions.append(tension_obj)

        tension_obj = build_tension_kwargs(prop_names, vals,
                                           'interfacial_tension_'
                                           '5_c_oil_salt_water_3_3_nacl',
                                           weathering[idx],
                                           273.15 + 5.0, 'seawater')
        tensions.append(tension_obj)

    return [InterfacialTension(**t) for t in tensions
            if t['n_m'] not in (None, 0.0)]


def build_tension_kwargs(prop_names, values, ift_name,
                         weathering, ref_temp_k, interface):
    '''
        Build a surface tension dictionary suitable to be passed in as
        keyword args.
        - prop_names: The list of property names
        - values: A list of Excel cell objects representing the properties.
        - ift_name: The interfacial tension property name.  This property will
                    need to be converted to N/m, and renamed to 'n_m'.
        - weathering: The fractional oil weathering amount.
        - ref_temp_k: The temperature of the oil at measurement time.
        - interface: The type of substance interfacing the oil.
    '''
    tension_obj = dict(zip(prop_names, [v[0].value for v in values]))

    # add some properties to the oil that we expect
    add_tension_kwargs(tension_obj, ref_temp_k, weathering, interface)

    tension_obj['n_m'] = convert_to_nm(tension_obj[ift_name])

    return tension_obj


def add_tension_kwargs(tension_obj, ref_temp_k, weathering, interface):
    tension_obj['ref_temp_k'] = ref_temp_k
    tension_obj['weathering'] = weathering
    tension_obj['interface'] = interface


def convert_to_nm(mn_per_m):
    '''
        Convert mN/m (dynes/cm) into N/m or return None value
    '''
    if isinstance(mn_per_m, (int, long, float)):
        return mn_per_m * 1e-3
    else:
        return None
