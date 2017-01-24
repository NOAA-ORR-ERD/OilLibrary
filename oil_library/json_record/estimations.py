'''
    JSON Oil record utility functions.

    These are functions to be used primarily for estimating oil
    properties that are contained within an incoming JSON oil record.
'''

from ..utilities.json import ObjFromDict
from ..imported_record.estimations import ImportedRecordWithEstimation


class JsonRecordWithEstimation(ImportedRecordWithEstimation):

    def __init__(self, json_rec):
        self.record = ObjFromDict(json_rec)
        self._normalize_json_attrs()

    def _normalize_json_attrs(self):
        self._default_attrs_with_weathering()
        self._default_inert_attrs()
        self._default_cut_attr()
        self._default_oil_misc_attrs()

    def _default_oil_misc_attrs(self):
        '''
            Just make sure the attributes exist so later processes
            don't have to guess
        '''
        for attrname in ('pour_point_min_k',
                         'pour_point_max_k'):
            if not (hasattr(self.record, attrname)):
                setattr(self.record, attrname, None)

    def _default_attrs_with_weathering(self):
        '''
            Just make sure the attributes exist so later processes
            don't have to guess
        '''
        for attrname in ('densities', 'kvis', 'dvis'):
            try:
                for attr in getattr(self.record, attrname):
                    if (hasattr(attr, 'weathering') and
                            attr.weathering is not None):
                        continue
                    else:
                        attr.weathering = 0.0
            except AttributeError:
                pass

    def _default_inert_attrs(self):
        '''
            Just make sure the attributes exist so later processes
            don't have to guess
        '''
        if not (hasattr(self.record, 'resins') or
                hasattr(self.record, 'resins_fraction')):
            self.record.resins_fraction = None

        if not (hasattr(self.record, 'asphaltenes') or
                hasattr(self.record, 'asphaltenes_fraction')):
            self.record.asphaltenes_fraction = None

    def _default_cut_attr(self):
        '''
            Just make sure the attributes exist so later processes
            don't have to guess
        '''
        if not hasattr(self.record, 'cuts'):
            self.record.cuts = []
