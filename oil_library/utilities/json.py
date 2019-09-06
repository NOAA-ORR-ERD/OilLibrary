'''
    JSON Oil record utility functions.

    These are general functions to be used primarily for helping us deal
    with an incoming JSON oil record.
'''


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
        for name, value in data.items():
            setattr(self, name, self._wrap(value))

    def _wrap(self, value):
        if isinstance(value, (tuple, list, set, frozenset)):
            return type(value)([self._wrap(v) for v in value])
        elif isinstance(value, dict):
            return ObjFromDict(value)
        else:
            return value
