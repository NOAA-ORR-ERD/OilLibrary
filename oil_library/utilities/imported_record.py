'''
    Imported Oil record utility functions.

    These are functions to be used primarily for estimating oil
    properties that are contained within an imported record from the
    NOAA Filemaker oil library database.
'''

import numpy as np
from scipy.optimize import curve_fit

from ..models import KVis, Density
from .estimations import (density_from_api, api_from_density,
                          density_at_temp, specific_gravity,
                          dvis_to_kvis, kvis_at_temp,
                          resin_fraction, asphaltene_fraction,
                          cut_temps_from_api,
                          fmasses_from_cuts, fmasses_flat_dist,
                          saturate_mol_wt, aromatic_mol_wt,
                          resin_mol_wt, asphaltene_mol_wt,
                          saturate_densities, aromatic_densities,
                          resin_density, asphaltene_density,
                          saturate_mass_fraction,
                          oil_water_surface_tension_from_api,
                          pour_point_from_kvis,
                          flash_point_from_bp, flash_point_from_api,
                          bullwinkle_fraction_from_asph,
                          bullwinkle_fraction_from_api,
                          )


def lowest_temperature(obj_list):
    '''
        General utility function.

        From a list of objects containing a ref_temp_k attribute,
        return the object that has the lowest temperature
    '''
    if len(obj_list) > 0:
        return sorted(obj_list, key=lambda d: d.ref_temp_k)[0]
    else:
        return None


def closest_to_temperature(obj_list, temperature):
    '''
        General Utility Function

        From a list of objects containing a ref_temp_k attribute,
        return the object that is closest to the specified temperature
    '''
    temp_diffs = [(obj, abs(obj.ref_temp_k - temperature))
                  for obj in obj_list
                  if obj.ref_temp_k is not None]
    if len(temp_diffs) > 0:
        return sorted(temp_diffs, key=lambda d: d[1])[0][0]
    else:
        return None


def oil_density_at_temp(imported_rec, temperature, weathering=0.0):
    density_list = [d for d in imported_rec.densities
                    if (d.kg_m_3 is not None and
                        d.ref_temp_k is not None and
                        d.weathering == weathering)]
    closest_density = closest_to_temperature(density_list, temperature)

    if closest_density is not None:
        d_ref, t_ref = (closest_density.kg_m_3,
                        closest_density.ref_temp_k)
    elif imported_rec.api is not None:
        d_ref, t_ref = density_from_api(imported_rec.api)
    else:
        return None

    return density_at_temp(d_ref, t_ref, temperature)


def oil_densities(imported_rec, weathering=0.0):
    densities = [d for d in imported_rec.densities
                 if d.kg_m_3 is not None and
                 d.ref_temp_k is not None and
                 d.weathering == weathering]

    if len(densities) == 0:
        kg_m_3, ref_temp_k = density_from_api(imported_rec.api)

        densities.append(Density(kg_m_3=kg_m_3,
                                 ref_temp_k=ref_temp_k,
                                 weathering=0.0))

    return densities


def oil_api(imported_rec):
    if imported_rec.api is not None:
        return imported_rec.api
    elif len(oil_densities(imported_rec)) > 0:
        return api_from_density(oil_density_at_temp(imported_rec, 273.15 + 15))
    else:
        return None


def oil_aggregate_kvis(imported_rec):
    kvis_list = [(k.ref_temp_k, (k.m_2_s, False))
                 for k in imported_rec.kvis
                 if k.m_2_s is not None and
                 k.ref_temp_k is not None]
    dvis_list = [(d.ref_temp_k,
                  (dvis_to_kvis(d.kg_ms,
                                oil_density_at_temp(imported_rec,
                                                    d.ref_temp_k)),
                   True)
                  )
                 for d in imported_rec.dvis
                 if d.kg_ms is not None and
                 d.ref_temp_k is not None]

    agg = dict(dvis_list)
    agg.update(kvis_list)

    out_items = sorted([(i[0], i[1][0], i[1][1])
                        for i in agg.iteritems()])

    kvis_out, estimated = zip(*[(KVis(m_2_s=k, ref_temp_k=t), e)
                                for t, k, e in out_items])

    return kvis_out, estimated


def oil_kvis_at_temp(imported_rec, temp_k, weathering=0.0):
    kvis_list = [kv for kv in oil_aggregate_kvis(imported_rec)[0]
                 if (kv.weathering == weathering)]
    closest_kvis = closest_to_temperature(kvis_list, temp_k)

    if closest_kvis is not None:
        ref_kvis, ref_temp_k = (closest_kvis.m_2_s,
                                closest_kvis.ref_temp_k)
    else:
        return None

    return kvis_at_temp(ref_kvis, ref_temp_k, temp_k)


#
# Oil Distillation Fractional Properties
#
def oil_inert_fractions(imported_rec):
    f_res, f_asph = imported_rec.resins, imported_rec.asphaltenes

    if f_res is not None and f_asph is not None:
        return f_res, f_asph
    else:
        density = oil_density_at_temp(imported_rec, 288.15)
        viscosity = oil_kvis_at_temp(imported_rec, 288.15)

    if f_res is None:
        f_res = resin_fraction(density, viscosity)

    if f_asph is None:
        f_asph = asphaltene_fraction(density, viscosity, f_res)

    return f_res, f_asph


def oil_culled_cuts(imported_rec):
    prev_temp = prev_fraction = 0.0
    for c in imported_rec.cuts:
        if c.vapor_temp_k < prev_temp:
            continue

        if c.fraction < prev_fraction:
            continue

        prev_temp = c.vapor_temp_k
        prev_fraction = c.fraction

        yield c


def _linear_curve(x, a, b):
    return (a * x + b)


def _inverse_linear_curve(y, a, b):
    return (y - b) / a


def oil_normalized_cut_values(imported_rec, N=10):
    f_res, f_asph = oil_inert_fractions(imported_rec)
    culled_cuts = list(oil_culled_cuts(imported_rec))

    if len(culled_cuts) == 0:
        if imported_rec.api is not None:
            oil_api = imported_rec.api
        else:
            oil_rho = oil_density_at_temp(imported_rec, 288.15)
            oil_api = api_from_density(oil_rho)

        BP_i = cut_temps_from_api(oil_api)
        fevap_i = np.cumsum(fmasses_flat_dist(f_res, f_asph))
    else:
        BP_i, fevap_i = zip(*[(c.vapor_temp_k, c.fraction)
                              for c in culled_cuts])

    popt, _pcov = curve_fit(_linear_curve, BP_i, fevap_i)

    fevap_i = np.linspace(0.0, 1.0 - f_res - f_asph, (N * 2) + 1)[1:]
    T_i = _inverse_linear_curve(fevap_i, *popt)

    fevap_i = fevap_i.reshape(-1, 2)[:, 1]
    T_i = T_i.reshape(-1, 2)[:, 0]

    above_zero = T_i > 0.0
    T_i = T_i[above_zero]
    fevap_i = fevap_i[above_zero]

    return T_i, fevap_i


def oil_cut_temps(imported_rec, N=10):
    cut_temps, _f_evap_i = oil_normalized_cut_values(imported_rec, N)

    return cut_temps


def oil_cut_fmasses(imported_rec, N=10):
    _cut_temps, f_evap_i = oil_normalized_cut_values(imported_rec, N)

    return fmasses_from_cuts(f_evap_i)


def oil_cut_temps_fmasses(imported_rec, N=10):
    cut_temps, f_evap_i = oil_normalized_cut_values(imported_rec, N)

    return cut_temps, fmasses_from_cuts(f_evap_i)


def oil_component_temps(imported_rec, N=10):
    cut_temps = oil_cut_temps(imported_rec, N)

    component_temps = np.append([1015.0, 1015.0],
                                zip(cut_temps, cut_temps))

    return np.roll(component_temps, -2)


def oil_component_types(imported_rec, N=10):
    T_i = oil_component_temps(imported_rec, N)

    types_out = ['Saturates', 'Aromatics'] * (len(T_i) / 2 - 1)
    types_out += ['Resins', 'Asphaltenes']

    return types_out


def oil_component_mol_wt(imported_rec, N=10):
    cut_temps = oil_cut_temps(imported_rec, N)

    return estimate_component_mol_wt(cut_temps)


def estimate_component_mol_wt(boiling_points):
    mw_list = np.append([resin_mol_wt(), asphaltene_mol_wt()],
                        zip(saturate_mol_wt(boiling_points),
                            aromatic_mol_wt(boiling_points)))

    return np.roll(mw_list, -2)


def oil_component_densities(imported_rec, N=10):
    cut_temps = oil_cut_temps(imported_rec, N)

    return estimate_component_densities(cut_temps)


def estimate_component_densities(boiling_points):
    rho_list = np.append([resin_density(), asphaltene_density()],
                         zip(saturate_densities(boiling_points),
                             aromatic_densities(boiling_points)))

    return np.roll(rho_list, -2)


def oil_component_specific_gravity(imported_rec, N=10):
    rho_list = oil_component_densities(imported_rec, N)

    return specific_gravity(rho_list)


def oil_component_mass_fractions(imported_rec):
    f_res, f_asph = oil_inert_fractions(imported_rec)
    cut_temps, fmass_i = oil_cut_temps_fmasses(imported_rec)

    f_sat_i = fmass_i / 2.0
    f_arom_i = fmass_i / 2.0

    for _i in range(20):
        f_sat_i, f_arom_i = verify_cut_fractional_masses(fmass_i, cut_temps,
                                                         f_sat_i, f_arom_i)

    mf_list = np.append([f_res, f_asph],
                        zip(f_sat_i, f_arom_i))

    return np.roll(mf_list, -2)


def verify_cut_fractional_masses(fmass_i, T_i, f_sat_i, f_arom_i):
    '''
        Assuming a distillate mass with a boiling point T_i,
        We propose what the component fractional masses might be.

        We calculate what the molecular weights and specific gravities
        likely are for saturates and aromatics at that temperature.

        Then we use these values, in combination with our proposed
        component fractional masses, to produce a proposed average
        molecular weight and specific gravity for the distillate.

        We then use Riazi's formulas (3.77 and 3.78) to obtain the
        saturate and aromatic fractional masses that represent our
        averaged molecular weight and specific gravity.

        If our proposed component mass fractions were correct (or at least
        consistent with Riazi's findings), then our computed component
        mass fractions should match.

        If they don't match, then the computed component fractions should
        at least be a closer approximation to that which is consistent
        with Riazi.

        It is intended that we run this function iteratively to obtain a
        successively approximated value for f_sat_i and f_arom_i.
    '''
    assert np.allclose(fmass_i, f_sat_i + f_arom_i)

    M_w_sat_i = saturate_mol_wt(T_i)
    M_w_arom_i = aromatic_mol_wt(T_i)

    M_w_avg_i = (M_w_sat_i * f_sat_i / fmass_i +
                 M_w_arom_i * f_arom_i / fmass_i)

    # estimate specific gravity
    rho_sat_i = saturate_densities(T_i)
    SG_sat_i = specific_gravity(rho_sat_i)

    rho_arom_i = aromatic_densities(T_i)
    SG_arom_i = specific_gravity(rho_arom_i)

    SG_avg_i = (SG_sat_i * f_sat_i / fmass_i +
                SG_arom_i * f_arom_i / fmass_i)

    f_sat_i = saturate_mass_fraction(fmass_i, M_w_avg_i, SG_avg_i, T_i)
    f_arom_i = fmass_i - f_sat_i

    # TODO: Riazi states that this formula only works with
    #       molecular weights less than 200.  So we will punt
    #       with Bill's recommendation of 50/50 in those cases.
    #       In the future we might be able to figure out how
    #       to implement CPPF eqs. 3.81 and 3.82
    above_200 = M_w_avg_i > 200.0
    try:
        f_sat_i[above_200] = fmass_i[above_200] / 2.0
        f_arom_i[above_200] = fmass_i[above_200] / 2.0
    except TypeError:
        # numpy array assignment failed, try a scalar assignment
        if above_200:
            f_sat_i = fmass_i / 2.0
            f_arom_i = fmass_i / 2.0

    return f_sat_i, f_arom_i


def oil_water_surface_tension(imported_rec):
    if (imported_rec.oil_water_interfacial_tension_n_m is not None and
            imported_rec.oil_water_interfacial_tension_ref_temp_k is not None):
        ow_st = imported_rec.oil_water_interfacial_tension_n_m
        ref_temp_k = imported_rec.oil_water_interfacial_tension_ref_temp_k

        return ow_st, ref_temp_k, False
    elif imported_rec.api is not None:
        ow_st = oil_water_surface_tension_from_api(imported_rec.api)

        return ow_st, 273.15 + 15, True
    else:
        est_api = api_from_density(oil_density_at_temp(imported_rec, 288.15))
        ow_st = oil_water_surface_tension_from_api(est_api)

        return ow_st, 273.15 + 15, True


def oil_seawater_surface_tension(imported_rec):
    if imported_rec.oil_seawater_interfacial_tension_n_m is not None:
        osw_st = imported_rec.oil_seawater_interfacial_tension_n_m
        ref_temp_k = imported_rec.oil_seawater_interfacial_tension_ref_temp_k

        return osw_st, ref_temp_k, False
    else:
        # we currently don't have an estimation for this one.
        return None, None, False


def oil_pour_point(imported_rec):
    min_k = max_k = None
    estimated = False

    if (imported_rec.pour_point_min_k is not None or
            imported_rec.pour_point_max_k is not None):
        # we have values to copy over
        min_k = imported_rec.pour_point_min_k
        max_k = imported_rec.pour_point_max_k
    else:
        lowest_kvis = lowest_temperature(oil_aggregate_kvis(imported_rec)[0])
        max_k = pour_point_from_kvis(lowest_kvis.m_2_s, lowest_kvis.ref_temp_k)
        estimated = True

    return min_k, max_k, estimated


def oil_flash_point(imported_rec):
    min_k = max_k = None
    estimated = False

    if (imported_rec.flash_point_min_k is not None or
            imported_rec.flash_point_max_k is not None):
        min_k = imported_rec.flash_point_min_k
        max_k = imported_rec.flash_point_max_k
    elif len(list(oil_culled_cuts(imported_rec))) > 2:
        cut_temps = oil_cut_temps(imported_rec)
        max_k = flash_point_from_bp(cut_temps[0])
        estimated = True
    elif imported_rec.api is not None:
        max_k = flash_point_from_api(imported_rec.api)
        estimated = True
    else:
        est_api = api_from_density(oil_density_at_temp(imported_rec, 288.15))
        max_k = flash_point_from_api(est_api)
        estimated = True

    return min_k, max_k, estimated


def oil_max_water_fraction_emulsion(imported_rec):
    if imported_rec.product_type == 'Crude':
        return 0.9
    else:
        return 0.0


def oil_bullwinkle_fraction(imported_rec):
    _f_res, f_asph = oil_inert_fractions(imported_rec)

    if f_asph > 0.0:
        return bullwinkle_fraction_from_asph(f_asph)
    elif imported_rec.api is not None:
        return bullwinkle_fraction_from_api(imported_rec.api)
    else:
        est_api = api_from_density(oil_density_at_temp(imported_rec, 288.15))
        return bullwinkle_fraction_from_api(est_api)


def oil_solubility(imported_rec):
    '''
        Note: imported records do not have a solubility attribute.
              We just return a default.
    '''
    return 0.0


def oil_adhesion(imported_rec):
    if imported_rec.adhesion is not None:
        return imported_rec.adhesion
    else:
        return 0.035


def oil_sulphur_fraction(imported_rec):
    if imported_rec.sulphur is not None:
        return imported_rec.sulphur
    else:
        return 0.0
