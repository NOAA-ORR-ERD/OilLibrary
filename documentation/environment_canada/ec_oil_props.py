
from ec_xl_parse import get_oil_properties_by_name


def get_oil_weathering(oil_columns, field_indexes):
    cells = get_oil_properties_by_name(oil_columns, field_indexes,
                                       None, 'weathered')
    return [c[0].value for c in cells]


def get_oil_reference(oil_columns, field_indexes):
    cells = get_oil_properties_by_name(oil_columns, field_indexes,
                                       None, 'reference')
    return ' '.join([c[0].value for c in cells
                     if c[0].value is not None])
