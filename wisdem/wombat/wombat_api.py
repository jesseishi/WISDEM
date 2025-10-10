"""Provides WISDEM's WOMBAT API."""


from warnings import warn

import openmdao.api as om

from wombat import Simulation


class Wombat(om.Group):
    """WOMBAT simulation API class for WISDEM API."""

    def initialize(self):
        """Initializes the API connections."""
        self.options.declare("scenario", default=None)  # NOTE: config file without the extension
        self.options.declare("library_path", default="default")  # TODO: default libraries coming soon

        # TODO: Should the random seed or generator be provided to the interface?

    def setup(self):
        """Define all input variables from all models."""
        self.add_subsystem(
            "wombat",
            WombatWisdem(
                scenario=self.options["scenario"],
                libary_path=self.options["library_path"],
            ),
            promotes=["*"],
        )


class WombatWisdem(om.ExplicitComponent):
    """WOMBAT-WISDEM Fixed Substructure API."""

    def initialize(self):
        """Initialize the API."""
        self.options.declare("scenario", default=None)
        self.options.declare("library_path", default="default")

    def setup(self):
        """Define all the inputs."""

        # TODO: need to ensure a passthrough for customized layouts (ORBIT or Ard integration)
        
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
            "total_opex",
            0.0,
            units="USD",
            desc=(
                "Total operational expenditure (fixed costs, port fees, labor, servicing"
                " equipment, and materials)"
            ),
        )
        self.add_output(
            "total_opex_kw",
            0.0,
            units="USD",
            desc=(
                "Total operational expenditure (fixed costs, port fees, labor, servicing"
                " equipment, and materials) per kW"
            ),
        )
        self.add_output(
            "materials_opex",
            0.0,
            units="USD",
            desc="Cost of all replaced and consumable materials for repairs and servicing",
        )
        self.add_output(
            "equipment_opex",
            0.0,
            units="USD",
            desc="Direct cost for renting and operating servicing equipment",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """Creates and runs the project, then gathers the results."""

        library_path = self.options["library_path"]

        try:
            config = Path(self.options["scenario"]).with_suffix(".yaml")
            sim = Simulation(library_path=library_path, config)
        except FileNotFoundError:
            config = config.with_suffix(".yml")
            sim = Simulation(library_path=library_path, config)

        sim.run(save_metrics_inputs=False, delete_logs=True)
        sim.env.cleanup()
        metrics = sim.metrics

        frequency = "project"
        capacity_kW = sim.project_capacity * 1000
        opex = metrics.opex(frequency, by_category=True)
        outputs["total_opex"] = opex.OpEx
        outputs["total_opex_kw"] = outputs["total_opex"] / capacity_kw
        outputs["materials_opex"] = opex.materials_cost
        outputs["equipment_opex"] = opex.equipment_cost
        # TODO: total_labor_cost, fixed costs, port_fees
