'''
    JSON Oil record utility functions.

    These are functions to be used primarily for estimating oil
    properties that are contained within an incoming JSON oil record.
'''

import numpy as np
from scipy.optimize import curve_fit

import estimations as est

from .imported_record import (ImportedRecordWithEstimation,
                              _linear_curve,
                              _inverse_linear_curve)


class JsonRecordWithEstimation(ImportedRecordWithEstimation):

    @classmethod
    def lowest_temperature(cls, obj_list):
        '''
            General utility function.

            From a list of objects containing a ref_temp_k attribute,
            return the object that has the lowest temperature
        '''
        if len(obj_list) > 0:
            return sorted(obj_list, key=lambda d: d['ref_temp_k'])[0]
        else:
            return None

    @classmethod
    def closest_to_temperature(cls, obj_list, temperature):
        '''
            General Utility Function

            From a list of objects containing a ref_temp_k attribute,
            return the object that is closest to the specified temperature
        '''
        temp_diffs = [(obj, abs(obj['ref_temp_k'] - temperature))
                      for obj in obj_list
                      if obj['ref_temp_k'] is not None]
        if len(temp_diffs) > 0:
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
        if attr_name in self.record:
            obj_list = [o for o in self.record[attr_name]
                        if all([(o[attr] is not None)
                                for attr in non_null_attrs])]

            for o in obj_list:
                if 'weathering' not in o or o['weathering'] is None:
                    o['weathering'] = 0.0
        else:
            obj_list = []

        return obj_list

    def density_at_temp(self, temperature, weathering=0.0):
        density_list = [d for d in self.culled_densities()
                        if d['weathering'] == weathering]
        closest_density = self.closest_to_temperature(density_list,
                                                      temperature)

        if closest_density is not None:
            d_ref, t_ref = (closest_density['kg_m_3'],
                            closest_density['ref_temp_k'])
        elif self.record['api'] is not None:
            d_ref, t_ref = est.density_from_api(self.record['api'])
        else:
            return None

        return est.density_at_temp(d_ref, t_ref, temperature)

    def get_densities(self, weathering=0.0):
        densities = [d for d in self.culled_densities()
                     if d['weathering'] == weathering]

        if len(densities) == 0:
            kg_m_3, ref_temp_k = est.density_from_api(self.record['api'])

            densities.append(dict(kg_m_3=kg_m_3,
                                  ref_temp_k=ref_temp_k,
                                  weathering=0.0))

        return densities

    def get_api(self):
        if self.record['api'] is not None:
            return self.record['api']
        elif len(self.get_densities()) > 0:
            return est.api_from_density(self.density_at_temp(273.15 + 15))
        else:
            return None

    def non_redundant_dvis(self):
        kvis_dict = dict([((v['weathering'], v['ref_temp_k']), v['m_2_s'])
                          for v in self.culled_kvis()])
        dvis_dict = dict([((v['weathering'], v['ref_temp_k']), v['kg_ms'])
                          for v in self.culled_dvis()])

        non_redundant_keys = set(dvis_dict.keys()).difference(kvis_dict.keys())
        for k in sorted(non_redundant_keys):
            yield dict(ref_temp_k=k[1],
                       weathering=k[0],
                       kg_ms=dvis_dict[k])

    def dvis_to_kvis(self, kg_ms, ref_temp_k):
        print 'dvis_to_kvis(): ', self.record, kg_ms, ref_temp_k
        density = self.density_at_temp(ref_temp_k)
        if density is None:
            return None
        else:
            return kg_ms / density

    @classmethod
    def dvis_obj_to_kvis_obj(cls, dvis_obj, density):
        viscosity = est.dvis_to_kvis(dvis_obj['kg_ms'], density)

        return dict(ref_temp_k=dvis_obj['ref_temp_k'],
                    weathering=dvis_obj['weathering'],
                    m_2_s=viscosity)

    def aggregate_kvis(self):
        kvis_list = self.culled_kvis()

        if 'dvis' in self.record:
            dvis_list = list(self.non_redundant_dvis())
            densities = [self.density_at_temp(d['ref_temp_k'])
                         for d in dvis_list]

            kvis_list += [self.dvis_obj_to_kvis_obj(dv, rho)
                          for dv, rho in zip(dvis_list, densities)]

        return sorted(kvis_list,
                      key=lambda x: (x['ref_temp_k'], x['weathering']))

    def kvis_at_temp(self, temp_k, weathering=0.0):
        kvis_list = [kv for kv in self.aggregate_kvis()
                     if (kv['weathering'] == weathering)]
        closest_kvis = self.closest_to_temperature(kvis_list, temp_k)

        if closest_kvis is not None:
            ref_kvis, ref_temp_k = (closest_kvis['m_2_s'],
                                    closest_kvis['ref_temp_k'])
        else:
            return None

        return est.kvis_at_temp(ref_kvis, ref_temp_k, temp_k)

    def inert_fractions(self):
        try:
            f_res, f_asph = self.record['resins'], self.record['asphaltenes']
        except KeyError:
            try:
                f_res, f_asph = (self.record['resins_fraction'],
                                 self.record['asphaltenes_fraction'])
            except KeyError:
                f_res, f_asph = None, None

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
        if 'cuts' in self.record:
            prev_temp = prev_fraction = 0.0
            for c in self.record['cuts']:
                if c['vapor_temp_k'] < prev_temp:
                    continue

                if c['fraction'] < prev_fraction:
                    continue

                prev_temp = c['vapor_temp_k']
                prev_fraction = c['fraction']

                yield c

    def normalized_cut_values(self, N=10):
        f_res, f_asph = self.inert_fractions()
        cuts = list(self.culled_cuts())

        if len(cuts) == 0:
            if self.record['api'] is not None:
                oil_api = self.record['api']
            else:
                oil_rho = self.density_at_temp(288.15)
                oil_api = est.api_from_density(oil_rho)

            BP_i = est.cut_temps_from_api(oil_api)
            fevap_i = np.cumsum(est.fmasses_flat_dist(f_res, f_asph))
        else:
            BP_i, fevap_i = zip(*[(c['vapor_temp_k'], c['fraction'])
                                  for c in cuts])

        popt, _pcov = curve_fit(_linear_curve, BP_i, fevap_i)

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

    def component_densities(self, N=10):
        cut_temps = self.get_cut_temps(N)

        return self.estimate_component_densities(cut_temps)

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
