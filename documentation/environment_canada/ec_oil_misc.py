

def get_min_temp(temp_c):
    '''
        calculate the pour point minimum value from the Excel content
        - Excel float content is in degrees Celcius

        - if we have no preceding operater,     then min = the value.
        - if we have a '>' preceding the float, then min = the value.
        - if we have a '<' preceding the float, then min = None.
        - otherwise,                                 min = None
    '''
    op, value = get_op_and_value(temp_c)

    if op == '<':
        value = None

    return celcius_to_kelvin(value)


def get_max_temp(temp_c):
    '''
        calculate the flash point minimum value from the Excel content
        - Excel float content is in degrees Celcius

        - if we have no preceding operater,     then max = the value.
        - if we have a '<' preceding the float, then max = the value.
        - if we have a '>' preceding the float, then max = None.
        - otherwise,                                 max = None
    '''
    op, value = get_op_and_value(temp_c)

    if op == '>':
        value = None

    return celcius_to_kelvin(value)


def get_op_and_value(value_in):
    '''
        Environment Canada sometimes puts a '<' or '>' in front of the numeric
        value in a cell of the Excel spreadsheet.
        In these cases, it is a string indicating greater than or less than
        the float value.  So we need to split the content into an operator
        and a float value.
        Most of the time, it is a float value, in which we just interpret it
        with no associated operator.
    '''
    op = None

    if isinstance(value_in, (int, float)):
        value = value_in
    elif isinstance(value_in, str):
        op = value_in[0].encode('utf8')
        value = float(value_in[1:])
    else:
        value = None

    return op, value


def celcius_to_kelvin(temp_c):
    if temp_c is not None:
        temp_c += 273.15

    return temp_c


def g_cm_2_to_kg_m_2(g_cm_2):
    if g_cm_2 is not None:
        g_cm_2 *= 10

    return g_cm_2


def percent_to_fraction(percent):
    if percent is not None:
        percent /= 100.0

    return percent
