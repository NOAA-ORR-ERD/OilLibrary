'''
    Imported Oil record utility functions.

    These are functions to be used primarily for estimating oil
    properties that are contained within an imported record from the
    NOAA Filemaker oil library database.
'''

import numpy as np
from scipy.optimize import curve_fit

from ..models import KVis, DVis, Density

from ..utilities import estimations as est


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
    def closest_to_temperature(cls, obj_list, temperature, num=1):
        '''
            General Utility Function

            From a list of objects containing a ref_temp_k attribute,
            return the object(s) that are closest to the specified
            temperature(s)

            We accept only a scalar temperature or a sequence of temperatures
        '''
        if hasattr(temperature, '__iter__'):
            # we like to deal with numpy arrays as opposed to simple iterables
            temperature = np.array(temperature)

        # our requested number of objs can have a range [0 ... listsize-1]
        if num >= len(obj_list):
            num = len(obj_list) - 1

        temp_diffs = np.array([abs(obj.ref_temp_k - temperature)
                               for obj in obj_list]).T

        if len(obj_list) <= 1:
            return obj_list
        else:
            # we probably don't really need this for such a short list,
            # but we use a numpy 'introselect' partial sort method for speed
            try:
                # temp_diffs for sequence of temps
                closest_idx = np.argpartition(temp_diffs, num)[:, :num]
            except IndexError:
                # temp_diffs for single temp
                closest_idx = np.argpartition(temp_diffs, num)[:num]

            try:
                # sequence of temperatures result
                closest = [sorted([obj_list[i] for i in r],
                                  key=lambda x: x.ref_temp_k)
                           for r in closest_idx]
            except TypeError:
                # single temperature result
                closest = sorted([obj_list[i] for i in closest_idx],
                                 key=lambda x: x.ref_temp_k)

            return closest

    @classmethod
    def bounding_temperatures(cls, obj_list, temperature):
        '''
            General Utility Function

            From a list of objects containing a ref_temp_k attribute,
            return the object(s) that are closest to the specified
            temperature(s)
            specifically:
            - we want the ones that immediately bound our temperature.
            - if our temperature is high and out of bounds of the temperatures
              in our obj_list, then we return a range containing only the
              highest temperature.
            - if our temperature is low and out of bounds of the temperatures
              in our obj_list, then we return a range containing only the
              lowest temperature.

            We accept only a scalar temperature or a sequence of temperatures
        '''
        temperature = np.array(temperature)

        if len(obj_list) <= 1:
            # range where the lowest and highest are basically the same.
            return [obj_list * 2]
        else:
            geq_temps = temperature.reshape(-1, 1) >= [obj.ref_temp_k
                                                       for obj in obj_list]
            high_and_oob = np.all(geq_temps, axis=1)
            low_and_oob = np.all(geq_temps ^ True, axis=1)

            rho_idxs0 = np.argmin(geq_temps, axis=1)
            rho_idxs0[rho_idxs0 > 0] -= 1
            rho_idxs0[high_and_oob] = len(obj_list) - 1

            rho_idxs1 = (rho_idxs0 + 1).clip(0, len(obj_list) - 1)
            rho_idxs1[low_and_oob] = 0

            return zip([obj_list[i] for i in rho_idxs0],
                       [obj_list[i] for i in rho_idxs1])

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

    def get_densities(self, weathering=0.0):
        '''
            return a list of densities for the oil at a specified state
            of weathering.
            We include the API as a density if:
            - the specified weathering is 0
            - the culled list of densities does not contain a measurement
              at 15C
        '''
        densities = [d for d in self.culled_densities()
                     if d.weathering == weathering]

        if (weathering == 0.0 and
                self.record.api is not None and
                len([d for d in densities if d.ref_temp_k == 288.15]) == 0):
            kg_m_3, ref_temp_k = est.density_from_api(self.record.api)

            densities.append(Density(kg_m_3=kg_m_3,
                                     ref_temp_k=ref_temp_k,
                                     weathering=0.0))

        return sorted(densities, key=lambda d: d.ref_temp_k)

    def density_at_temp(self, temperature=288.15, weathering=0.0):
        '''
            Get the oil density at a temperature or temperatures.

            Note: there is a catch-22 which prevents us from getting
                  the min_temp in all casees:
                  - to estimate pour point, we need viscosities
                  - if we need to convert dynamic viscosities to
                    kinematic, we need density at 15C
                  - to estimate density at temp, we need to estimate pour point
                  - ...and then we recurse
                  For this case we need to make an exception.
            Note: If we have a pour point that is higher than one or more
                  of our reference temperatures, then the lowest reference
                  temperature will become our minimum temperature.
        '''
        densities = self.get_densities(weathering=weathering)

        # set the minimum temperature to be the oil's pour point
        if (self.record.pour_point_min_k is None and
                self.record.pour_point_max_k is None and
                hasattr(self.record, 'dvis') and
                len(self.record.dvis) > 0):
            min_temp = 0.0  # effectively no restriction
        else:
            min_temp = np.min([d.ref_temp_k for d in densities] +
                              [pp for pp in self.pour_point()[:2]
                               if pp is not None])

        if hasattr(temperature, '__iter__'):
            temperature = np.clip(temperature, min_temp, 1000.0)
        else:
            temperature = min_temp if temperature < min_temp else temperature

        ref_density, ref_temp_k = self._get_reference_densities(densities,
                                                                temperature)
        k_rho_t = self._vol_expansion_coeff(densities, temperature)

        rho_t = est.density_at_temp(ref_density, ref_temp_k,
                                    temperature, k_rho_t)
        if len(rho_t) == 1:
            return rho_t[0]
        else:
            return rho_t

    def _get_reference_densities(self, densities, temperature):
        '''
            Given a temperature, we return the best measured density,
            and its reference temperature, to be used in calculation.

            For our purposes, it is the density closest to the given
            temperature.
        '''
        closest_densities = self.bounding_temperatures(densities, temperature)

        try:
            # sequence of ranges
            density_values = np.array([[d.kg_m_3 for d in r]
                                       for r in closest_densities])
            ref_temp_values = np.array([[d.ref_temp_k for d in r]
                                        for r in closest_densities])
            greater_than = np.all((temperature > ref_temp_values.T).T, axis=1)
            density_values[greater_than, 0] = density_values[greater_than, 1]
            ref_temp_values[greater_than, 0] = ref_temp_values[greater_than, 1]

            return density_values[:, 0], ref_temp_values[:, 0]
        except TypeError:
            # single range
            density_values = np.array([d.kg_m_3 for d in closest_densities])
            ref_temp_values = np.array([d.ref_temp_k
                                        for d in closest_densities])

            if np.all(temperature > ref_temp_values):
                return density_values[1], ref_temp_values[1]
            else:
                return density_values[0], ref_temp_values[0]

    def _vol_expansion_coeff(self, densities, temperature):
        closest_densities = self.bounding_temperatures(densities, temperature)

        temperature = np.array(temperature)
        closest_values = np.array([[(d.kg_m_3, d.ref_temp_k)
                                    for d in r]
                                   for r in closest_densities])

        args_list = [[t for d in v for t in d]
                     for v in closest_values]
        k_rho_t = np.array([est.vol_expansion_coeff(*args)
                            for args in args_list])

        greater_than = np.all((temperature > closest_values[:, :, 1].T).T,
                              axis=1)
        less_than = np.all((temperature < closest_values[:, :, 1].T).T,
                           axis=1)

        if self.record.api > 30:
            k_rho_default = 0.0009
        else:
            k_rho_default = 0.0008

        k_rho_t[greater_than | less_than] = k_rho_default

        if k_rho_t.shape[0] == 1:
            return k_rho_t[0]
        else:
            return k_rho_t

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
        closest_kvis = self.closest_to_temperature(kvis_list, temp_k)[0]

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
        return self._adios2_bullwinkle_fraction()

    def _adios3_bullwinkle_fraction(self):
        '''
            This is the algorithm described in Bill's Oil Properties
            Estimation document.  In the document, I think it was intended
            to be the same as what Adios2 uses.  However the Adios2 c++ file
            OilInitialize.cpp contains steps that are missing here and in the
            document.
        '''
        _f_res, f_asph = self.inert_fractions()

        if f_asph > 0.0:
            return est.bullwinkle_fraction_from_asph(f_asph)
        else:
            return est.bullwinkle_fraction_from_api(self.get_api())

    def _adios2_bullwinkle_fraction(self):
        '''
            This is the mass fraction that must evaporate or dissolve before
            stable emulsification can begin.
            - For this estimation, we depend on an oil object with a valid
              asphaltene fraction or a valid api
            - This is a scalar value calculated with a reference temperature
              of 15C
            - For right now we are referencing the Adios2 code file
              OilInitialize.cpp, function CAdiosData::Bullwinkle(void)
        '''
        if self.record.product_type == "Refined":
            bullwinkle_fraction = 1.0
        elif self.record.emuls_constant_max is not None:
            bullwinkle_fraction = self.record.emuls_constant_max
        else:
            # product type is crude
            Ni = (self.record.nickel
                  if self.record.nickel is not None
                  else 0.0)
            Va = (self.record.vanadium
                  if self.record.vanadium is not None
                  else 0.0)

            _f_res, f_asph = self.inert_fractions()
            oil_api = self.get_api()

            if (Ni > 0.0 and Va > 0.0 and Ni + Va > 15.0):
                bullwinkle_fraction = 0.0
            elif f_asph > 0.0:
                # Bullvalue = 0.32 - 3.59 * f_Asph
                bullwinkle_fraction = 0.20219 - 0.168 * np.log10(f_asph)
                bullwinkle_fraction = np.clip(bullwinkle_fraction, 0.0, 0.303)
            elif oil_api < 26.0:
                bullwinkle_fraction = 0.08
            elif oil_api > 50.0:
                bullwinkle_fraction = 0.303
            else:
                bullwinkle_fraction = (-1.038 -
                                       0.78935 * np.log10(1.0 / oil_api))

            bullwinkle_fraction = self._adios2_new_bull_calc(bullwinkle_fraction)

        return bullwinkle_fraction

    def _adios2_new_bull_calc(self, bullwinkle_fraction):
        '''
            From the Adios2 c++ file OilInitialize.cpp, there is functionality
            inside the function CAdiosData::Bullwinkle() which is annotated
            in the code as 'new bull calc'.

            It uses the following definitions:
            - TG, Documented as the value 'dT/df - evaporation'.
                  I can only assume this is the initial fractional rate of
                  evaporation.
            - TBP, Documented as the 'ADIOS 1 liquid boiling point
                   (bubble pt)'.
            - BullAdios1, which appears to be used to scale-average the
                          initially computed bullwinkle fraction.

            Regardless, in order to approximate what Adios2 is doing, we
            need this modification of our bullwinkle fraction.
        '''
        oil_api = self.get_api()

        t_g = 1356.7 - 247.36 * np.log(oil_api)
        t_bp = 532.98 - 3.1295 * oil_api
        bull_adios1 = (483.0 - t_bp) / t_g

        bull_adios1 = np.clip(bull_adios1, 0.0, 0.4)

        return 0.5 * (bullwinkle_fraction + bull_adios1)

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
