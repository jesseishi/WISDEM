import numpy as np
from math import gamma
from openmdao.api import ExplicitComponent

# ---------------------
# Map Design Variables to Discretization
# ---------------------

class PDFBase(ExplicitComponent):
    """probability distribution function"""
    def initialize(self):
        self.options.declare('nspline')
    def setup(self):
        nspline = self.options['nspline']
        self.add_input('x', shape=nspline)

        self.add_output('f', shape=nspline)


class CDFBase(ExplicitComponent):
    """cumulative distribution function"""
    def initialize(self):
        self.options.declare('nspline')
    def setup(self):
        nspline = self.options['nspline']

        self.add_input('x', shape=nspline,  units='m/s', desc='corresponding reference height')
        self.add_input('k', shape=1, desc='shape or form factor')

        self.add_output('F', shape=nspline, units='m/s', desc='magnitude of wind speed at each z location')


class WeibullCDF(CDFBase):
    def setup(self):
        super(WeibullCDF, self).setup()
        """Weibull cumulative distribution function"""

        self.add_input('A', shape=1, desc='scale factor')
        
        self.declare_partials('F', 'x')

    def compute(self, inputs, outputs):
        outputs['F'] = 1.0 - np.exp(-(inputs['x']/inputs['A'])**inputs['k'])

    def compute_partials(self, inputs, J):

        x = inputs['x']
        A = inputs['A']
        k = inputs['k']
        
        J['F', 'x'] = np.diag(np.exp(-(x/A)**k)*(x/A)**(k-1)*k/A)
        


class WeibullWithMeanCDF(CDFBase):
    def setup(self):
        super(WeibullWithMeanCDF, self).setup()
        """Weibull cumulative distribution function"""

        self.add_input('xbar', shape=1, units='m/s', desc='mean value of distribution')

        self.declare_partials('F', 'x')
        
    def compute(self, inputs, outputs):

        A = inputs['xbar'] / gamma(1.0 + 1.0/inputs['k'])

        outputs['F'] = 1.0 - np.exp(-(inputs['x']/A)**inputs['k'])


    def compute_partials(self, inputs, J):

        x = inputs['x']
        k = inputs['k']
        A = inputs['xbar'] / gamma(1.0 + 1.0/k)
        dx = np.diag(np.exp(-(x/A)**k)*(x/A)**(k-1)*k/A)
        dxbar = -np.exp(-(x/A)**k)*(x/A)**(k-1)*k*x/A**2/gamma(1.0 + 1.0/k)
        
        J['F', 'x'] = dx
        J['F', 'xbar'] = dxbar

        

class RayleighCDF(CDFBase):
    def setup(self):
        super(RayleighCDF,  self).setup()

        # variables
        self.add_input('xbar', shape=1, units='m/s', desc='reference wind speed (usually at hub height)')

        self.declare_partials('F', 'x')

    def compute(self, inputs, outputs):

        outputs['F'] = 1.0 - np.exp(-np.pi/4.0*(inputs['x']/inputs['xbar'])**2)

    def compute_partials(self, inputs, J):

        x = inputs['x']
        xbar = inputs['xbar']
        dx = np.diag(np.exp(-np.pi/4.0*(x/xbar)**2)*np.pi*x/(2.0*xbar**2))
        dxbar = -np.exp(-np.pi/4.0*(x/xbar)**2)*np.pi*x**2/(2.0*xbar**3)
        
        J['F', 'x'] = dx
        J['F', 'xbar'] = dxbar
        
        
