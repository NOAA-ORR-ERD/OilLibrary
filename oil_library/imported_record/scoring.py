#!/usr/bin/env python

import numpy as np


class ImportedRecordWithScore(object):
    def __init__(self, imported_rec):
        self.record = imported_rec

    def aggregate_score(self, Q_i, w_i=None):
        '''
            General method for aggregating a number of sub-scores.
            We implement a weighted average for this.
        '''
        Q_i = np.array(Q_i)

        if w_i is None:
            w_i = np.ones(Q_i.shape)
        else:
            w_i = np.array(w_i)

        return np.sum(w_i * Q_i) / np.sum(w_i)

    def score(self):
        scores = [(self.score_densities(), 5.0),
                  (self.score_viscosities(), 5.0),
                  (self.score_sara_fractions(), 5.0),
                  (self.score_cuts(), 10.0),
                  (self.score_interfacial_tensions(), 3.0),
                  (self.score_pour_point(), 2.0),
                  (self.score_demographics(), 1.0),
                  (self.score_flash_point(), 1.0),
                  (self.score_emulsion_constants(), 1.0)]

        return self.aggregate_score(*list(zip(*scores)))

    def score_demographics(self):
        fields = ('reference',)
        scores = []

        for f in fields:
            if getattr(self.record, f) is not None:
                scores.append(1.0)
            else:
                scores.append(0.0)

        return self.aggregate_score(scores)

    def score_api(self):
        if self.record.api is None:
            return 0.0
        else:
            return 1.0

    def score_densities(self):
        scores = []

        for d in self.record.densities:
            scores.append(self._score_density_rec(d))

        if not any([np.isclose(d.ref_temp_k, [288.0, 288.15]).any()
                    for d in self.record.densities]):
            scores.append(self.score_api())

        # We have a maximum number of 4 density field sets in our flat file
        # We can set a lower acceptable number later
        if len(scores) < 4:
            scores += [0.0] * (4 - len(scores))

        # compute our weights
        w_i = 1.0 / (2.0 ** (np.arange(len(scores)) + 1))
        w_i[-1] = w_i[-2]  # duplicate the last weight so we sum to 1.0

        return self.aggregate_score(scores, w_i)

    def _score_density_rec(self, density_rec):
        if (density_rec.kg_m_3 is not None and
                density_rec.ref_temp_k is not None):
            return 1.0
        else:
            return 0.0

    def score_pour_point(self):
        scores = []

        scores.append(self._score_pour_point_max())
        scores.append(self._score_pour_point_min())
        w_i = [2.0, 1.0]

        return self.aggregate_score(scores, w_i)

    def _score_pour_point_min(self):
        return (1.0 if self.record.pour_point_min_k is not None else 0.0)

    def _score_pour_point_max(self):
        return (1.0 if self.record.pour_point_max_k is not None else 0.0)

    def score_flash_point(self):
        if (self.record.flash_point_min_k is not None or
                self.record.flash_point_max_k is not None):
            return 1.0
        else:
            return 0.0

    def score_sara_fractions(self):
        scores = []

        scores.append(self._score_sara_saturates())
        scores.append(self._score_sara_aromatics())
        scores.append(self._score_sara_resins())
        scores.append(self._score_sara_asphaltenes())

        return self.aggregate_score(scores)

    def _score_sara_saturates(self):
        return (1.0 if self.record.saturates is not None else 0.0)

    def _score_sara_aromatics(self):
        return (1.0 if self.record.aromatics is not None else 0.0)

    def _score_sara_resins(self):
        return (1.0 if self.record.resins is not None else 0.0)

    def _score_sara_asphaltenes(self):
        return (1.0 if self.record.asphaltenes is not None else 0.0)

    def score_emulsion_constants(self):
        scores = []

        scores.append(self._score_water_content_emulsion())
        scores.append(self._score_emulsion_constant_min())
        # scores.append(self._score_emulsion_constant_max())

        w_i = [2.0, 3.0]

        return self.aggregate_score(scores, w_i)

    def _score_water_content_emulsion(self):
        return (1.0 if self.record.water_content_emulsion is not None else 0.0)

    def _score_emulsion_constant_min(self):
        return (1.0 if self.record.emuls_constant_min is not None else 0.0)

    def _score_emulsion_constant_max(self):
        return (1.0 if self.record.emuls_constant_max is not None else 0.0)

    def score_interfacial_tensions(self):
        scores = []

        scores.append(self._score_oil_water_tension())
        scores.append(self._score_oil_seawater_tension())

        return self.aggregate_score(scores)

    def _score_oil_water_tension(self):
        rec = self.record
        if (rec.oil_water_interfacial_tension_n_m is not None and
                rec.oil_water_interfacial_tension_ref_temp_k is not None):
            return 1.0
        else:
            return 0.0

    def _score_oil_seawater_tension(self):
        rec = self.record
        if (rec.oil_seawater_interfacial_tension_n_m is not None and
                rec.oil_seawater_interfacial_tension_ref_temp_k is not None):
            return 1.0
        else:
            return 0.0

    def score_viscosities(self):
        scores = []
        all_temps = set()
        all_viscosities = []

        for v in self.record.kvis + self.record.dvis:
            if v.ref_temp_k not in all_temps:
                all_viscosities.append(v)
                all_temps.add(v.ref_temp_k)

        for v in all_viscosities:
            scores.append(self._score_single_viscosity(v))

        # We require a minimum number of 4 viscosity field sets
        if len(scores) < 4:
            scores += [0.0] * (4 - len(scores))

        # compute our weights
        w_i = 1.0 / (2.0 ** (np.arange(len(scores)) + 1))
        w_i[-1] = w_i[-2]  # duplicate the last weight so we sum to 1.0

        return self.aggregate_score(scores, w_i)

    def _score_single_viscosity(self, viscosity_rec):
        temp = viscosity_rec.ref_temp_k

        try:
            value = viscosity_rec.m_2_s
        except AttributeError:
            value = viscosity_rec.kg_ms

        if (value is not None and temp is not None):
            return 1.0
        else:
            return 0.0

    def score_cuts(self):
        scores = []

        for c in self.record.cuts:
            scores.append(self._score_single_cut(c))

        # We would like a minimum number of 10 distillation cuts
        if len(scores) < 10:
            scores += [0.0] * (10 - len(scores))

        # compute our weights
        w_i = 1.0 / (2.0 ** (np.arange(len(scores)) + 1))
        w_i[-1] = w_i[-2]  # duplicate the last weight so we sum to 1.0

        return self.aggregate_score(scores, w_i)

    def _score_single_cut(self, cut_rec):
        if self._cut_has_fraction(cut_rec) == 1.0:
            if self._cut_has_vapor_temp(cut_rec) == 1.0:
                return 1.0
            elif self._cut_has_liquid_temp(cut_rec) == 1.0:
                return 0.8
            else:
                return 0.0
        else:
            return 0.0

    def _cut_has_vapor_temp(self, cut_rec):
        return (0.0 if cut_rec.vapor_temp_k is None else 1.0)

    def _cut_has_fraction(self, cut_rec):
        return (0.0 if cut_rec.fraction is None else 1.0)

    def _cut_has_liquid_temp(self, cut_rec):
        return (0.0 if cut_rec.liquid_temp_k is None else 1.0)

    def score_toxicities(self):
        scores = []

        for t in self.record.toxicities:
            scores.append(self._score_single_toxicity(t))

        if any([(s == 1.0) for s in scores]):
            return 1.0
        else:
            return 0.0

    def _score_single_toxicity(self, tox_rec):
        if (tox_rec.species is not None and
            (tox_rec.after_24h is not None or
             tox_rec.after_48h is not None or
             tox_rec.after_96h is not None)):
            return 1.0
        else:
            return 0.0
