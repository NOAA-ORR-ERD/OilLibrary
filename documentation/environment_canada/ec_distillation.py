
from ec_models import ECCut

from ec_xl_parse import get_oil_properties_by_category, custom_slugify
from ec_oil_props import get_oil_weathering
from ec_oil_misc import celcius_to_kelvin


def get_oil_distillation_cuts(oil_columns, field_indexes):
    '''
        There are two distinct sets of distillation cut data in the EC
        spreadsheet. They are:
        - Boiling Point: Distribution, Temperature (C).  Here the labels are
                         percent values representing the fraction boiled off,
                         and the data is the temperature at which the
                         fractional value occurs.
        - Boiling Point: Cumulative Weight Fraction (%).  Here the labels are
                         temperatures (C) values, and the data is the fraction
                         that is boiled off at that temperature.

        We will try to get both sets of data and then merge them if possible.
        Most oils will have either one set or the other, not both.
        Dimensional parameters are simply (weathering).
    '''
    weathering = get_oil_weathering(oil_columns, field_indexes)

    bp_distribution = get_cuts_from_bp_distribution(oil_columns,
                                                    field_indexes,
                                                    weathering)

    bp_cumulative_frac = get_cuts_from_bp_cumulative_frac(oil_columns,
                                                          field_indexes,
                                                          weathering)

    return [item for sublist in (bp_distribution, bp_cumulative_frac)
            for item in sublist]


def get_cuts_from_bp_distribution(oil_columns, field_indexes, weathering):
    cuts = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'boiling_point_'
                                           'distribution_temperature_c')
    prop_names = props.keys()

    for idx, vals in enumerate(zip(*props.values())):
        cuts_from_dist = build_cuts_from_dist_data(prop_names, vals,
                                                   weathering[idx])
        cuts.extend(cuts_from_dist)

    return [c for c in cuts if c.vapor_temp_k is not None]


def build_cuts_from_dist_data(prop_names, values, weathering):
    '''
        Build a list of EC distillation cut objects from boiling point
        distribution data.
        - prop_names: The list of property names
        - values: A list of Excel cell objects representing the properties.
        - weathering: The fractional oil weathering amount.

        Note: The labels have a bit of a problem.  Most of them are percent
              value labels, which is fine, but additionally, we have
              'initial_boiling_point', and 'fbp'.  These are unusable because
              there is no indication of what fraction the initial and final
              boiling point has.  I could assume the initial boiling point has
              a fraction of 0%, but it is clear that the final boiling point is
              a temperature somewhere between the 95% and 100% temperatures.
              So it is a fraction somewhere between 95% and 100%, which we
              don't precisely know.
    '''
    cuts = []
    dist_data = dict(zip(prop_names, [v[0].value for v in values]))

    # The only labels we care about are the percent value labels
    for frac in ([(p / 100.0) for p in range(5, 100, 5)] + [1]):
        label = custom_slugify('{:0}'.format(frac))
        vapor_temp_c = dist_data[label]
        cuts.append(build_cut_kwargs(vapor_temp_c, frac, weathering))

    return [ECCut(**c) for c in cuts]


def get_cuts_from_bp_cumulative_frac(oil_columns, field_indexes, weathering):
    cuts = []

    props = get_oil_properties_by_category(oil_columns, field_indexes,
                                           'boiling_point_'
                                           'cumulative_weight_fraction')
    prop_names = props.keys()

    for idx, vals in enumerate(zip(*props.values())):
        cuts_from_dist = build_cuts_from_cumulative_fraction(prop_names, vals,
                                                             weathering[idx])
        cuts.extend(cuts_from_dist)

    return [c for c in cuts if c.fraction is not None]


def build_cuts_from_cumulative_fraction(prop_names, values, weathering):
    '''
        Build a list of EC distillation cut objects from cumulative weight
        fraction data.
        - prop_names: The list of property names
        - values: A list of Excel cell objects representing the properties.
        - weathering: The fractional oil weathering amount.

        Note: The labels have a bit of a problem.  Most of them are percent
              value labels, which is fine, but additionally, we have
              'initial_boiling_point', and 'fbp'.  These are unusable because
              there is no indication of what fraction the initial and final
              boiling point has.  I could assume the initial boiling point has
              a fraction of 0%, but it is clear that the final boiling point is
              a temperature somewhere between the 95% and 100% temperatures.
              So it is a fraction somewhere between 95% and 100%, which we
              don't precisely know.
    '''
    cuts = []
    dist_data = dict(zip(prop_names, [v[0].value for v in values]))

    # The only labels we care about are the temperature labels
    temp_values = [item
                   for sublist in [range(40, 200, 20), range(200, 701, 50)]
                   for item in sublist]

    for temp_c in temp_values:
        label = '{}'.format(temp_c)
        frac = dist_data[label]
        cuts.append(build_cut_kwargs(temp_c, frac, weathering))

    return [ECCut(**c) for c in cuts]


def build_cut_kwargs(vapor_temp_c, fraction, weathering):
    return {'vapor_temp_k': celcius_to_kelvin(vapor_temp_c),
            'fraction': fraction,
            'weathering': weathering}











