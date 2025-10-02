"""Provides WISDEM's WOMBAT API."""


from warnings import warn

import openmdao.api as om

from wombat import Simulation


class Wombat(om.Group):
    """WOMBAT simulation API class for WISDEM API."""

    def initialize(self):
        """Initializes the API connections."""
        # self.options.declare("floating", default=False)
        # self.options.declare("jacket", default=False)
        # self.options.declare("jacket_legs", default=0)
        ...

    def setup(self):
        """Define all input variables from all models."""
        self.set_input_defaults("wtiv", "example_wtiv")
        self.set_input_defaults("boem_review_cost", 0.0, units="USD")

        self.add_subsystem(
            "wombat",
            WombatWisdem(
                # floating=self.options["floating"],
                # jacket=self.options["jacket"],
                # jacket_legs=self.options["jacket_legs"],
            ),
            promotes=["*"],
        )


class WombatWisdem(om.ExplicitComponent):
    """ORBIT-WISDEM Fixed Substructure API."""

    def initialize(self):
        """Initialize the API."""
        # self.options.declare("floating", default=False)
        # self.options.declare("jacket", default=False)
        # self.options.declare("jacket_legs", default=0)
        ...

    def setup(self):
        """Define all the inputs."""
        
        self.add_discrete_input(
            "wtiv",
            "example_wtiv",
            desc=(
                "Vessel configuration to use for installation of foundations"
                " and turbines."
            ),
        )

        self.add_input(
            "boem_review_cost",
            0.0,
            units="USD",
            desc=(
                "Cost for additional review by U.S. Dept of Interior Bureau"
                " of Ocean Energy Management (BOEM)"
            ),
        )

        # Outputs
        self.add_output(
            "bos_capex",
            0.0,
            units="USD",
            desc="Sum of system and installation capex",
        )

    def compile_orbit_config_file(
        self, inputs, outputs, discrete_inputs, discrete_outputs,
    ):
        """Compiles the ORBIT configuration dictionary."""

        config = {}

        self._wombat_config = config
        return config

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """Creates and runs the project, then gathers the results."""

        config = self.compile_orbit_config_file(
            inputs, outputs, discrete_inputs, discrete_outputs,
        )

        project = ProjectManager(config)
        project.run()

        # The ORBIT version of total_capex includes turbine capex, so we do our own sum of
        # the parts here that wisdem doesn't account for
        capacity_kW = 1e3 * inputs["turbine_rating"] * discrete_inputs["number_of_turbines"]
        outputs["bos_capex"] = project.bos_capex
