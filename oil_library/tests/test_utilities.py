'''
test functions in utilities modules
'''
import numpy as np
import pytest

from oil_library import get_oil_props


op_obj = get_oil_props('LUCKENBACH FUEL OIL')
oil_obj = op_obj.record

# Test case - get ref temps from densities then append ref_temp for
# density at 0th index for a few more values:
#    density_test = [d.ref_temp_k for d in oil_.densities]
#    density_test.append(oil_.densities[0].ref_temp_k)
density_tests = [oil_obj.densities[ix].ref_temp_k
                 if ix < len(oil_obj.densities)
                 else oil_obj.densities[0].ref_temp_k
                 for ix in range(0, len(oil_obj.densities) + 3)]
density_exp = [d.kg_m_3 for temp in density_tests for d in oil_obj.densities
               if abs(d.ref_temp_k - temp) == 0]

'''
test get_density for
- scalar
- list, tuple
- numpy arrays as row/column and with/without output arrays
'''


@pytest.mark.parametrize(("temps", "exp_value", "use_out"),
                         [(density_tests[0], density_exp[0], False),
                          (density_tests, density_exp, False),
                          (tuple(density_tests), density_exp, False),
                          (np.asarray(density_tests)
                           .reshape(len(density_tests), -1),
                           np.asarray(density_exp)
                           .reshape(len(density_tests), -1), False),
                          (np.asarray(density_tests),
                           np.asarray(density_exp), False),
                          ])
def test_get_density(temps, exp_value, use_out):
    if use_out:
        out = np.zeros_like(temps)
        op_obj.density_at_temp(temps, out)
    else:
        out = op_obj.density_at_temp(temps)

    assert np.all(out == exp_value)   # so it works for scalar + arrays


# Test case - get ref temps from kvis then append ref_temp for
# kvis at 0th index for a few more values:
#    viscosity_tests = [d.ref_temp_k for d in oil_.densities]
#    viscosity_tests.append(oil_.densities[0].ref_temp_k)
oil_pp = op_obj.pour_point()[0]
if oil_pp is None:
    oil_pp = op_obj.pour_point()[1]

v_max = op_obj.kvis_at_temp(oil_pp)

viscosity_tests = [oil_obj.kvis[ix].ref_temp_k if ix < len(oil_obj.kvis)
                   else oil_obj.kvis[0].ref_temp_k
                   for ix in range(0, len(oil_obj.kvis) + 3)]

print 'v_max', v_max
viscosity_exp = [(d.m_2_s, v_max)[v_max < d.m_2_s]
                 for temp in viscosity_tests
                 for d in oil_obj.kvis
                 if abs(d.ref_temp_k - temp) == 0]


@pytest.mark.parametrize(("temps", "exp_value", "use_out"),
                         [(viscosity_tests[0], viscosity_exp[0], False),
                          (viscosity_tests, viscosity_exp, False),
                          (tuple(viscosity_tests), viscosity_exp, False),
                          (np.asarray(viscosity_tests)
                           .reshape(len(viscosity_tests), -1),
                           np.asarray(viscosity_exp)
                           .reshape(len(viscosity_tests), -1), False),
                          (np.asarray(viscosity_tests),
                           np.asarray(viscosity_exp), False),
                          ])
def test_get_viscosity(temps, exp_value, use_out):
    if use_out:
        out = np.zeros_like(temps)
        op_obj.kvis_at_temp(temps, out)
    else:
        out = op_obj.kvis_at_temp(temps)

    print 'temps: ', temps
    print 'out: ', out
    print 'expected: ', exp_value

    assert np.all(out == exp_value)   # so it works for scalar + arrays


@pytest.mark.parametrize("max_cuts", (1, 2, 3, 4, 5))
def test_boiling_point(max_cuts):
    '''
    some basic testing of boiling_point function
    - checks len(bp) == max_cuts * 2
    - also checks that the BP for saturates == BP for aromatics
    '''

    bp = op_obj.component_temps(N=max_cuts)

    print 'bp = ', bp

    assert len(bp) == max_cuts * 2 + 2
    assert ([bp[ix] - bp[ix + 1]
             for ix in range(0, max_cuts * 2, 2)] ==
            [0.0] * max_cuts)
