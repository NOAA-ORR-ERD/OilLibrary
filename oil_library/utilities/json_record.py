'''
    JSON Oil record utility functions.

    These are functions to be used primarily for estimating oil
    properties that are contained within an incoming JSON oil record.
'''

from .imported_record import ImportedRecordWithEstimation


class ObjFromDict(object):
    '''
        Generalized method for interpreting a nested data structure of
        dicts, lists, and values, such as that coming from a parsed
        JSON string.  We consume this data structure and represent it
        as a structure of linked python objects.

        So instead of needing to access our data like this:
            json_obj['densities'][0]['ref_temp_k']
        we can do this instead:
            json_obj.densities[0].ref_temp_k
    '''
    def __init__(self, data):
        for name, value in data.iteritems():
            setattr(self, name, self._wrap(value))

    def _wrap(self, value):
        if isinstance(value, (tuple, list, set, frozenset)):
            return type(value)([self._wrap(v) for v in value])
        elif isinstance(value, dict):
            return ObjFromDict(value)
        else:
            return value


class JsonRecordWithEstimation(ImportedRecordWithEstimation):

    def __init__(self, json_rec):
        self.record = ObjFromDict(json_rec)
        self._normalize_json_attrs()

    def _normalize_json_attrs(self):
        self._default_attrs_with_weathering()
        self._default_inert_attrs()
        self._default_cut_attr()

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

















