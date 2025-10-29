"""Provides WISDEM's WOMBAT API."""


from warnings import warn

import openmdao.api as om

from wombat import Simulation
from wombat.core.library import DEFAULT, load_yaml


class Wombat(om.Group):
    """WOMBAT simulation API class for WISDEM API."""

    def initialize(self):
        """Initializes the API connections."""
        self.options.declare("scenario", default=None)  # NOTE: config file without the extension
        
        # TODO: Should the random seed or generator be provided to the interface?

        self.set_input_defaults("name", "wisdem-wombat")
        self.set_input_defaults("weather", None, units="")  # TODO: load default file?
        self.set_input_defaults("workday_start", 6, units="h")
        self.set_input_defaults("workday_end", 6, units="h")
        self.set_input_defaults("inflation_rate", 0, units="percent")

        # Fixed costs
        # TODO: update for expected, most common scenario
        # TODO: pathway for fixed, floating, and land-based
        self.set_input_defaults("labor", 0, units="USD/kW", desc="")
        self.set_input_defaults("operations_management_administration", 0, units="USD/kW", desc="")
        self.set_input_defaults("operating_facilities", 0, units="USD/kW", desc="")
        self.set_input_defaults("insurance", 0, units="USD/kW", desc="")
        self.set_input_defaults("annual_leases_fees", 0, units="USD/kW", desc="")

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

        self.add_discrete_input("name", "wisdem-wombat", desc="Name of the simulation")
        self.add_discrete_input("weather", None, units="")  # TODO: load default file?
        self.add_discrete_input("workday_start", 6, units="h")
        self.add_discrete_input("workday_end", 6, units="h")
        self.add_input("inflation_rate", 0, units="percent")

        # Fixed costs
        # TODO: update for expected, most common scenario
        # TODO: pathway for fixed, floating, and land-based
        self.add_input("labor", 0, units="USD/kW", desc="")
        self.add_input("operations_management_administration", 0, units="USD/kW", desc="")
        self.add_input("operating_facilities", 0, units="USD/kW", desc="")
        self.add_input("insurance", 0, units="USD/kW", desc="")
        self.add_input("annual_leases_fees", 0, units="USD/kW", desc="")

        
        self.set_input_defaults("layout", None)
        self.set_input_defaults("project_capacity", None, units="MW")
        
        # Optional primary inputs
        self.add_input("port_distance", None, units="km")
        self.add_discrete_input("layout_coords", None, units="")  # TODO: load default file?
        self.add_discrete_input("fixed_costs", None, units="")  # TODO: load default file?
        self.add_discrete_input("port", None, units="")  # TODO: load default file?
        self.add_discrete_input("start_year", None, units="yr")
        self.add_discrete_input("end_year", None, units="yr")
        self.add_discrete_input("maintenance_start", None, units="") # TODO: no date-time units?
        self.add_discrete_input("non_operational_start", None, units="") # TODO: no date-time units?
        self.add_discrete_input("non_operational_end", None, units="") # TODO: no date-time units?
        self.add_discrete_input("reduced_speed_start", None, units="") # TODO: no date-time units?
        self.add_discrete_input("reduced_speed_end", None, units="") # TODO: no date-time units?
        self.add_discrete_input("reduced_speed", None, units="")
        self.add_discrete_input("random_seed", None, units="")
        self.add_discrete_input("random_generator", None, units="")
        
        self.add_input("service_equipment", None, units="")  # TODO: load default file?
        self.add_discrete_input("cables", None, units="")  # TODO: load default file?
        self.add_discrete_input("substations", None, units="")  # TODO: load default file?
        self.add_discrete_input("turbines", None, units="")  # TODO: load default file?
        self.add_discrete_input("vessels", None, units="")  # TODO: load default file?


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

    def _compile_scenario_inputs(self, inputs, discrete_inputs) -> dict:
        scenario = self.options["scenario"]
        if scenario == "land":
            additional_config = {
                "vessels": {},
                "service_equipment": {},
                "fixed_costs": {},
                "substations": {},
                "cables": {},
            }
            raise NotImplementedError("No default land-based data is available for WOMBAT.")
        
        if scenario == "fixed":
            additional_config = {
                "vessels": {
                    "ctv": load_yaml(DEFAULT / "vessels", "ctv.yaml"),
                    "hlv": load_yaml(DEFAULT / "vessels", "hlv.yaml"),
                    "cab": load_yaml(DEFAULT / "vessels", "cab.yaml"),
                    "dsv": load_yaml(DEFAULT / "vessels", "dsv.yaml"),
                },
                "service_equipment": [["ctv", 3], "hlv", "cab", "dsv"],
                "fixed_costs": {},  # TODO: udpate when COWER data is updated
                "substations": {
                    "base_substation": load_yaml(DEFAULT / "substations", "fixed_offshore_substation.yaml")
                },
                "cables": {
                    "base_array": load_yaml(DEFAULT / "cables", "array_osw.yaml"),
                    "base_export": load_yaml(DEFAULT / "cables", "export_osw.yaml"),
                },
            }
            return additional_confg
        
        if scenario == "floating":
            additional_config = {
                "vessels": {
                    "ctv": load_yaml(DEFAULT / "vessels", "ctv.yaml"),
                    "cab": load_yaml(DEFAULT / "vessels", "cab.yaml"),
                    "dsv": load_yaml(DEFAULT / "vessels", "dsv.yaml"),
                    "tug1": load_yaml(DEFAULT / "vessels", "tugboat1.yaml"),
                    "tug2": load_yaml(DEFAULT / "vessels", "tugboat2.yaml"),
                },
                "service_equipment": [["ctv", 3], "cab", "dsv"],
                "fixed_costs": {},  # TODO: udpate when COWER data is updated
                "substations": {
                    "base_substation": load_yaml(DEFAULT / "substations", "floating_offshore_substation.yaml")
                },
                "cables": {
                    "base_array": load_yaml(DEFAULT / "cables", "array_osw.yaml"),
                    "base_export": load_yaml(DEFAULT / "cables", "export_osw.yaml"),
                },
                "port": load_yaml(DEFAULT / "port", "morro_bay_port.yaml"),
            }
            return additional_confg

    def compile_inputs(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """Creates the WOMBAT configuration file."""
        
        config = {
            "name": discrete_inputs[""],
            # "layout": inputs[""],
            # "layout_coords": discrete_inputs[""],
            # "weather": inputs[""],
            "workday_start": discrete_inputs[""],
            "workday_end": discrete_inputs[""],
            "inflation_rate": inputs[""],
            "project_capacity": inputs[""],
            "start_year": inputs[""],
            "end_year": inputs[""],
            "port_distance": inputs[""],
            "maintenance_start": inputs[""],
            "non_operational_start": inputs[""],
            "non_operational_end": inputs[""],
            "reduced_speed_start": inputs[""],
            "reduced_speed_end": inputs[""],
            "reduced_speed": inputs[""],
            "random_seed": inputs[""],
            "random_generator": inputs[""],
            "cables": inputs[""],
            "turbines": inputs[""],
            **self._compile_scenario_inputs(inputs, discrete_inputs)
        }

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
