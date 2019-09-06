
from ec_models import EvaporationEq

from ec_xl_parse import get_oil_properties_by_category
from ec_oil_props import get_oil_weathering


def get_oil_evaporation_eqs(oil_columns, field_indexes):
    '''
        The Evironment Canada data sheet contains equations for evaporative
        loss, along with coefficient values to be used per oil. There are
        three equations and three possible coefficients (A, B, and optionally
        C). We will try to capture both the algorithm and the coefficients.
        Dimensional parameters are simply (weathering).
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)
    evap_ests_1998 = get_evaporation_eqs_ests_1998(oil_columns,
                                                   field_indexes,
                                                   weathering)

    evap_mass_loss1 = get_evaporation_eqs_mass_loss1(oil_columns,
                                                     field_indexes,
                                                     weathering)

    evap_mass_loss2 = get_evaporation_eqs_mass_loss2(oil_columns,
                                                     field_indexes,
                                                     weathering)

    return evap_ests_1998 + evap_mass_loss1 + evap_mass_loss2


def get_evaporation_eqs_ests_1998(oil_columns, field_indexes, weathering):
    evaporation_eqs = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'evaporation_ests_1998_1')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        evaporation_kwargs = build_evaporation_kwargs(prop_names, vals,
                                                      weathering[idx],
                                                      '(A + BT) ln t',
                                                      'for_ev_a_bt_ln_t')
        evaporation_eqs.append(evaporation_kwargs)

    return [EvaporationEq(**eq) for eq in evaporation_eqs
            if eq['a'] is not None and eq['b'] is not None]


def get_evaporation_eqs_mass_loss1(oil_columns, field_indexes, weathering):
    evaporation_eqs = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'parameters_for_'
                                           'evaporation_equation_mass_loss')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        evaporation_kwargs = build_evaporation_kwargs(prop_names, vals,
                                                      weathering[idx],
                                                      '(A + BT) sqrt(t)',
                                                      'for_ev_a_bt_sqrt_t')
        evaporation_eqs.append(evaporation_kwargs)

    return [EvaporationEq(**eq) for eq in evaporation_eqs
            if eq['a'] is not None and eq['b'] is not None]


def get_evaporation_eqs_mass_loss2(oil_columns, field_indexes, weathering):
    evaporation_eqs = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'parameters_for_'
                                           'evaporation_equation_mass_loss')
    prop_names = list(props.keys())

    for idx, vals in enumerate(zip(*list(props.values()))):
        evaporation_kwargs = build_evaporation_kwargs(prop_names, vals,
                                                      weathering[idx],
                                                      'A + B ln (t + C)',
                                                      'for_ev_a_b_ln_t_c')
        evaporation_eqs.append(evaporation_kwargs)

    return [EvaporationEq(**eq) for eq in evaporation_eqs
            if eq['a'] is not None and eq['b'] is not None]


def build_evaporation_kwargs(prop_names, values, weathering,
                             equation, coeff_label):
    '''
        Build evaporation equation properties dictionary suitable to be
        passed in as keyword args.
        - prop_names: The list of property names
        - values: A list of Excel cell objects representing the properties.
        - weathering: The fractional oil weathering amount.
        - coeff_label: the property label containing our coefficients.  This
                       is a suffix that we will prepend with the coefficient
                       we would like to get.
    '''
    evap_kwargs = dict(list(zip(prop_names, [v[0].value for v in values])))

    evap_kwargs['weathering'] = weathering
    evap_kwargs['equation'] = equation

    evap_kwargs['a'] = evap_kwargs['a_{}'.format(coeff_label)]
    evap_kwargs['b'] = evap_kwargs['b_{}'.format(coeff_label)]

    if 'c_{}'.format(coeff_label) in evap_kwargs:
        evap_kwargs['c'] = evap_kwargs['c_{}'.format(coeff_label)]

    return evap_kwargs






