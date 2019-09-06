'''
OilProps class which serves as a wrapper around
gnome.db.oil_library.models.Oil class

It also contains a dict containing a small number of sample_oils if user does
not wish to query database to use an _r_oil.

It contains a function that takes a string for 'name' and returns and Oil
object used to initialize and OilProps object

Not sure at present if this needs to be serializable?
'''
import copy
from itertools import groupby, chain, zip_longest

try:
    from functools import lru_cache  # it's built-in on py3
except ImportError:
    from backports.functools_lru_cache import lru_cache  # needs backports for py2

import numpy as np

from .models import Oil
from .oil.estimations import OilWithEstimation


# create a dtype for storing sara information in numpy array
sara_dtype = np.dtype([('type', 'S16'),
                       ('boiling_point', np.float64),
                       ('fraction', np.float64),
                       ('density', np.float64),
                       ('mol_wt', np.float64)])


class OilProps(OilWithEstimation):
    '''
    Class which:
    - Contains an oil object.
    - Provides more sophisticated oil properties than the basic oil database
      object.
    - These properties are the result of calculations made upon the
      basic oil database properties.
    - Generally speaking, we will try to adhere to the ASTM standards and use
      the SI measurement system when determining units for our values.
      The SI base units are consistent with the MKS system.

    Specifically, OilProps has a few categories of properties:
    Density:
    - returns a scalar as opposed to a list of Densities.

    Viscosity:

    '''

    def __init__(self, oil_obj):
        '''
        Extends the raw Oil object to include properties required by
        weathering processes. If oil_ is not pulled from database or user may
        wish to use simple half life weatherer, in this case, there is no need
        to carry around more than one psuedo-component. Let user set max_cuts
        if desired, but only during initialization.

        :param oil_: Oil object that maps to entity in OilLib database
        :type oil_: Oil object
        '''
        super(OilProps, self).__init__(oil_obj)

        # Default format for mass components:
        # mass_fraction =
        #     [m0_s, m0_a, m1_s, m1_a, ..., m_resins, m_asphaltenes]
        #
        # the boiling points are in ascending order
        self._init_sara()

        self._bullwinkle = None
        self._bulltime = None

    def __repr__(self):
        return ('{0.__class__.__module__}.{0.__class__.__name__}('
                'oil_={0.record!r})'.format(self))

    name = property(lambda self: self.record.name,
                    lambda self, val: setattr(self.record, 'name', val))
    api = property(lambda self: self.get('api'))

    def get(self, prop):
        'get raw oil props'
        val = None
        try:
            val = getattr(self.record, prop)
        except AttributeError:
            try:
                val = getattr(self.record.imported, prop)
            except Exception:
                pass

        return val

    @property
    def bulltime(self):
        '''
        return bulltime (time to emulsify)
        either user set or just return a flag
        '''
        # check for user input value, otherwise set to -999 as a flag
        bulltime = -999.

        if self._bulltime is not None:
            return self._bulltime
        else:
            return bulltime

    @bulltime.setter
    def bulltime(self, value):
        """
        time to start emulsification
        """
        self._bulltime = value

    @property
    def bullwinkle(self):
        '''
        return bullwinkle (emulsion constant)
        either user set or return database value
        '''
        # check for user input value, otherwise return database value

        if self._bullwinkle is not None:
            return self._bullwinkle
        else:
            return self.get('bullwinkle_fraction')

    @bullwinkle.setter
    def bullwinkle(self, value):
        """
        emulsion constant
        """
        self._bullwinkle = value

    @property
    def num_components(self):
        '''
        number of components with mass fraction > 0.0 used to model the oil
        '''
        return len(self._sara)

    @property
    def molecular_weight(self):
        return self._component_mw()

    def _component_mw(self, sara_type=None):
        '''
        return the molecular weight of the pseudocomponents
        '''
        ret = self._sara['mol_wt']

        if sara_type is not None:
            ret = ret[np.where(self._sara['type'] == sara_type)]

        return ret

    @property
    def mass_fraction(self):
        return self._sara['fraction']

    @property
    def boiling_point(self):
        return self._sara['boiling_point']

    @property
    def component_density(self):
        return self._component_density()

    def _component_density(self, sara_type=None):
        '''
        return the density of the pseudocomponents.
        '''
        ret = self._sara['density']

        if sara_type is not None:
            ret = ret[np.where(self._sara['type'] == sara_type)]

        return ret

    @property
    def component_types(self):
        return self._sara['type']

    def vapor_pressure(self, temp, atmos_pressure=101325.0):
        '''
        water_temp and boiling point units are Kelvin
        returns the vapor_pressure in SI units (Pascals)
        '''
        D_Zb = 0.97
        R_cal = 1.987  # calories

        D_S = 8.75 + 1.987 * np.log(self.boiling_point)
        C_2i = 0.19 * self.boiling_point - 18

        var = 1. / (self.boiling_point - C_2i) - 1. / (temp - C_2i)
        ln_Pi_Po = (D_S * (self.boiling_point - C_2i) ** 2 /
                    (D_Zb * R_cal * self.boiling_point) * var)
        Pi = np.exp(ln_Pi_Po) * atmos_pressure

        return Pi

    def tojson(self):
        '''
            For now, just convert underlying oil object tojson() method
            - An Oil object that has been queried from the database
              contains a lot of unnecessary relationships that we do not
              want to represent in our JSON output,
              So we prune them by first constructing an Oil object from the
              JSON payload of the queried Oil object.
              This creates an Oil object in memory that does not have any
              database links.
              Then we output the JSON from the unlinked object.
        '''

        return Oil.from_json(self.record.tojson()).tojson()

    def get_gnome_oil(self):
        '''
            Return just the oil attributes needed for Gnome
        '''

        densities = []
        density_ref_temps = []
        density_weathering = []
        kvis = []
        kvis_ref_temps = []
        kvis_weathering = []
        for d in self.record.densities:
            densities.append(d.kg_m_3)
            density_ref_temps.append(d.ref_temp_k)
            density_weathering.append(d.weathering)

        for k in self.record.kvis:
            kvis.append(k.m_2_s)
            kvis_ref_temps.append(k.ref_temp_k)
            kvis_weathering.append(k.weathering)

        mass_fraction = self.mass_fraction.tolist()
        boiling_point = self.boiling_point.tolist()
        molecular_weight = self.molecular_weight.tolist()
        component_density = self.component_density.tolist()
        component_types = self.component_types.tolist()

        gnome_oil = {'name':self.name,
                       'api':self.api,
                       'pour_point':self.pour_point()[0],
                       'solubility':self.solubility(),
                       'bullwinkle_fraction':self.get('bullwinkle_fraction'),
                       'bullwinkle_time':self.bulltime,
                       'densities':densities,
                       'density_ref_temps':density_ref_temps,
                       'density_weathering':density_weathering,
                       'kvis':kvis,
                       'kvis_ref_temps':kvis_ref_temps,
                       'kvis_weathering':kvis_weathering,
                       'emulsion_water_fraction_max':self.record.emulsion_water_fraction_max,
                       'mass_fraction':mass_fraction,
                       'boiling_point':boiling_point,
                       'molecular_weight':molecular_weight,
                       'component_density':component_density,
                       'sara_type':component_types}

        return gnome_oil
        
    def _compare__dict(self, other):
        '''
        cannot just do self.__dict__ == other.__dict__ since
        '''
        for key, val in self.__dict__.items():
            o_val = other.__dict__[key]

            if isinstance(val, np.ndarray):
                if np.any(val != o_val):
                    return False
            else:
                if val != o_val:
                    return False

        return True

    def __eq__(self, other):
        '''
        need to explicitly compare __dict__
        However, PyGnome initializes two OilProps object when invoked from the
        WebGnomeClient, there is an sql alchemy object embedded in _r_oil
        which maybe different. To avoid comparing the sqlalchemy object that
        is part of the raw oil record, this works as follows:

        1. check if self.__dict__ == other.__dict__
        2. if above fails, then check if the tojson() for both OilProps objects
        match. This assumes that both objects contain tojson()
        '''
        if type(self) != type(other):
            return False

        if self._compare__dict(other):
            return True

        try:
            return self.tojson() == other.tojson()
        except Exception:
            return False

    def __ne__(self, other):
        return not self == other

    def __deepcopy__(self, memo):
        '''
        The _r_oil object should not be copied - it should just be referenced
        to create the OilProps copy. The database record itself does not need
        to be a deepcopy - both OilProps objects can reference the same
        database record
        '''
        c_op = self.__class__(self.record)

        if c_op != self:
            '''
            Attributes are currently derived from _r_oil object. Unless the
            user changes 'mass_fractions', 'boiling_point', 'molecular_weight'
            after initialization, the two objects should be equal
            '''
            for attr in c_op.__dict__:
                if getattr(self, attr) != getattr(c_op, attr):
                    setattr(c_op, attr,
                            copy.deepcopy(getattr(self, attr), memo))

        return c_op

    def _init_sara(self):
        '''
        initialize self._sara as a numpy array. The information is structured
        in increasing boiling points as:
            ['Saturates', boiling_point_0, mass_fraction, density, molWt]
            ['Aromatics', boiling_point_0, mass_fraction, density, molWt]
            ['Saturates', boiling_point_1, mass_fraction, density, molWt]
            ['Aromatics', boiling_point_1, mass_fraction, density, molWt]
            ...
            ['Resins', boiling_point_terminal, mass_fraction, density, molWt]
            ['Asphaltenes', boiling_point_terminal, mass_fraction, density, molWt]

        Omit components that have 0 mass fraction
        '''
        all_comp = list(chain(*[sorted(list(g), key=lambda s: s.sara_type,
                                       reverse=True)
                                for _k, g
                                in groupby(sorted(self.record.sara_fractions,
                                                  key=lambda s: s.ref_temp_k),
                                           lambda x: x.ref_temp_k)]
                              ))

        all_dens = list(chain(*[sorted(list(g), key=lambda s: s.sara_type,
                                       reverse=True)
                                for _k, g
                                in groupby(sorted(self.record.sara_densities,
                                                  key=lambda s: s.ref_temp_k),
                                           lambda x: x.ref_temp_k)]
                              ))

        all_mw = list(chain(*[sorted(list(g), key=lambda s: s.sara_type,
                                     reverse=True)
                              for _k, g
                              in groupby(sorted(self.record.molecular_weights,
                                                key=lambda s: s.ref_temp_k),
                                         lambda x: x.ref_temp_k)]
                            ))

        items = []
        sum_frac = 0.
        for comp, dens, mol_wt in zip_longest(all_comp, all_dens, all_mw):
            if (comp.ref_temp_k != comp.ref_temp_k or
                    comp.sara_type != comp.sara_type):
                msg = "mismatch in sara_fractions and sara_densities tables"
                raise ValueError(msg)

            if comp.fraction > 0.0:
                if hasattr(mol_wt, 'g_mol'):
                    mw = mol_wt.g_mol
                else:
                    # We currently don't have estimation methods for
                    # resin and asphaltene molecular weights, so they
                    # don't exist in the oil record.
                    if comp.sara_type == 'Resins':
                        # recommended avg. value from Bill is 800 g/mol
                        mw = 800.0
                    elif comp.sara_type == 'Asphaltenes':
                        # recommended avg. value from Bill is 1000 g/mol
                        mw = 1000.0

                items.append((comp.sara_type, comp.ref_temp_k, comp.fraction,
                              dens.density, mw))
                sum_frac += comp.fraction

        self._sara = np.asarray(items, dtype=sara_dtype)

        if not np.isclose(self._sara[:]['fraction'].sum(), 1.0):
            msg = ("mass fraction sum: {0} - sum should be approximately 1.0"
                   .format(self._sara[:]['fraction'].sum()))
            raise ValueError(msg)
