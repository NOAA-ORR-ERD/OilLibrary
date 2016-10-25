'''
    Factory methods for getting an oil object
'''
import numpy as np

from sqlalchemy.orm.exc import NoResultFound

from . import _get_db_session
from . import _sample_oils
from .models import (Oil, KVis, Density, Cut,
                     MolecularWeight, SARAFraction, SARADensity)

from .oil_props import OilProps

import utilities.estimations as est
from .utilities.imported_record import ImportedRecordWithEstimation
from .utilities.json_record import JsonRecordWithEstimation


def get_oil_props(oil_info, max_cuts=None):
    '''
    returns the OilProps object
    max_cuts is only used for 'fake' sample_oils. It's a way to allow testing.
    When pulling record from database, this is ignored.
    '''
    oil_ = get_oil(oil_info, max_cuts)
    return OilProps(oil_)


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

    """
    if isinstance(oil_, dict):
        prune_db_ids(oil_)
        oil_obj = Oil.from_json(oil_)

        _estimate_missing_oil_props(oil_obj, oil_, max_cuts)

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


def _estimate_missing_oil_props(oil_obj, oil_json, max_cuts):
    oil_obj = ImportedRecordWithEstimation(oil_obj)
    json_obj = JsonRecordWithEstimation(oil_json)

    _add_missing_density_info(oil_obj)

    _add_kvis_from_dvis(oil_obj, json_obj)

    _add_inert_fractions(oil_obj, json_obj)

    if len(list(oil_obj.culled_cuts())) == 0:
        _normalize_cuts(oil_obj)

    if (len(oil_obj.record.molecular_weights) == 0 or
            len(oil_obj.record.sara_fractions) == 0 or
            len(oil_obj.record.sara_densities) == 0):
        # these three sequences are to be treated with a common indexing
        # scheme.  So if any of them are 0, then they all need to be
        # estimated.
        del oil_obj.record.molecular_weights[:]
        del oil_obj.record.sara_fractions[:]
        del oil_obj.record.sara_densities[:]

        # Component Fractional estimations
        _add_component_mol_wt(oil_obj, json_obj)

        _add_component_mass_fractions(oil_obj, json_obj)

        _add_component_densities(oil_obj, json_obj)


def _add_missing_density_info(oil_obj):
    if len(oil_obj.record.densities) == 0 and oil_obj.record.api is None:
        raise ValueError('Oil object has no density information and no API!!')
    elif len(oil_obj.record.densities) == 0:
        kg_m_3, ref_temp_k = est.density_from_api(oil_obj.get_api())

        oil_obj.record.densities.append(Density(kg_m_3=kg_m_3,
                                                ref_temp_k=ref_temp_k))
    else:  # oil_obj.api is None
        oil_obj.api = oil_obj.get_api()


def _add_kvis_from_dvis(oil_obj, oil_json):
    '''
        Our Oil object has no dynamic viscosity properties, but we may have
        dynamic viscosities in our JSON payload.  So we convert them to
        kinematic viscosity records and add them.
    '''
    if 'dvis' in oil_json.record:
        dvis_list = list(oil_json.non_redundant_dvis())
        densities = [oil_json.density_at_temp(d['ref_temp_k'])
                     for d in dvis_list]

        for dv, rho in zip(dvis_list, densities):
            kvis_json = oil_json.dvis_obj_to_kvis_obj(dv, rho)
            oil_obj.record.kvis.append(KVis(**kvis_json))

    oil_obj.record.kvis.sort(key=lambda k: (k.weathering, k.ref_temp_k))


def _add_inert_fractions(oil_obj, oil_json):
    f_res, f_asph = oil_json.inert_fractions()

    if oil_obj.record.resins_fraction is None:
        oil_obj.record.resins_fraction = f_res

    if oil_obj.record.asphaltenes_fraction is None:
        oil_obj.record.asphaltenes_fraction = f_asph


def kvis_exists(kvis, kwargs):
    temperature = kwargs['ref_temp_k']
    weathering = kwargs.get('weathering', 0.0)
    return len([v for v in kvis
                if (v.ref_temp_k == temperature and
                    v.weathering == weathering)
                ]) > 0


def _normalize_cuts(oil_obj):
    temps, fractions = oil_obj.normalized_cut_values()

    # Remove our original cuts.  I am not sure, but for SQLAlchemy iterable
    # relationships, we might want to preserve the object, so we just
    # clear it out.
    del oil_obj.record.cuts[:]

    for T_i, f_evap_i in zip(temps, fractions):
        oil_obj.record.cuts.append(Cut(vapor_temp_k=T_i, fraction=f_evap_i))


def _add_component_mol_wt(oil_obj, json_obj):
    temps = json_obj.component_temps()
    mol_wts = json_obj.component_mol_wt()
    c_types = json_obj.component_types()

    for T_i, mol_wt_i, c_type in zip(temps, mol_wts, c_types):
        (oil_obj.record.molecular_weights
         .append(MolecularWeight(sara_type=c_type,
                                 g_mol=mol_wt_i,
                                 ref_temp_k=T_i)))


def _add_component_mass_fractions(oil_obj, oil_json):
    temps = oil_json.component_temps()
    fracs = oil_json.component_mass_fractions()
    c_types = oil_json.component_types()

    for T_i, f_i, c_type in zip(temps, fracs, c_types):
        oil_obj.record.sara_fractions.append(SARAFraction(sara_type=c_type,
                                                          fraction=f_i,
                                                          ref_temp_k=T_i))


def _add_component_densities(oil_obj, oil_json):
    densities = oil_json.component_densities()
    fracs = oil_json.component_mass_fractions()
    temps = oil_json.component_temps()
    c_types = oil_json.component_types()

    # we need to scale our densities to match our aggregate density
    rho0_oil = oil_json.density_at_temp(273.15 + 15)
    Cf_dens = (rho0_oil / np.sum(fracs * densities))

    densities *= Cf_dens

    for T_i, rho, c_type in zip(temps, densities, c_types):
        oil_obj.record.sara_densities.append(SARADensity(sara_type=c_type,
                                                         density=rho,
                                                         ref_temp_k=T_i))
