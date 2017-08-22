
from ec_models import Emulsion

from ec_xl_parse import get_oil_properties_by_category
from ec_oil_props import get_oil_weathering
from ec_oil_misc import percent_to_fraction


def get_oil_emulsions(oil_columns, field_indexes):
    '''
        The Evironment Canada data sheet contains data for emulsion properties,
        which we will try to capture.
        Dimensional parameters are (temperature, age, weathering).
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    emulsion_age_0 = get_emulsion_age_0(oil_columns, field_indexes, weathering)

    emulsion_age_7 = get_emulsion_age_7(oil_columns, field_indexes, weathering)

    return emulsion_age_0 + emulsion_age_7


def get_emulsion_age_0(oil_columns, field_indexes, weathering):
    emulsions = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'emulsion_at_15_degc_'
                                           'on_the_day_of_formation_'
                                           'ests_1998_2')
    prop_names = props.keys()

    for idx, vals in enumerate(zip(*props.values())):
        emulsion_kwargs = build_emulsion_kwargs(prop_names, vals,
                                                weathering[idx],
                                                273.15 + 15.0, 0.0)
        emulsions.append(emulsion_kwargs)

    return [Emulsion(**e) for e in emulsions
            if e['water_content_fraction'] is not None]


def get_emulsion_age_7(oil_columns, field_indexes, weathering):
    emulsions = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'emulsion_at_15_degc_'
                                           'one_week_after_formation_'
                                           'ests_1998b')
    prop_names = props.keys()

    for idx, vals in enumerate(zip(*props.values())):
        emulsion_kwargs = build_emulsion_kwargs(prop_names, vals,
                                                weathering[idx],
                                                273.15 + 15.0, 7.0)
        emulsions.append(emulsion_kwargs)

    return [Emulsion(**e) for e in emulsions
            if e['water_content_fraction'] is not None]


def build_emulsion_kwargs(prop_names, values,
                          weathering, ref_temp_k, age_days):
    '''
        Build emulsion properties dictionary suitable to be passed in as
        keyword args.
        - prop_names: The list of property names
        - values: A list of Excel cell objects representing the properties.
        - weathering: The fractional oil weathering amount.
    '''
    emul_kwargs = dict(zip(prop_names, [v[0].value for v in values]))

    emul_kwargs['weathering'] = weathering
    emul_kwargs['ref_temp_k'] = ref_temp_k
    emul_kwargs['age_days'] = age_days

    # emul_kwargs['complex_modulus_pa']  # already there
    # emul_kwargs['storage_modulus_pa']  # already there
    # emul_kwargs['loss_modulus_pa']  # already there
    # emul_kwargs['tan_delta_v_e']  # already there
    # emul_kwargs['complex_viscosity_pa_s']  # already there

    emul_kwargs['water_content_fraction'] = percent_to_fraction(emul_kwargs['water_content_w_w'])

    return emul_kwargs
