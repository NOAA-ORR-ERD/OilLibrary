'''
    Factory methods for getting an oil object
'''
import numpy as np

from sqlalchemy.orm.exc import NoResultFound

import unit_conversion as uc

from . import _get_db_session
from . import _sample_oils
from .models import Oil, KVis, Density, Cut
from .utilities import get_boiling_points_from_api

from .oil_props import OilProps

from .init_oil import (density_at_temperature,
                       add_ra_fractions,
                       add_molecular_weights,
                       add_saturate_aromatic_fractions,
                       add_component_densities,
                       adjust_resin_asphaltene_fractions)


def get_oil(oil_, max_cuts=None):
    """
    function returns the Oil object given the name of the oil as a string.

    :param oil_: The oil that spilled.
                 - If it is a dictionary of items, then we will assume it is
                   a JSON payload sufficient for creating an Oil object.
                 - If it is one of the names stored in _sample_oil dict,
                   then an Oil object with specified API is returned.
                 - Otherwise, query the database for the oil_name and return
                   the associated Oil object.
    :type oil_: str or dict

    Optional arg:

    :param max_cuts: This is ** only ** used for _sample_oils which dont have
        distillation cut information. For testing, this allows us to model the
        oil with variable number of cuts, with equally divided mass. For a
        real oil pulled from the database, this is ignored.
    :type max_cuts: int

    NOTE I:
    -------
    One issue is that the kwargs in Oil contain spaces, like 'oil_'. This
    can be handled if the user defines a dict as follows:
        kw = {'oil_': 'new oil', 'Field Name': 'field name'}
        get_oil(**kw)
    however, the following will not work:
        get_oil('oil_'='new oil', 'Field Name'='field name')

    This is another reason, we need an interface between the SQL object and the
    end user.
    """
    if isinstance(oil_, dict):
        prune_db_ids(oil_)
        oil_obj = Oil.from_json(oil_)

        add_kvis_from_dvis(oil_obj, oil_)

        _estimate_missing_oil_props(oil_obj, max_cuts)

        return oil_obj

    if oil_ in _sample_oils.keys():
        return _sample_oils[oil_]
    else:
        '''
        db_file should exist - if it doesn't then create if first
        should we raise error here?
        '''
        session = _get_db_session()

        try:
            oil = session.query(Oil).filter(Oil.name == oil_).one()
            oil.densities
            oil.kvis
            oil.cuts
            oil.sara_fractions
            oil.sara_densities
            oil.molecular_weights
            return oil
        except NoResultFound, ex:
            ex.message = ("oil with name '{0}', not found in database.  "
                          "{1}".format(oil_, ex.message))
            ex.args = (ex.message, )
            raise ex


def prune_db_ids(oil_):
    '''
        If we are instantiating an oil using a JSON payload, we do not
        need any id to be passed.  It is not necessary, and is in fact
        misleading.
        We probably only need to do it here in this module.
    '''
    for attr in ('id', 'oil_id', 'imported_record_id', 'estimated_id'):
        if attr in oil_:
            del oil_[attr]

    for list_attr in ('cuts', 'densities', 'kvis', 'molecular_weights',
                      'sara_fractions', 'sara_densities'):
        if list_attr in oil_:
            for item in oil_[list_attr]:
                for attr in ('id', 'oil_id', 'imported_record_id',
                             'estimated_id'):
                    if attr in item:
                        del item[attr]


def add_kvis_from_dvis(oil_obj, oil_json):
    '''
        Our Oil object has no dynamic viscosity properties, but we may have
        dynamic viscosities in our JSON payload.  So we convert them to
        kinematic viscosity records and add them.
    '''
    if 'dvis' in oil_json:
        kvis_values = [convert_dvis_to_kvis(oil_obj, **d)
                       for d in oil_json['dvis']]
        all_kwargs = [dict(d.items() + [('m_2_s', k)])
                      for d, k in zip(oil_json['dvis'], kvis_values)
                      if k is not None]
        for kwargs in all_kwargs:
            if not kvis_exists(oil_obj.kvis, kwargs):
                oil_obj.kvis.append(KVis(**kwargs))

    oil_obj.kvis.sort(key=lambda k: k.ref_temp_k)


def convert_dvis_to_kvis(oil_obj, kg_ms, ref_temp_k):
    density = density_at_temperature(oil_obj, ref_temp_k)
    if density is None:
        return None
    else:
        return kg_ms / density


def kvis_exists(kvis, kwargs):
    temperature = kwargs['ref_temp_k']
    weathering = kwargs.get('weathering', 0.0)
    return len([v for v in kvis
                if (v.ref_temp_k == temperature and
                    v.weathering == weathering)
                ]) > 0


def _estimate_missing_oil_props(oil_obj, max_cuts):
    if oil_obj.densities == [] and oil_obj.api is not None:
        _add_density_estimated_from_api(oil_obj)

    if oil_obj.cuts == [] and oil_obj.api is not None:
        _add_cuts_estimated_from_api(oil_obj, max_cuts)

    if oil_obj.molecular_weights == []:
        add_molecular_weights(None, oil_obj)

    if oil_obj.sara_fractions == []:
        add_ra_fractions(None, oil_obj)
        add_saturate_aromatic_fractions(None, oil_obj)

    if oil_obj.sara_densities == []:
        add_component_densities(None, oil_obj)

    if oil_obj.molecular_weights == []:
        adjust_resin_asphaltene_fractions(None, oil_obj)


def _add_density_estimated_from_api(oil_obj):
    kg_m_3 = uc.convert('density', 'api', 'kg/m^3', oil_obj.api)

    oil_obj.densities = [Density(kg_m_3=kg_m_3, ref_temp_k=288.15)]


def _add_cuts_estimated_from_api(oil_obj, max_cuts):
        mass_left = 1.0
        mass_left -= sum([f.fraction for f in oil_obj.sara_fractions
                          if f.sara_type in ('Resins', 'Asphaltenes')])

        prev_mass_frac = 0.0

        summed_boiling_points = []
        for t, f in get_boiling_points_from_api(max_cuts, mass_left,
                                                oil_obj.api):
            added_to_sums = False

            for idx, [ut, _summed_value] in enumerate(summed_boiling_points):
                if np.isclose(t, ut):
                    summed_boiling_points[idx][1] += f
                    added_to_sums = True
                    break

            if added_to_sums is False:
                summed_boiling_points.append([t, f])

        for t_i, fraction in summed_boiling_points:
            oil_obj.cuts.append(Cut(fraction=prev_mass_frac + fraction,
                                    vapor_temp_k=t_i))
            prev_mass_frac += fraction


def get_oil_props(oil_info, max_cuts=None):
    '''
    returns the OilProps object
    max_cuts is only used for 'fake' sample_oils. It's a way to allow testing.
    When pulling record from database, this is ignored.
    '''
    oil_ = get_oil(oil_info, max_cuts)
    return OilProps(oil_)
