
from collections import defaultdict

from slugify import Slugify

custom_slugify = Slugify(to_lower=True)
custom_slugify.separator = '_'


def get_oil_column_indexes(xl_sheet):
    '''
        This is tailored to parse the data format of the Excel spreadsheet of
        oil properties that was given to NOAA by Environment Canada (2017).

        Each single oil is represented in the spreadsheet by a contiguous
        group of columns, and only the first column contains the name of
        the oil.

        Return a dict with oil names as keys and a list of associated
        column indexes as values
    '''
    col_headers = defaultdict(list)
    col_prev_name = None

    for idx, col in enumerate(xl_sheet.columns):
        if idx >= 2:
            if col[0].value is not None:
                col_value = col[0].value.strip()

                col_headers[col_value].append(idx)
                col_prev_name = col_value
            else:
                col_headers[col_prev_name].append(idx)

    return col_headers


def get_row_field_names(xl_sheet):
    '''
        This is tailored to parse the data format of the Excel spreadsheet of
        oil properties that was given to NOAA by Environment Canada (2017).

        Column 0 contains field category names in which each single category
        is represented by a contiguous group of rows, and only the first row
        contains the name of the category.

        Within the group of category rows, column 1 contains specific oil
        property names.  So to get a specific property for an oil, one needs to
        reference (category, property)
        A property name within a category is not unique.  For example,
        emulsion at 15C has multiple standard_deviation fields.

        There also exist rows that are not associated with any oil property
        which contain blank fields for both category and property.

        For field names, we would like to keep them lowercase, strip out the
        special characters, and separate the individual word components of the
        field name with '_'
    '''
    row_fields = defaultdict(lambda: defaultdict(list))
    row_prev_name = None

    for idx, row in enumerate(xl_sheet.rows):
        if all([(r.value is None) for r in row[:2]]):
            category_name, field_name = None, None
        elif row[0].value is not None:
            category_name = custom_slugify(row[0].value).lower()
            row_prev_name = category_name
            if row[1].value is not None:
                field_name = custom_slugify(str(row[1].value)).lower()
            else:
                field_name = None
        else:
            category_name = row_prev_name
            if row[1].value is not None:
                field_name = custom_slugify(str(row[1].value)).lower()
            else:
                field_name = None

        row_fields[category_name][field_name].append(idx)

    return row_fields


def get_oil_columns(xl_sheet, col_indexes):
    '''
        Return the columns in the Excel sheet referenced by a list of indexes
    '''
    return [c for i, c in enumerate(xl_sheet.columns) if i in col_indexes]


def get_oil_properties_by_name(oil_columns, field_indexes,
                               category, name):
    '''
        Get the oil data properties for each column of oil data, referenced by
        their category name and oil property name.
        - This function is intended to work on the oil data columns for a
          single oil, but this is not enforced.
    '''
    return [[c[i] for i in field_indexes[category][name]]
            for c in oil_columns]


def get_oil_properties_by_category(oil_columns, field_indexes,
                                   category):
    '''
        Get all oil data properties for each column of oil data, that exist
        within a single category.
        - This function is intended to work on the oil data columns for a
          single oil, but this is not enforced.
        - the oil properties will be returned as a dictionary.
    '''
    ret = {}
    cat_fields = field_indexes[category]
    for f, idxs in cat_fields.items():
        ret[f] = [[c[i] for i in idxs]
                  for c in oil_columns]

    return ret
