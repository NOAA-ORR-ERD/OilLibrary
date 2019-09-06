
import numpy as np

from openpyxl import load_workbook

from ec_xl_parse import (get_oil_column_indexes,
                         get_oil_columns,
                         get_row_field_names)
from ec_oil_props import get_oil_weathering, get_oil_reference
from ec_density import get_oil_densities, get_oil_api
from ec_viscosity import get_oil_viscosities
from ec_interfacial_tension import get_oil_interfacial_tensions
from ec_flash_point import get_oil_flash_points
from ec_pour_point import get_oil_pour_points
from ec_distillation import get_oil_distillation_cuts
from ec_adhesion import get_oil_adhesions
from ec_evaporation_eq import get_oil_evaporation_eqs
from ec_emulsion import get_oil_emulsions
from ec_groups import (get_oil_sulfur_content,
                       get_oil_water_content,
                       get_oil_wax_content,
                       get_oil_sara_total_fractions)

from pprint import PrettyPrinter
pp = PrettyPrinter(indent=2, width=120)


if __name__ == '__main__':
    wb = load_workbook('Physiochemical properties of petroleum products-EN.xlsx')
    wb.get_sheet_names()

    db_sheet = wb.get_sheet_by_name('Database')

    col_indexes = get_oil_column_indexes(db_sheet)
    field_indexes = get_row_field_names(db_sheet)

    for cat, v in field_indexes.items():
        for field, idxs in v.items():
            print(cat, field, idxs)

    for name, idxs in col_indexes.items():
        # if name == 'Arabian Heavy [2004]':
        # if name == 'Anadarko HIA-376':
        # if name == 'Gail Well E010':
        # if name == 'Access West Winter Blend':
        if name == 'Alaminos Canyon Block 25':
            oil_columns = get_oil_columns(db_sheet, col_indexes[name])
            print('Weathered %: ', get_oil_weathering(oil_columns, field_indexes))
            print('Reference: ', get_oil_reference(oil_columns, field_indexes))

            print('Densities: ')
            pp.pprint(get_oil_densities(oil_columns, field_indexes))
            print('APIs:', get_oil_api(oil_columns, field_indexes))

            print('DVis: ')
            pp.pprint(get_oil_viscosities(oil_columns, field_indexes))

            print('Interfacial Tensions:')
            pp.pprint(get_oil_interfacial_tensions(oil_columns, field_indexes))

            print('Flash Points:')
            pp.pprint(get_oil_flash_points(oil_columns, field_indexes))

            print('Pour Points:')
            pp.pprint(get_oil_pour_points(oil_columns, field_indexes))

            print('Boiling Point Distribution:')
            pp.pprint(get_oil_distillation_cuts(oil_columns, field_indexes))

            print('Adhesion:')
            pp.pprint(get_oil_adhesions(oil_columns, field_indexes))

            print('Evaporation:')
            evap_eqs = get_oil_evaporation_eqs(oil_columns, field_indexes)
            pp.pprint([(eq, eq.calculate(np.e, 1)) for eq in evap_eqs])

            print('Emulsion:')
            pp.pprint(get_oil_emulsions(oil_columns, field_indexes))

            print('Sulfur Content:')
            pp.pprint(get_oil_sulfur_content(oil_columns, field_indexes))

            print('Water Content:')
            pp.pprint(get_oil_water_content(oil_columns, field_indexes))

            print('Wax Content:')
            pp.pprint(get_oil_wax_content(oil_columns, field_indexes))

            print('SARA Fractions:')
            pp.pprint(get_oil_sara_total_fractions(oil_columns, field_indexes))





