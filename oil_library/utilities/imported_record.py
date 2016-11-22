'''
    Imported Oil record utility functions.

    These are functions to be used primarily for estimating oil
    properties that are contained within an imported record from the
    NOAA Filemaker oil library database.
'''

import numpy as np
from scipy.optimize import curve_fit

from ..models import KVis, DVis, Density
import estimations as est


def _linear_curve(x, a, b):
    return (a * x + b)


def clamp(x, M, zeta=0.03):
    '''
        We make use of a generalized logistic function or Richard's curve
        to generate a linear function that is clamped at x == M.
        We make use of a zeta value to tune the parameters nu, resulting in a
        smooth transition as we cross the M boundary.
    '''
    return (x -
            (x / (1.0 + np.e ** (-15 * (x - M))) ** (1.0 / (1 + zeta))) +
            (M / (1.0 + np.e ** (-15 * (x - M))) ** (1.0 / (1 - zeta))))


def _inverse_linear_curve(y, a, b, M, zeta=0.12):
    y_c = clamp(y, M, zeta)

    return (y_c - b) / a


class ImportedRecordWithEstimation(object):
    def __init__(self, imported_rec):
        self.record = imported_rec

    @classmethod
    def lowest_temperature(cls, obj_list):
        '''
            General utility function.

            From a list of objects containing a ref_temp_k attribute,
            return the object that has the lowest temperature
        '''
        if len(obj_list) > 0:
            return sorted(obj_list, key=lambda d: d.ref_temp_k)[0]
        else:
            return None

    @classmethod
    def closest_to_temperature(cls, obj_list, temperature):
        '''
            General Utility Function

            From a list of objects containing a ref_temp_k attribute,
            return the object that is closest to the specified temperature(s)
        '''
        temp_diffs = [(obj, abs(obj.ref_temp_k - temperature))
                      for obj in obj_list
                      if obj.ref_temp_k is not None]

        if len(temp_diffs) > 0:
            try:
                # treat like numpy array as a default
                objs, temp_diff_arr = zip(*[td for td in temp_diffs])
                temp_diff_arr = np.vstack([ta.reshape(-1)
                                           for ta in temp_diff_arr])

                return [objs[i] for i in np.argmin(temp_diff_arr, 0)]
            except (ValueError, AttributeError):
                # treat like a scalar
                return sorted(temp_diffs, key=lambda d: d[1])[0][0]
        else:
            return None

    def culled_measurement(self, attr_name, non_null_attrs):
        '''
            General utility function for returning a common class of
            one-to-many Oil record relationships.

            A certain grouping of sub-objects of the Oil class, such as
            Density, KVis, and DVis, contain a measured value, a reference
            temperature at which the value was measured, and a measure of
            how much the oil was weathered.

            We iterate over this list of sub-objects, and only return the
            ones that have a non-null measured value and reference temperature.
            The weathering property is optional, and will default to 0.0.
        '''
        if hasattr(self.record, attr_name):
            obj_list = [o for o in getattr(self.record, attr_name)
                        if all([(getattr(o, attr) is not None)
                                for attr in non_null_attrs])]

            for o in obj_list:
                if o.weathering is None:
                    o.weathering = 0.0
        else:
            obj_list = []

        return obj_list

    def culled_densities(self):
        return self.culled_measurement('densities', ['kg_m_3', 'ref_temp_k'])

    def culled_kvis(self):
        return self.culled_measurement('kvis', ['m_2_s', 'ref_temp_k'])

    def culled_dvis(self):
        return self.culled_measurement('dvis', ['kg_ms', 'ref_temp_k'])

    def density_at_temp(self, temperature=288.15, weathering=0.0):
        if hasattr(temperature, '__iter__'):
            # we like to deal with numpy arrays as opposed to simple iterables
            temperature = np.array(temperature)

        density_list = [d for d in self.culled_densities()
                        if d.weathering == weathering]
        closest_density = self.closest_to_temperature(density_list,
                                                      temperature)

        if closest_density is not None:
            try:
                # treat as a list
                d_ref, ref_temp_k = zip(*[(d.kg_m_3, d.ref_temp_k)
                                          for d in closest_density])

                if len(closest_density) > 1:
                    d_ref, ref_temp_k = (np.array(d_ref)
                                         .reshape(temperature.shape),
                                         np.array(ref_temp_k)
                                         .reshape(temperature.shape))
                else:
                    d_ref, ref_temp_k = d_ref[0], ref_temp_k[0]
            except TypeError:
                # treat as a scalar
                d_ref, ref_temp_k = (closest_density.kg_m_3,
                                     closest_density.ref_temp_k)
        elif self.record.api is not None:
            d_ref, ref_temp_k = est.density_from_api(self.record.api)
        else:
            return None

        return est.density_at_temp(d_ref, ref_temp_k, temperature)

    def get_densities(self, weathering=0.0):
        densities = [d for d in self.culled_densities()
                     if d.weathering == weathering]

        if len(densities) == 0:
            kg_m_3, ref_temp_k = est.density_from_api(self.record.api)

            densities.append(Density(kg_m_3=kg_m_3,
                                     ref_temp_k=ref_temp_k,
                                     weathering=0.0))

        return densities

    def get_api(self):
        if self.record.api is not None:
            return self.record.api
        elif len(self.get_densities()) > 0:
            return est.api_from_density(self.density_at_temp(273.15 + 15))
        else:
            return None

    def non_redundant_dvis(self):
        kvis_dict = dict([((k.weathering, k.ref_temp_k), k.m_2_s)
                          for k in self.culled_kvis()])
        dvis_dict = dict([((d.weathering, d.ref_temp_k), d.kg_ms)
                          for d in self.culled_dvis()])

        non_redundant_keys = set(dvis_dict.keys()).difference(kvis_dict.keys())
        for k in sorted(non_redundant_keys):
            yield DVis(ref_temp_k=k[1],
                       weathering=k[0],
                       kg_ms=dvis_dict[k])

    def dvis_to_kvis(self, kg_ms, ref_temp_k):
        density = self.density_at_temp(ref_temp_k)
        if density is None:
            return None
        else:
            return kg_ms / density

    @classmethod
    def dvis_obj_to_kvis_obj(cls, dvis_obj, density):
        viscosity = est.dvis_to_kvis(dvis_obj.kg_ms, density)

        return KVis(ref_temp_k=dvis_obj.ref_temp_k,
                    weathering=dvis_obj.weathering,
                    m_2_s=viscosity)

    def aggregate_kvis(self):
        kvis_list = [(k.ref_temp_k, (k.m_2_s, False))
                     for k in self.culled_kvis()]

        if hasattr(self.record, 'dvis'):
            dvis_list = [(d.ref_temp_k,
                          (est.dvis_to_kvis(d.kg_ms,
                                            self.density_at_temp(d.ref_temp_k)
                                            ),
                           True)
                          )
                         for d in list(self.non_redundant_dvis())]

            agg = dict(dvis_list)
            agg.update(kvis_list)
        else:
            agg = dict(kvis_list)

        out_items = sorted([(i[0], i[1][0], i[1][1])
                            for i in agg.iteritems()])

        kvis_out, estimated = zip(*[(KVis(m_2_s=k, ref_temp_k=t), e)
                                    for t, k, e in out_items])

        return kvis_out, estimated

    def kvis_at_temp(self, temp_k=288.15, weathering=0.0):
        if hasattr(temp_k, '__iter__'):
            # we like to deal with numpy arrays as opposed to simple iterables
            temp_k = np.array(temp_k)

        kvis_list = [kv for kv in self.aggregate_kvis()[0]
                     if (kv.weathering == weathering)]
        closest_kvis = self.closest_to_temperature(kvis_list, temp_k)

        if closest_kvis is not None:
            try:
                # treat as a list
                ref_kvis, ref_temp_k = zip(*[(kv.m_2_s, kv.ref_temp_k)
                                             for kv in closest_kvis])
                if len(closest_kvis) > 1:
                    ref_kvis = np.array(ref_kvis).reshape(temp_k.shape)
                    ref_temp_k = np.array(ref_temp_k).reshape(temp_k.shape)
                else:
                    ref_kvis, ref_temp_k = ref_kvis[0], ref_temp_k[0]
            except TypeError:
                # treat as a scalar
                ref_kvis, ref_temp_k = (closest_kvis.m_2_s,
                                        closest_kvis.ref_temp_k)
        else:
            return None

        return est.kvis_at_temp(ref_kvis, ref_temp_k, temp_k)

    #
    # Oil Distillation Fractional Properties
    #
    def inert_fractions(self):
        try:
            f_res, f_asph = self.record.resins, self.record.asphaltenes
        except AttributeError:
            f_res, f_asph = (self.record.resins_fraction,
                             self.record.asphaltenes_fraction)

        if f_res is not None and f_asph is not None:
            return f_res, f_asph
        else:
            density = self.density_at_temp(288.15)
            viscosity = self.kvis_at_temp(288.15)

        if f_res is None:
            f_res = est.resin_fraction(density, viscosity)

        if f_asph is None:
            f_asph = est.asphaltene_fraction(density, viscosity, f_res)

        return f_res, f_asph

    def culled_cuts(self):
        prev_temp = prev_fraction = 0.0
        for c in self.record.cuts:
            if c.vapor_temp_k < prev_temp:
                continue

            if c.fraction < prev_fraction:
                continue

            prev_temp = c.vapor_temp_k
            prev_fraction = c.fraction

            yield c

    def normalized_cut_values(self, N=10):
        f_res, f_asph = self.inert_fractions()
        cuts = list(self.culled_cuts())

        if len(cuts) == 0:
            if self.record.api is not None:
                oil_api = self.record.api
            else:
                oil_rho = self.density_at_temp(288.15)
                oil_api = est.api_from_density(oil_rho)

            BP_i = est.cut_temps_from_api(oil_api)
            fevap_i = np.cumsum(est.fmasses_flat_dist(f_res, f_asph))
        else:
            BP_i, fevap_i = zip(*[(c.vapor_temp_k, c.fraction) for c in cuts])

        popt, _pcov = curve_fit(_linear_curve, BP_i, fevap_i)
        f_cutoff = _linear_curve(732.0, *popt)  # center of asymptote (< 739)
        popt = popt.tolist() + [f_cutoff]

        fevap_i = np.linspace(0.0, 1.0 - f_res - f_asph, (N * 2) + 1)[1:]
        T_i = _inverse_linear_curve(fevap_i, *popt)

        fevap_i = fevap_i.reshape(-1, 2)[:, 1]
        T_i = T_i.reshape(-1, 2)[:, 0]

        above_zero = T_i > 0.0
        T_i = T_i[above_zero]
        fevap_i = fevap_i[above_zero]

        return T_i, fevap_i

    def get_cut_temps(self, N=10):
        cut_temps, _f_evap_i = self.normalized_cut_values(N)

        return cut_temps

    def get_cut_fmasses(self, N=10):
        _cut_temps, f_evap_i = self.normalized_cut_values(N)

        return est.fmasses_from_cuts(f_evap_i)

    def get_cut_temps_fmasses(self, N=10):
        cut_temps, f_evap_i = self.normalized_cut_values(N)

        return cut_temps, est.fmasses_from_cuts(f_evap_i)

    def component_temps(self, N=10):
        cut_temps = self.get_cut_temps(N)

        component_temps = np.append([1015.0, 1015.0],
                                    zip(cut_temps, cut_temps))

        return np.roll(component_temps, -2)

    def component_types(self, N=10):
        T_i = self.component_temps(N)

        types_out = ['Saturates', 'Aromatics'] * (len(T_i) / 2 - 1)
        types_out += ['Resins', 'Asphaltenes']

        return types_out

    def component_mol_wt(self, N=10):
        cut_temps = self.get_cut_temps(N)

        return self.estimate_component_mol_wt(cut_temps)

    @classmethod
    def estimate_component_mol_wt(cls, boiling_points):
        mw_list = np.append([est.resin_mol_wt(), est.asphaltene_mol_wt()],
                            zip(est.saturate_mol_wt(boiling_points),
                                est.aromatic_mol_wt(boiling_points)))

        return np.roll(mw_list, -2)

    def component_densities(self, N=10):
        cut_temps = self.get_cut_temps(N)

        return self.estimate_component_densities(cut_temps)

    @classmethod
    def estimate_component_densities(cls, boiling_points):
        rho_list = np.append([est.resin_density(), est.asphaltene_density()],
                             zip(est.saturate_densities(boiling_points),
                                 est.aromatic_densities(boiling_points)))

        return np.roll(rho_list, -2)

    def component_specific_gravity(self, N=10):
        rho_list = self.component_densities(N)

        return est.specific_gravity(rho_list)

    def component_mass_fractions(self):
        f_res, f_asph = self.inert_fractions()
        cut_temps, fmass_i = self.get_cut_temps_fmasses()

        f_sat_i = fmass_i / 2.0
        f_arom_i = fmass_i / 2.0

        for _i in range(20):
            f_sat_i, f_arom_i = self.verify_cut_fractional_masses(fmass_i,
                                                                  cut_temps,
                                                                  f_sat_i,
                                                                  f_arom_i)

        mf_list = np.append([f_res, f_asph],
                            zip(f_sat_i, f_arom_i))

        return np.roll(mf_list, -2)

    @classmethod
    def verify_cut_fractional_masses(cls, fmass_i, T_i, f_sat_i, f_arom_i,
                                     prev_f_sat_i=None):
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

        M_w_sat_i = est.saturate_mol_wt(T_i)
        M_w_arom_i = est.aromatic_mol_wt(T_i)

        M_w_avg_i = (M_w_sat_i * f_sat_i / fmass_i +
                     M_w_arom_i * f_arom_i / fmass_i)

        # estimate specific gravity
        rho_sat_i = est.saturate_densities(T_i)
        SG_sat_i = est.specific_gravity(rho_sat_i)

        rho_arom_i = est.aromatic_densities(T_i)
        SG_arom_i = est.specific_gravity(rho_arom_i)

        SG_avg_i = (SG_sat_i * f_sat_i / fmass_i +
                    SG_arom_i * f_arom_i / fmass_i)

        f_sat_i = est.saturate_mass_fraction(fmass_i, M_w_avg_i, SG_avg_i, T_i)
        f_arom_i = fmass_i - f_sat_i

        # Note:   Riazi states that eqs. 3.77 and 3.78 only work with
        #         molecular weights less than 200. In those cases,
        #         Chris would like to use the last fraction in which
        #         the molecular weight was less than 200 instead
        #         of just guessing 50/50
        # TODO:   In the future we might be able to figure out how
        #         to implement CPPF eqs. 3.81 and 3.82, which take
        #         care of cases where molecular weight is greater
        #         than 200.
        above_200 = M_w_avg_i > 200.0
        try:
            if np.any(above_200):
                if np.all(above_200):
                    # once in awhile we get a record where all molecular
                    # weights are over 200, In this case, we have no
                    # choice but to use the 50/50 scale
                    scale_sat_i = 0.5
                else:
                    last_good_sat_i = f_sat_i[above_200 ^ True][-1]
                    last_good_fmass_i = fmass_i[above_200 ^ True][-1]

                    scale_sat_i = last_good_sat_i / last_good_fmass_i

                f_sat_i[above_200] = fmass_i[above_200] * scale_sat_i
                f_arom_i[above_200] = fmass_i[above_200] * (1.0 - scale_sat_i)
        except TypeError:
            # numpy array assignment failed, try a scalar assignment
            if above_200:
                # for a scalar, the only way to determine the last
                # successfully computed f_sat_i is to pass it in
                if prev_f_sat_i is None:
                    scale_sat_i = 0.5
                else:
                    scale_sat_i = prev_f_sat_i / fmass_i

                f_sat_i = fmass_i * scale_sat_i
                f_arom_i = fmass_i * (1.0 - scale_sat_i)

        return f_sat_i, f_arom_i

    def oil_water_surface_tension(self):
        if (self.record.oil_water_interfacial_tension_n_m is not None and
                self.record.oil_water_interfacial_tension_ref_temp_k is not None):
            ow_st = self.record.oil_water_interfacial_tension_n_m
            ref_temp_k = self.record.oil_water_interfacial_tension_ref_temp_k

            return ow_st, ref_temp_k, False
        elif self.record.api is not None:
            ow_st = est.oil_water_surface_tension_from_api(self.record.api)

            return ow_st, 273.15 + 15, True
        else:
            est_api = est.api_from_density(self.density_at_temp(288.15))
            ow_st = est.oil_water_surface_tension_from_api(est_api)

            return ow_st, 273.15 + 15, True

    def oil_seawater_surface_tension(self):
        if self.record.oil_seawater_interfacial_tension_n_m is not None:
            osw_st = self.record.oil_seawater_interfacial_tension_n_m
            ref_temp_k = self.record.oil_seawater_interfacial_tension_ref_temp_k

            return osw_st, ref_temp_k, False
        else:
            # we currently don't have an estimation for this one.
            return None, None, False

    def pour_point(self):
        min_k = max_k = None
        estimated = False

        if (self.record.pour_point_min_k is not None or
                self.record.pour_point_max_k is not None):
            # we have values to copy over
            min_k = self.record.pour_point_min_k
            max_k = self.record.pour_point_max_k
        else:
            lowest_kvis = self.lowest_temperature(self.aggregate_kvis()[0])
            max_k = est.pour_point_from_kvis(lowest_kvis.m_2_s,
                                             lowest_kvis.ref_temp_k)
            estimated = True

        return min_k, max_k, estimated

    def flash_point(self):
        min_k = max_k = None
        estimated = False

        if (self.record.flash_point_min_k is not None or
                self.record.flash_point_max_k is not None):
            min_k = self.record.flash_point_min_k
            max_k = self.record.flash_point_max_k
        elif len(list(self.culled_cuts())) > 2:
            cut_temps = self.get_cut_temps()
            max_k = est.flash_point_from_bp(cut_temps[0])
            estimated = True
        elif self.record.api is not None:
            max_k = est.flash_point_from_api(self.record.api)
            estimated = True
        else:
            est_api = est.api_from_density(self.density_at_temp(288.15))
            max_k = est.flash_point_from_api(est_api)
            estimated = True

        return min_k, max_k, estimated

    def max_water_fraction_emulsion(self):
        if self.record.product_type == 'Crude':
            return 0.9
        else:
            return 0.0

    def bullwinkle_fraction(self):
        _f_res, f_asph = self.inert_fractions()

        if f_asph > 0.0:
            return est.bullwinkle_fraction_from_asph(f_asph)
        elif self.record.api is not None:
            return est.bullwinkle_fraction_from_api(self.record.api)
        else:
            est_api = est.api_from_density(self.density_at_temp(288.15))
            return est.bullwinkle_fraction_from_api(est_api)

    def solubility(self):
        '''
            Note: imported records do not have a solubility attribute.
                  We just return a default.
        '''
        return 0.0

    def adhesion(self):
        if self.record.adhesion is not None:
            return self.record.adhesion
        else:
            return 0.035

    def sulphur_fraction(self):
        if self.record.sulphur is not None:
            return self.record.sulphur
        else:
            return 0.0
