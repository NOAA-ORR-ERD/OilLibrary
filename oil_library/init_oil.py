'''
    This is where we handle the initialization of the estimated oil properties.
    This will be the 'real' oil record that we use.

    Basically, we have an Estimated object that is a one-to-one relationship
    with the Oil object.  This is where we will place the estimated oil
    properties.
'''
import logging
import transaction

import numpy as np

from .models import (ImportedRecord, Oil, Estimated,
                     Cut, SARAFraction, SARADensity, MolecularWeight)

from .utilities.estimations import api_from_density

from .utilities.imported_record import ImportedRecordWithEstimation
from .utilities.oil import OilWithEstimation


from pprint import PrettyPrinter
pp = PrettyPrinter(indent=2, width=120)

logger = logging.getLogger(__name__)


class OilRejected(Exception):
    '''
        Custom exception for Oil initialization that we can raise if we
        decide we need to reject an oil record for any reason.
    '''
    def __init__(self, message, oil_name, *args):
        # without this you may get DeprecationWarning
        self.message = message

        # Special attribute you desire with your Error,
        # perhaps the value that caused the error?:
        self.oil_name = oil_name

        # allow users initialize misc. arguments as any other builtin Error
        super(OilRejected, self).__init__(message, oil_name, *args)

    def __repr__(self):
        return '{0}(oil={1}, errors={2})'.format(self.__class__.__name__,
                                                 self.oil_name,
                                                 self.message)


def pprint_for_one_oil(oil, *args):
    '''
        Just a simple diagnostic printing routine.
        The idea is to print messages for just one oil record
        to reduce verboseness when diagnosing these routines.
    '''
    adios_oil_id = 'AD02434'

    if hasattr(oil, 'adios_oil_id') and oil.adios_oil_id == adios_oil_id:
        pp.pprint(args)


def process_oils(session_class):
    session = session_class()
    record_ids = [r.adios_oil_id for r in session.query(ImportedRecord)]
    session.close()

    logger.info('Adding Oil objects...')
    for record_id in record_ids:
        # Note: committing our transaction for every record slows the
        #       import job significantly.  But this is necessary if we
        #       want the option of rejecting oil records.
        session = session_class()
        transaction.begin()
        rec = (session.query(ImportedRecord)
               .filter(ImportedRecord.adios_oil_id == record_id)
               .one())

        try:
            add_oil(rec)
            transaction.commit()
        except OilRejected as e:
            logger.warning(repr(e))
            transaction.abort()


def add_oil(record):
    oil = generate_oil(record)

    reject_oil_if_bad(record, oil)

    record.oil = oil


def generate_oil(imported_rec):
    logger.info('Begin estimations for {0}'
                .format(imported_rec.adios_oil_id))
    oil = Oil()
    oil.estimated = Estimated()
    imp_rec_obj = ImportedRecordWithEstimation(imported_rec)

    add_demographics(imp_rec_obj, oil)

    # Core estimations
    add_densities(imp_rec_obj, oil)
    add_viscosities(imp_rec_obj, oil)

    # Distillation estimations
    add_inert_fractions(imp_rec_obj, oil)
    add_distillation_cuts(imp_rec_obj, oil)

    # Component Fractional estimations
    add_component_mol_wt(imp_rec_obj, oil)
    add_component_mass_fractions(imp_rec_obj, oil)
    add_component_densities(imp_rec_obj, oil)

    # Miscellaneous estimations
    add_oil_water_interfacial_tension(imp_rec_obj, oil)
    add_oil_seawater_interfacial_tension(imp_rec_obj, oil)
    add_pour_point(imp_rec_obj, oil)
    add_flash_point(imp_rec_obj, oil)
    add_max_water_fraction_of_emulsion(imp_rec_obj, oil)
    add_bullwinkle_fractions(imp_rec_obj, oil)
    add_solubility(imp_rec_obj, oil)
    add_adhesion(imp_rec_obj, oil)
    add_sulphur_mass_fraction(imp_rec_obj, oil)

    # estimations not in the document, but needed
    add_metals(imp_rec_obj, oil)
    add_aggregate_volatile_fractions(oil)
    add_misc_fractions(imp_rec_obj, oil)
    add_k0y(imp_rec_obj, oil)

    return oil


def add_demographics(imp_rec_obj, oil):
    oil.name = imp_rec_obj.record.oil_name
    oil.adios_oil_id = imp_rec_obj.record.adios_oil_id


def add_densities(imp_rec_obj, oil):
    try:
        oil.densities = imp_rec_obj.get_densities()
        oil.api = imp_rec_obj.get_api()
    except Exception as e:
        logger.warning('Exception: record {}\n'
                       '{}\n'
                       'check for valid api and densities.'
                       .format(imp_rec_obj.record.adios_oil_id, e))


def add_viscosities(imp_rec_obj, oil):
        kvis, estimated = imp_rec_obj.aggregate_kvis()

        for k in kvis:
            oil.kvis.append(k)

        if any(estimated):
            oil.estimated.viscosities = True


def add_inert_fractions(imp_rec_obj, oil):
    '''
        Add the resin and asphaltene fractions to our oil
        This does not include the component resins & asphaltenes
    '''
    f_res, f_asph = imp_rec_obj.inert_fractions()

    oil.resins_fraction, oil.asphaltenes_fraction = f_res, f_asph


def add_distillation_cuts(imp_rec_obj, oil):
    for T_i, f_evap_i in zip(*imp_rec_obj.normalized_cut_values()):
        oil.cuts.append(Cut(vapor_temp_k=T_i, fraction=f_evap_i))


def add_component_mol_wt(imp_rec_obj, oil):
    temps = imp_rec_obj.component_temps()
    mol_wts = imp_rec_obj.component_mol_wt()
    c_types = imp_rec_obj.component_types()

    for T_i, mol_wt_i, c_type in zip(temps, mol_wts, c_types):
        oil.molecular_weights.append(MolecularWeight(sara_type=c_type,
                                                     g_mol=mol_wt_i,
                                                     ref_temp_k=T_i))


def add_component_mass_fractions(imp_rec_obj, oil):
    temps = imp_rec_obj.component_temps()
    fracs = imp_rec_obj.component_mass_fractions()
    c_types = imp_rec_obj.component_types()

    for T_i, f_i, c_type in zip(temps, fracs, c_types):
        oil.sara_fractions.append(SARAFraction(sara_type=c_type,
                                               fraction=f_i,
                                               ref_temp_k=T_i))


def add_component_densities(imp_rec_obj, oil):
    densities = imp_rec_obj.component_densities()
    fracs = imp_rec_obj.component_mass_fractions()
    temps = imp_rec_obj.component_temps()
    c_types = imp_rec_obj.component_types()

    # we need to scale our densities to match our aggregate density
    rho0_oil = imp_rec_obj.density_at_temp(273.15 + 15)
    Cf_dens = (rho0_oil / np.sum(fracs * densities))

    densities *= Cf_dens

    for T_i, rho, c_type in zip(temps, densities, c_types):
        oil.sara_densities.append(SARADensity(sara_type=c_type,
                                              density=rho,
                                              ref_temp_k=T_i))


def add_oil_water_interfacial_tension(imp_rec_obj, oil):
    (ow_st, ref_temp_k, estimated) = imp_rec_obj.oil_water_surface_tension()

    oil.oil_water_interfacial_tension_n_m = ow_st
    oil.oil_water_interfacial_tension_ref_temp_k = ref_temp_k

    oil.estimated.oil_water_interfacial_tension_n_m = estimated
    oil.estimated.oil_water_interfacial_tension_ref_temp_k = estimated


def add_oil_seawater_interfacial_tension(imp_rec_obj, oil):
    (osw_st,
     ref_temp_k,
     estimated) = imp_rec_obj.oil_seawater_surface_tension()

    oil.oil_seawater_interfacial_tension_n_m = osw_st
    oil.oil_seawater_interfacial_tension_ref_temp_k = ref_temp_k

    oil.estimated.oil_seawater_interfacial_tension_n_m = estimated
    oil.estimated.oil_seawater_interfacial_tension_ref_temp_k = estimated


def add_pour_point(imp_rec_obj, oil):
    min_k, max_k, estimated = imp_rec_obj.pour_point()

    oil.pour_point_min_k = min_k
    oil.pour_point_max_k = max_k

    oil.estimated.pour_point_min_k = estimated
    oil.estimated.pour_point_max_k = estimated


def add_flash_point(imp_rec_obj, oil):
    min_k, max_k, estimated = imp_rec_obj.flash_point()

    oil.flash_point_min_k = min_k
    oil.flash_point_max_k = max_k

    oil.estimated.flash_point_min_k = estimated
    oil.estimated.flash_point_max_k = estimated


def add_max_water_fraction_of_emulsion(imp_rec_obj, oil):
    f_w_max = imp_rec_obj.max_water_fraction_emulsion()

    oil.emulsion_water_fraction_max = f_w_max
    oil.estimated.emulsion_water_fraction_max = True


def add_bullwinkle_fractions(imp_rec_obj, oil):
    oil.bullwinkle_fraction = imp_rec_obj.bullwinkle_fraction()


def add_solubility(imp_rec_obj, oil):
    oil.solubility = imp_rec_obj.solubility()


def add_adhesion(imp_rec_obj, oil):
    oil.adhesion = imp_rec_obj.adhesion()


def add_sulphur_mass_fraction(imp_rec_obj, oil):
    oil.sulphur_fraction = imp_rec_obj.sulphur_fraction()


def add_metals(imp_rec_obj, oil):
    oil.nickel_ppm = imp_rec_obj.record.nickel
    oil.vanadium_ppm = imp_rec_obj.record.vanadium


def add_aggregate_volatile_fractions(oil):
    '''
        for this we need an oil record that already has
        the component mass fractions estimated.
    '''
    oil.saturates_fraction = np.sum([f.fraction
                                     for f in oil.sara_fractions
                                     if f.sara_type == 'Saturates'])
    oil.aromatics_fraction = np.sum([f.fraction
                                     for f in oil.sara_fractions
                                     if f.sara_type == 'Aromatics'])


def add_misc_fractions(imp_rec_obj, oil):
    oil.polars_fraction = imp_rec_obj.record.polars
    oil.benzene_fraction = imp_rec_obj.record.benzene
    oil.paraffins_fraction = imp_rec_obj.record.paraffins
    oil.wax_content_fraction = imp_rec_obj.record.wax_content


def add_k0y(imp_rec_obj, oil):
    if imp_rec_obj.record.k0y is not None:
        oil.k0y = imp_rec_obj.record.k0y
    else:
        oil.k0y = 2.02e-06


#
#
# ### Oil Quality checks
#
#

def reject_oil_if_bad(imported_rec, oil):
    '''
        Here, we have an oil in which all estimations have been made.
        We will now check the imported record and the oil object to see
        if there are any detectable flaws.
        If any flaw is detected, we will raise the OilRejected exception.
        All flaws will be compiled into a list of error messages to be passed
        into the exception.
    '''
    errors = []

    if imported_rec_was_manually_rejected(imported_rec):
        errors.append('Imported Record was manually rejected')

    if not oil_has_kvis(oil):
        errors.append('Oil has no kinematic viscosities')

    if oil_has_duplicate_cuts(oil):
        errors.append('Oil has duplicate cuts')

    if oil_has_heavy_sa_components(oil):
        errors.append('Oil has heavy SA components')

    if not oil_api_matches_density(oil):
        errors.append('Oil API does not match its density')

    if errors:
        raise OilRejected(errors, imported_rec.adios_oil_id)


def imported_rec_was_manually_rejected(imported_rec):
    '''
        This list was initially compiled to try and fix some anomalies
        that were showing up in the oil query form.

        When we update the source file that provides our imported record
        data, we should revisit this list.
        We should also revisit this list as we add methods to detect flaws
        in our oil record.
    '''
    adios_oil_id = imported_rec.adios_oil_id
    if adios_oil_id in (None,):
        return True
    return False


def oil_has_kvis(oil):
    '''
        Our oil record should have at least one kinematic viscosity when
        estimations are complete.
    '''
    if len(oil.kvis) > 0:
        return True
    else:
        return False


def oil_has_duplicate_cuts(oil):
    '''
        Some oil records have been found to have distillation cuts with
        duplicate vapor temperatures, and the fraction that should be chosen
        at that temperature is ambiguous.
    '''
    unique_temps = set([o.vapor_temp_k for o in oil.cuts])

    if len(oil.cuts) != len(unique_temps):
        return True
    else:
        return False


def oil_has_heavy_sa_components(oil):
    '''
        Some oil records have been found to have Saturate & Asphaltene
        densities that were calculated to be heavier than the Resins &
        Asphaltenes.
        This is highly improbable and indicates the record has problems
        with its imported data values.
    '''
    resin_rho = [d.density for d in oil.sara_densities
                 if d.sara_type == 'Resins']

    if len(resin_rho) == 0:
        resin_rho = 1100.0
    else:
        resin_rho = np.max((resin_rho[0], 1100.0))

    for d in oil.sara_densities:
        if d.sara_type in ('Saturates', 'Aromatics'):
            if d.density > resin_rho:
                return True

    return False


def oil_api_matches_density(oil):
    '''
        The oil API should pretty closely match its density at 15C.
    '''
    oil_estimations = OilWithEstimation(oil)

    d_0 = oil_estimations.density_at_temp(273.15 + 15)
    api = api_from_density(d_0)

    if np.isclose(oil.api, api, atol=1.0):
        return True

    logger.info('(oil.api, api_from_density) = ({}, {})'
                .format(oil.api, api))
    return False
