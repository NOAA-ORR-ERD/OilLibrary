
import numpy as np

from sqlalchemy import (Column,
                        Integer,
                        Float,
                        Enum,
                        ForeignKey)

# Let's make declarative_base a class decorator
from oil_library.models import Base


class InterfacialTension(Base):
    __tablename__ = 'interfacial_tensions'
    id = Column(Integer, primary_key=True)
    imported_record_id = Column(Integer, ForeignKey('imported_records.id'))
    oil_id = Column(Integer, ForeignKey('oils.id'))

    interface = Column(Enum('air', 'water', 'seawater'), nullable=False)

    n_m = Column(Float(53))
    ref_temp_k = Column(Float(53))
    weathering = Column(Float(53))

    def __init__(self, **kwargs):
        for a, v in kwargs.iteritems():
            if (a in self.columns):
                setattr(self, a, v)

        if 'weathering' not in kwargs:
            # sqlalchemy column defaults only work upon insert/update, so we
            # have to put an explicit default here.
            self.weathering = 0.0

    def __repr__(self):
        return ('<InterfacialTension({0.n_m} N/m at {0.ref_temp_k}K, '
                'if={0.interface})>'
                .format(self))


class FlashPoint(Base):
    __tablename__ = 'flash_points'
    id = Column(Integer, primary_key=True)
    imported_record_id = Column(Integer, ForeignKey('imported_records.id'))
    oil_id = Column(Integer, ForeignKey('oils.id'))

    min_temp_k = Column(Float(53))
    max_temp_k = Column(Float(53))
    weathering = Column(Float(53))

    def __init__(self, **kwargs):
        for a, v in kwargs.iteritems():
            if (a in self.columns):
                setattr(self, a, v)

        if 'weathering' not in kwargs:
            # sqlalchemy column defaults only work upon insert/update, so we
            # have to put an explicit default here.
            self.weathering = 0.0

    def __repr__(self):
        return ('<FlashPoint('
                'min={0.min_temp_k}K, '
                'max={0.max_temp_k}K, '
                'weathering={0.weathering})>'
                .format(self))


class PourPoint(Base):
    __tablename__ = 'pour_points'
    id = Column(Integer, primary_key=True)
    imported_record_id = Column(Integer, ForeignKey('imported_records.id'))
    oil_id = Column(Integer, ForeignKey('oils.id'))

    min_temp_k = Column(Float(53))
    max_temp_k = Column(Float(53))
    weathering = Column(Float(53))

    def __init__(self, **kwargs):
        for a, v in kwargs.iteritems():
            if (a in self.columns):
                setattr(self, a, v)

        if 'weathering' not in kwargs:
            # sqlalchemy column defaults only work upon insert/update, so we
            # have to put an explicit default here.
            self.weathering = 0.0

    def __repr__(self):
        return ('<PourPoint('
                'min={0.min_temp_k}K, '
                'max={0.max_temp_k}K, '
                'weathering={0.weathering})>'
                .format(self))


class ECCut(Base):
    '''
        Distillation cut object that has been tailored to Environment
        Canada's data.  Mostly the same, but with weathering added.
    '''
    __tablename__ = 'ec_cuts'
    id = Column(Integer, primary_key=True)
    imported_record_id = Column(Integer, ForeignKey('imported_records.id'))
    oil_id = Column(Integer, ForeignKey('oils.id'))

    vapor_temp_k = Column(Float(53))
    liquid_temp_k = Column(Float(53))
    fraction = Column(Float(53))
    weathering = Column(Float(53))

    def __init__(self, **kwargs):
        for a, v in kwargs.iteritems():
            if (a in self.columns):
                setattr(self, a, v)

        if 'weathering' not in kwargs:
            # sqlalchemy column defaults only work upon insert/update, so we
            # have to put an explicit default here.
            self.weathering = 0.0

    def __repr__(self):
        lt = '{0}K'.format(self.liquid_temp_k) if self.liquid_temp_k else None
        vt = '{0}K'.format(self.vapor_temp_k) if self.vapor_temp_k else None
        return ('<Cut(liquid_temp={0}, vapor_temp={1}, '
                'fraction={2}, weathering={3})>'
                .format(lt, vt, self.fraction, self.weathering))


class Adhesion(Base):
    __tablename__ = 'adhesions'
    id = Column(Integer, primary_key=True)
    imported_record_id = Column(Integer, ForeignKey('imported_records.id'))
    oil_id = Column(Integer, ForeignKey('oils.id'))

    kg_m_2 = Column(Float(53))
    weathering = Column(Float(53))

    def __init__(self, **kwargs):
        for a, v in kwargs.iteritems():
            if (a in self.columns):
                setattr(self, a, v)

        if 'weathering' not in kwargs:
            # sqlalchemy column defaults only work upon insert/update, so we
            # have to put an explicit default here.
            self.weathering = 0.0

    def __repr__(self):
        return ('<Adhesion({0.kg_m_2} kg/m^2, weathering={0.weathering})>'
                .format(self))


class EvaporationEq(Base):
    __tablename__ = 'evaporation_eqs'
    id = Column(Integer, primary_key=True)
    imported_record_id = Column(Integer, ForeignKey('imported_records.id'))
    oil_id = Column(Integer, ForeignKey('oils.id'))

    a = Column(Float(53))
    b = Column(Float(53))
    c = Column(Float(53))
    equation = Column(Enum('(A + BT) ln t',
                           '(A + BT) sqrt(t)',
                           'A + B ln (t + C)'),
                      nullable=False)

    weathering = Column(Float(53))

    def __init__(self, **kwargs):
        for a, v in kwargs.iteritems():
            if (a in self.columns):
                setattr(self, a, v)

        if 'weathering' not in kwargs:
            # sqlalchemy column defaults only work upon insert/update, so we
            # have to put an explicit default here.
            self.weathering = 0.0

        self.alg = {'(A + BT) ln t': self.calculate_ests_1998,
                    '(A + BT) sqrt(t)': self.calculate_mass_loss1,
                    'A + B ln (t + C)': self.calculate_mass_loss2}

    def __repr__(self):
        return ('<EvaporationEq(a={0.a}, b={0.b}, c={0.c}, '
                'eq="{0.equation}", '
                'weathering={0.weathering})>'
                .format(self))

    def calculate(self, t, T=None):
        return self.alg[self.equation](t, T)

    def calculate_ests_1998(self, t, T):
        return (self.a + self.b * T) * np.log(t)

    def calculate_mass_loss1(self, t, T):
        return (self.a + self.b * T) * np.sqrt(t)

    def calculate_mass_loss2(self, t, T):
        return self.a + self.b * np.log(t + self.c)


class Emulsion(Base):
    __tablename__ = 'emulsions'
    id = Column(Integer, primary_key=True)
    imported_record_id = Column(Integer, ForeignKey('imported_records.id'))
    oil_id = Column(Integer, ForeignKey('oils.id'))

    complex_modulus_pa = Column(Float(53))
    storage_modulus_pa = Column(Float(53))
    loss_modulus_pa = Column(Float(53))
    tan_delta_v_e = Column(Float(53))
    complex_viscosity_pa_s = Column(Float(53))
    water_content_fraction = Column(Float(53))

    ref_temp_k = Column(Float(53))
    age_days = Column(Float(53))
    weathering = Column(Float(53))

    def __init__(self, **kwargs):
        for a, v in kwargs.iteritems():
            if (a in self.columns):
                setattr(self, a, v)

        if 'weathering' not in kwargs:
            # sqlalchemy column defaults only work upon insert/update, so we
            # have to put an explicit default here.
            self.weathering = 0.0

    def __repr__(self):
        return ('<Emulsion('
                'complex_mod={0.complex_modulus_pa:0.3g} Pa, '
                'storage_mod={0.storage_modulus_pa:0.3g} Pa, '
                'loss_mod={0.loss_modulus_pa:0.3g} Pa, '
                'tan_delta={0.tan_delta_v_e:0.3g} V/E, '
                'complex_vis={0.complex_viscosity_pa_s:0.3g} Pa.s, '
                'water_content={0.water_content_fraction:0.3g}, '
                'temp={0.ref_temp_k}K, '
                'age={0.age_days} days, '
                'weathering={0.weathering})>'
                .format(self))








