"""Provides WISDEM's WOMBAT API."""


from warnings import warn

import openmdao.api as om
from wombat import Simulation
from wombat.core.library import DEFAULT_DATA, load_yaml, load_weather


class Wombat(om.Group):
    """WOMBAT simulation API class for WISDEM API."""

    def initialize(self):
        """Initializes the API connections."""
        self.options.declare("scenario", default=None)  # NOTE: config file without the extension
        self.options.declare("config", default=None)
        
        # TODO: Should the random seed or generator be provided to the interface?

        self.set_input_defaults("years", 20, units="yr")
        self.set_input_defaults("workday_start", 7, units="h")
        self.set_input_defaults("workday_end", 19, units="h")
        self.set_input_defaults("port_distance", 50, units="km")
        self.set_input_defaults("n_ctv", 3, units="unitless")
        self.set_input_defaults("n_hlv", 1, units="unitless")
        self.set_input_defaults("n_tugboat", 2, units="unitless")
        self.set_input_defaults("port_workday_start", 6, units="h")
        self.set_input_defaults("port_workday_end", 18, units="h")
        self.set_input_defaults("n_port_crews", 2, units="unitless")
        self.set_input_defaults("max_port_operations", 2, units="unitless")
        self.set_input_defaults("repair_port_distance", 116, units="km")
        self.set_input_defaults("maintenance_start", None, units="unitless")
        self.set_input_defaults("non_operational_start", None, units="unitless")
        self.set_input_defaults("non_operational_end", None, units="unitless")
        self.set_input_defaults("reduced_speed_start", None, units="unitless")
        self.set_input_defaults("reduced_speed_end", None, units="unitless")
        self.set_input_defaults("reduced_speed", None, units="km/h")
        self.set_input_defaults("project_capacity", None, units="MW")
        self.set_input_defaults("turbine_capex_kw", None, units="$/kW")
        self.set_input_defaults("turbine_capacity", None, units="MW")
        
        self.set_discrete_input_defaults("layout", None, units="unitless")
        self.set_discrete_input_defaults("random_seed", 42, units="unitless")


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
        self.options.declare("config", default=None)

    def load_scenario_config(self) -> dict:
        config["name"] = "wisdem_wombat"
        scenario = self.options["scenario"]
        if scenario == "land":
            raise NotImplementedError("No default land-based data is available for WOMBAT.")
        
        if scenario == "fixed":
            config = load_yaml(DEFAULT_DATA / "project/config", "osw_fixed.yaml")
                
            config["vessels"] = {
                "ctv": load_yaml(DEFAULT_DATA / "vessels", "ctv.yaml"),
                "hlv": load_yaml(DEFAULT_DATA / "vessels", "hlv.yaml"),
                "cab": load_yaml(DEFAULT_DATA / "vessels", "cab.yaml"),
                "dsv": load_yaml(DEFAULT_DATA / "vessels", "dsv.yaml"),
            }
            config["fixed_costs"] = load_yaml(DEFAULT_DATA / "project/config", "osw_fixed_bottom_costs.yaml")
            config["substations"] = {"base_substation": load_yaml(DEFAULT_DATA / "substations", "fixed_offshore_substation.yaml")}
            config["cables"] = {
                "base_array": load_yaml(DEFAULT_DATA / "cables", "array_osw.yaml"),
                "base_export": load_yaml(DEFAULT_DATA / "cables", "export_osw.yaml"),
            }
            config["turbines"] = {"base_turbine": load_yaml(DEFAULT_DATA / "turbines", "fixed_osw_turbine.yaml")}
            config["weather"] = load_weather(DEFAULT_DATA / "weather/era5_40.0N_72.5W_1990_2020.csv")[["datetime", "windspeed", "waveheight"]]
            config["end_year"] = 2020      
        elif scenario == "floating":
            config = load_yaml(DEFAULT_DATA / "project/config", "osw_floating.yaml")
            config["vessels"] = {
                "ctv": load_yaml(DEFAULT_DATA / "vessels", "ctv.yaml"),
                "cab": load_yaml(DEFAULT_DATA / "vessels", "cab.yaml"),
                "dsv": load_yaml(DEFAULT_DATA / "vessels", "dsv.yaml"),
                "tugboat": load_yaml(DEFAULT_DATA / "vessels", "tugboat.yaml"),
            }
            config["fixed_costs"] = load_yaml(DEFAULT_DATA / "project/config", "osw_floating_costs.yaml")
            config["substations"] = {"base_substation": load_yaml(DEFAULT_DATA / "substations", "floating_offshore_substation.yaml")}
            config["cables"] = {
                "base_array": load_yaml(DEFAULT_DATA / "cables", "array_osw.yaml"),
                "base_export": load_yaml(DEFAULT_DATA / "cables", "export_osw.yaml"),
            }
            config["turbines"] = {"base_turbine": load_yaml(DEFAULT_DATA / "turbines", "floating_osw_turbine.yaml")}
            config["port"] = load_yaml(DEFAULT_DATA / "project/port", "base_port.yaml")
            config["weather"] = load_weather(DEFAULT_DATA / "weather/era5_41.0N_125.0W_1989_2019.csv")[["datetime", "windspeed", "waveheight"]]
            config["end_year"] = 2019
        
        config["layout_coords"] = "distance"
        return config

    def setup(self):
        """Define all the inputs."""

        base_config = self.load_scenario_config()
        self.add_discrete_input("config", base_config, desc="Base configuration dictionary.")

        self.add_discrete_input("years", 20, desc="Number of years to simulation the operations and maintenance phase of the farm lifecycle")
        self.add_discrete_input("workday_start", 7, desc="Hour of the day where any work-related activities begin")
        self.add_discrete_input("workday_end", 19, desc="Hour of the day where any work-related activities end")
        self.add_input("equipment_dispatch_distance", 50, units="km", desc="Distance, in km, that servicing equipment must travel daily to reach the wind farm")
        self.add_discrete_input("n_ctv", 3, desc="Number of crew transfer vessels that should be made available to the wind farm.")
        self.add_discrete_input("n_hlv", 1, desc="Number of heavy lift vessels that should be made available to the wind farm (fixed-bottom simulations only)")
        self.add_discrete_input("n_tugboat", 2, desc="Number of tugboat groups that should be available to the port to tow floating turbines to port and back")
        self.add_discrete_input("port_workday_start", 6, desc="Hour of the day where any work-related activities begin for port-side repairs")
        self.add_discrete_input("port_workday_end", 18, desc="Hour of the day where any work-related activities end for port-side repairs")
        self.add_discrete_input("n_port_crews", 2, desc="Number of port-side crews available to work on simultaneous repairs for any at-port turbine")
        self.add_discrete_input("max_port_operations", 2, desc="Number of turbines that can be at port at once")
        self.add_input("repair_port_distance", 116, units="km", desc="Distance, in km, that tugboats must travel to reach the wind farm for tow-to-port repairs")
        self.add_discrete_input("maintenance_start", None, desc="Date of first maintenance event to determine regular interval timing. Can be set to prior to the starting year to ensure staggered starts.")
        self.add_discrete_input("non_operational_start", None, desc="Starting date, in MM/DD format, for an annual period where the site is inaccessible")
        self.add_discrete_input("non_operational_end", None, desc="Ending date, in MM/DD format, for an annual period where the site is inaccessible")
        self.add_discrete_input("reduced_speed_start", None, desc="Starting date, in MM/DD format, for an annual period where traveling speed is reduced")
        self.add_discrete_input("reduced_speed_end", None, desc="Ending date, in MM/DD format, for an annual period where traveling speed is reduced")
        self.add_input("reduced_speed", None, units="km/h", desc="Reduced speed applied to servicing equipment in the reduced speed period")
        self.add_input("project_capacity", None, units="MW", desc="Total wind farm capacity")
        self.add_input("turbine_capex_kw", None, units="$/kW", desc="Turbine CapEx per kW of nameplate capacity")
        self.add_input("turbine_capacity", None, units="W", desc="Turbine nameplate capacity")

        # TODO: need to ensure a passthrough for customized layouts (ORBIT or Ard integration)
        self.add_discrete_input("layout", None, desc="Tabular wind farm layout generated from ORBIT")
        
        # Turbine modifications
        # All defaults are -1 to indicate the WOMBAT defaults will be used
        self.add_input("power_converter_minor_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("power_converter_minor_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("power_converter_minor_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("power_converter_major_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("power_converter_major_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("power_converter_major_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("power_converter_replacement_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("power_converter_replacement_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("power_converter_replacement_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        
        self.add_input("electrical_system_minor_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("electrical_system_minor_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("electrical_system_minor_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("electrical_system_major_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("electrical_system_major_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("electrical_system_major_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("electrical_system_replacement_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("electrical_system_replacement_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("electrical_system_replacement_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        
        self.add_input("hydraulic_pitch_system_minor_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("hydraulic_pitch_system_minor_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("hydraulic_pitch_system_minor_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("hydraulic_pitch_system_major_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("hydraulic_pitch_system_major_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("hydraulic_pitch_system_major_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("hydraulic_pitch_system_replacement_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("hydraulic_pitch_system_replacement_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("hydraulic_pitch_system_replacement_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        
        self.add_input("ballast_pump_minor_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("ballast_pump_minor_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("ballast_pump_minor_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        
        self.add_input("yaw_system_minor_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("yaw_system_minor_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("yaw_system_minor_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("yaw_system_major_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("yaw_system_major_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("yaw_system_major_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("yaw_system_replacement_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("yaw_system_replacement_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("yaw_system_replacement_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        
        self.add_input("rotor_blades_minor_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("rotor_blades_minor_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("rotor_blades_minor_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("rotor_blades_major_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("rotor_blades_major_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("rotor_blades_major_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("rotor_blades_replacement_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("rotor_blades_replacement_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("rotor_blades_replacement_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        
        self.add_input("generator_minor_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("generator_minor_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("generator_minor_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("generator_major_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("generator_major_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("generator_major_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("generator_replacement_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("generator_replacement_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("generator_replacement_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        
        self.add_input("drive_train_minor_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("drive_train_minor_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("drive_train_minor_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("drive_train_major_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("drive_train_major_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("drive_train_major_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("drive_train_replacement_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("drive_train_replacement_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("drive_train_replacement_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        
        self.add_input("anchor_minor_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("anchor_minor_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("anchor_minor_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("anchor_major_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("anchor_major_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("anchor_major_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("anchor_replacement_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("anchor_replacement_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("anchor_replacement_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        
        self.add_input("mooring_lines_minor_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("mooring_lines_minor_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("mooring_lines_minor_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("mooring_lines_major_repair_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("mooring_lines_major_repair_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("mooring_lines_major_repair_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("mooring_lines_replacement_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("mooring_lines_replacement_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("mooring_lines_replacement_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")
        self.add_input("mooring_lines_buoyancy_module_replacement_scale", -1, units="unitless", desc="1 / mean time between failure (years)")
        self.add_input("mooring_lines_buoyancy_module_replacement_time", -1, units="hours", desc="Number of hours to complete the repair")
        self.add_input("mooring_lines_buoyancy_module_replacement_materials", 1, units="$", desc="Total cost of materials used to complete the repair. If between 0 and 1, the cost is proportional to the turbine CapEx.")


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

    def create_layout(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """Creates the WOMBAT layout DataFrame from the ORBIT outputs."""
        layout = discrete_outputs["layout"]
        layout[["type", "subassembly", "upstream_cable"]] = ["turbine", "base_turbine", "base_array"]
        layout.loc[
            layout.id.isin(layout.substation_id),
            ["type", "subassembly", "upstream_cable"]
        ] = ["substation", "base_substation", "base_export"]
        return layout

    def compile_inputs(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """Creates the WOMBAT configuration file."""
        
        scenario = self.options["scenario"]
        config = inputs["config"]
        config["name"] = discrete_inputs["name"]
        config["layout"] = create_layout(inputs, outputs, discrete_inputs, discrete_outputs)
        config["weather"] = discrete_inputs["weather"]
        config["workday_start"] = discrete_inputs["workday_start"]
        config["workday_end"] = discrete_inputs["workday_end"]
        config["project_capacity"] = inputs["project_capacity"]
        config["port_distance"] = inputs["equipment_dispatch_distance"]
        config["maintenance_start"] = discrete_inputs["maintenance_start"]
        config["non_operational_start"] = discrete_inputs["non_operational_start"]
        config["non_operational_end"] = discrete_inputs["non_operational_end"]
        config["reduced_speed_start"] = discrete_inputs["reduced_speed_start"]
        config["reduced_speed_end"] = discrete_inputs["reduced_speed_end"]
        config["reduced_speed"] = discrete_inputs["reduced_speed"]
        
        if scenario == "floating":
            config["service_equipment"] = [
                [discrete_inputs["n_ctv"], "ctv"],
                [1, "dsv"],
                [1, "cab"],
            ]
            config["port"]["tugboats"] = [discrete_inputs["n_tugboats"], "tugboat"]
            config["port"]["site_distance"] = inputs["repair_port_distance"]
            config["port"]["workday_start"] = discrete_inputs["port_workday_start"]
            config["port"]["workday_end"] = discrete_inputs["port_workday_end"]
            config["port"]["max_operations"] = discrete_inputs["port_max_operations"]
            config["port"]["n_crews"] = discrete_inputs["n_port_crews"]
            config["port"]["max_operations"] = discrete_inputs["port_max_operations"]
        elif scenario == "fixed":
            config["service_equipment"] = [
                [discrete_inputs["n_ctv"], "ctv"],
                [discrete_inputs["n_hlv"], "hlv"],
                [1, "dsv"],
                [1, "cab"],
            ]

        config["start_year"] = config["end_year"] - discrete_inputs["years"] + 1
        
        config["random_seed"] = discrete_inputs["random_seed"]
        config["random_generator"] = discrete_inputs["random_generator"]
        config["cables"] = inputs["cables"]
        config["turbines"] = inputs["turbines"]
        
        original_capacity = config["turbines"]["base_turbine"]["capacity_kw"]
        original_capex = config["turbines"]["base_turbine"]["capex_kw"]
        config["turbines"]["base_turbine"]["capacity_kw"] = inputs["turbine_capacity"] / 1000.0
        config["turbines"]["base_turbine"]["capex_kw"] = inputs["turbine_capex_kw"]

        turbine_capex = original_capacity * original_capex
        for subassembly in config["turbines"]["base_turbine"].items():
            if subassembly in ("capacity_kw", "capex_kw", "power_curve", "n_stacks", "stack_capacity_kw"):
                continue
            for i, maintenance in enumerate(config["turbines"]["base_turbine"][subassembly]["maintenance"]):
                config["turbines"]["base_turbine"][subassembly]["maintenance"][i]["materials"] /= turbine_capex
            for i, failure in enumerate(config["turbines"]["base_turbine"][subassembly]["failures"]):
                config["turbines"]["base_turbine"][subassembly]["failures"][i]["materials"] /= turbine_capex

        # TODO: determine if any of the scale, time, or cost components should be removed, and how
        # they should connect to WISDEM's other modeled values
        if (val := inputs["power_converter_minor_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["power_converter"]["failures"][0]["scale"] = val
        if (val := inputs["power_converter_minor_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["power_converter"]["failures"][0]["time"] = val
        if (val := inputs["power_converter_minor_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["power_converter"]["failures"][0]["materials"] = val
        if (val := inputs["power_converter_major_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["power_converter"][1]["scale"] = val
        if (val := inputs["power_converter_major_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["power_converter"][1]["time"] = val
        if (val := inputs["power_converter_major_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["power_converter"][1]["materials"] = val
        if (val := inputs["power_converter_replacement_scale"]) > -1:
            config["turbines"]["base_turbine"]["power_converter"][2]["scale"] = val
        if (val := inputs["power_converter_replacement_time"]) > -1:
            config["turbines"]["base_turbine"]["power_converter"][2]["time"] = val
        if (val := inputs["power_converter_replacement_materials"]) > -1:
            config["turbines"]["base_turbine"]["power_converter"][2]["materials"] = val

        if (val := inputs["electrical_system_minor_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["electrical_system"]["failures"][0]["scale"] = val
        if (val := inputs["electrical_system_minor_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["electrical_system"]["failures"][0]["time"] = val
        if (val := inputs["electrical_system_minor_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["electrical_system"]["failures"][0]["materials"] = val
        if (val := inputs["electrical_system_major_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["electrical_system"][1]["scale"] = val
        if (val := inputs["electrical_system_major_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["electrical_system"][1]["time"] = val
        if (val := inputs["electrical_system_major_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["electrical_system"][1]["materials"] = val
        if (val := inputs["electrical_system_replacement_scale"]) > -1:
            config["turbines"]["base_turbine"]["electrical_system"][2]["scale"] = val
        if (val := inputs["electrical_system_replacement_time"]) > -1:
            config["turbines"]["base_turbine"]["electrical_system"][2]["time"] = val
        if (val := inputs["electrical_system_replacement_materials"]) > -1:
            config["turbines"]["base_turbine"]["electrical_system"][2]["materials"] = val

        if (val := inputs["hydraulic_pitch_system_minor_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["hydraulic_pitch_system"]["failures"][0]["scale"] = val
        if (val := inputs["hydraulic_pitch_system_minor_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["hydraulic_pitch_system"]["failures"][0]["time"] = val
        if (val := inputs["hydraulic_pitch_system_minor_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["hydraulic_pitch_system"]["failures"][0]["materials"] = val
        if (val := inputs["hydraulic_pitch_system_major_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["hydraulic_pitch_system"][1]["scale"] = val
        if (val := inputs["hydraulic_pitch_system_major_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["hydraulic_pitch_system"][1]["time"] = val
        if (val := inputs["hydraulic_pitch_system_major_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["hydraulic_pitch_system"][1]["materials"] = val
        if (val := inputs["hydraulic_pitch_system_replacement_scale"]) > -1:
            config["turbines"]["base_turbine"]["hydraulic_pitch_system"][2]["scale"] = val
        if (val := inputs["hydraulic_pitch_system_replacement_time"]) > -1:
            config["turbines"]["base_turbine"]["hydraulic_pitch_system"][2]["time"] = val
        if (val := inputs["hydraulic_pitch_system_replacement_materials"]) > -1:
            config["turbines"]["base_turbine"]["hydraulic_pitch_system"][2]["materials"] = val

        if (val := inputs["ballast_pump_minor_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["ballast_pump"]["failures"][0]["scale"] = val
        if (val := inputs["ballast_pump_minor_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["ballast_pump"]["failures"][0]["time"] = val
        if (val := inputs["ballast_pump_minor_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["ballast_pump"]["failures"][0]["materials"] = val

        if (val := inputs["yaw_system_minor_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["yaw_system"]["failures"][0]["scale"] = val
        if (val := inputs["yaw_system_minor_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["yaw_system"]["failures"][0]["time"] = val
        if (val := inputs["yaw_system_minor_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["yaw_system"]["failures"][0]["materials"] = val
        if (val := inputs["yaw_system_major_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["yaw_system"][1]["scale"] = val
        if (val := inputs["yaw_system_major_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["yaw_system"][1]["time"] = val
        if (val := inputs["yaw_system_major_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["yaw_system"][1]["materials"] = val
        if (val := inputs["yaw_system_replacement_scale"]) > -1:
            config["turbines"]["base_turbine"]["yaw_system"][2]["scale"] = val
        if (val := inputs["yaw_system_replacement_time"]) > -1:
            config["turbines"]["base_turbine"]["yaw_system"][2]["time"] = val
        if (val := inputs["yaw_system_replacement_materials"]) > -1:
            config["turbines"]["base_turbine"]["yaw_system"][2]["materials"] = val

        if (val := inputs["rotor_blades_minor_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["rotor_blades"]["failures"][0]["scale"] = val
        if (val := inputs["rotor_blades_minor_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["rotor_blades"]["failures"][0]["time"] = val
        if (val := inputs["rotor_blades_minor_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["rotor_blades"]["failures"][0]["materials"] = val
        if (val := inputs["rotor_blades_major_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["rotor_blades"][1]["scale"] = val
        if (val := inputs["rotor_blades_major_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["rotor_blades"][1]["time"] = val
        if (val := inputs["rotor_blades_major_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["rotor_blades"][1]["materials"] = val
        if (val := inputs["rotor_blades_replacement_scale"]) > -1:
            config["turbines"]["base_turbine"]["rotor_blades"][2]["scale"] = val
        if (val := inputs["rotor_blades_replacement_time"]) > -1:
            config["turbines"]["base_turbine"]["rotor_blades"][2]["time"] = val
        if (val := inputs["rotor_blades_replacement_materials"]) > -1:
            config["turbines"]["base_turbine"]["rotor_blades"][2]["materials"] = val

        if (val := inputs["generator_minor_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["generator"]["failures"][0]["scale"] = val
        if (val := inputs["generator_minor_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["generator"]["failures"][0]["time"] = val
        if (val := inputs["generator_minor_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["generator"]["failures"][0]["materials"] = val
        if (val := inputs["generator_major_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["generator"][1]["scale"] = val
        if (val := inputs["generator_major_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["generator"][1]["time"] = val
        if (val := inputs["generator_major_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["generator"][1]["materials"] = val
        if (val := inputs["generator_replacement_scale"]) > -1:
            config["turbines"]["base_turbine"]["generator"][2]["scale"] = val
        if (val := inputs["generator_replacement_time"]) > -1:
            config["turbines"]["base_turbine"]["generator"][2]["time"] = val
        if (val := inputs["generator_replacement_materials"]) > -1:
            config["turbines"]["base_turbine"]["generator"][2]["materials"] = val

        if (val := inputs["drive_train_minor_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["drive_train"]["failures"][0]["scale"] = val
        if (val := inputs["drive_train_minor_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["drive_train"]["failures"][0]["time"] = val
        if (val := inputs["drive_train_minor_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["drive_train"]["failures"][0]["materials"] = val
        if (val := inputs["drive_train_major_repair_scale"]) > -1:
            config["turbines"]["base_turbine"]["drive_train"][1]["scale"] = val
        if (val := inputs["drive_train_major_repair_time"]) > -1:
            config["turbines"]["base_turbine"]["drive_train"][1]["time"] = val
        if (val := inputs["drive_train_major_repair_materials"]) > -1:
            config["turbines"]["base_turbine"]["drive_train"][1]["materials"] = val
        if (val := inputs["drive_train_replacement_scale"]) > -1:
            config["turbines"]["base_turbine"]["drive_train"][2]["scale"] = val
        if (val := inputs["drive_train_replacement_time"]) > -1:
            config["turbines"]["base_turbine"]["drive_train"][2]["time"] = val
        if (val := inputs["drive_train_replacement_materials"]) > -1:
            config["turbines"]["base_turbine"]["drive_train"][2]["materials"] = val

        if scenario == "floating":
            if (val := inputs["anchor_minor_repair_scale"]) > -1:
                config["turbines"]["base_turbine"]["anchor"]["failures"][0]["scale"] = val
            if (val := inputs["anchor_minor_repair_time"]) > -1:
                config["turbines"]["base_turbine"]["anchor"]["failures"][0]["time"] = val
            if (val := inputs["anchor_minor_repair_materials"]) > -1:
                config["turbines"]["base_turbine"]["anchor"]["failures"][0]["materials"] = val
            if (val := inputs["anchor_major_repair_scale"]) > -1:
                config["turbines"]["base_turbine"]["anchor"][1]["scale"] = val
            if (val := inputs["anchor_major_repair_time"]) > -1:
                config["turbines"]["base_turbine"]["anchor"][1]["time"] = val
            if (val := inputs["anchor_major_repair_materials"]) > -1:
                config["turbines"]["base_turbine"]["anchor"][1]["materials"] = val
            if (val := inputs["anchor_replacement_scale"]) > -1:
                config["turbines"]["base_turbine"]["anchor"][2]["scale"] = val
            if (val := inputs["anchor_replacement_time"]) > -1:
                config["turbines"]["base_turbine"]["anchor"][2]["time"] = val
            if (val := inputs["anchor_replacement_materials"]) > -1:
                config["turbines"]["base_turbine"]["anchor"][2]["materials"] = val
            
            if (val := inputs["mooring_lines_minor_repair_scale"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines"]["failures"][0]["scale"] = val
            if (val := inputs["mooring_lines_minor_repair_time"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines"]["failures"][0]["time"] = val
            if (val := inputs["mooring_lines_minor_repair_materials"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines"]["failures"][0]["materials"] = val
            if (val := inputs["mooring_lines_major_repair_scale"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines"][1]["scale"] = val
            if (val := inputs["mooring_lines_major_repair_time"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines"][1]["time"] = val
            if (val := inputs["mooring_lines_major_repair_materials"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines"][1]["materials"] = val
            if (val := inputs["mooring_lines_replacement_scale"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines"][2]["scale"] = val
            if (val := inputs["mooring_lines_replacement_time"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines"][2]["time"] = val
            if (val := inputs["mooring_lines_replacement_materials"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines"][2]["materials"] = val
            if (val := inputs["mooring_lines_buoyancy_module_replacement_replacement_scale"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines_buoyancy_module_replacement"][3]["scale"] = val
            if (val := inputs["mooring_lines_buoyancy_module_replacement_replacement_time"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines_buoyancy_module_replacement"][3]["time"] = val
            if (val := inputs["mooring_lines_buoyancy_module_replacement_replacement_materials"]) > -1:
                config["turbines"]["base_turbine"]["mooring_lines_buoyancy_module_replacement"][3]["materials"] = val

        return config

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """Creates and runs the project, then gathers the results."""

        library_path = self.options["library_path"]
        config = self.compile_inputs(inputs, outputs, discrete_inputs, discrete_outputs)

        sim = Simulation(library_path=library_path, config=config)

        sim.run(save_metrics_inputs=False, delete_logs=True)
        metrics = sim.metrics

        frequency = "project"
        capacity_kW = sim.project_capacity * 1000
        opex = metrics.opex(frequency, by_category=True)
        outputs["total_opex"] = opex.OpEx
        outputs["total_opex_kw"] = outputs["total_opex"] / capacity_kW
        
        outputs["time_availability"] = metrics.time_based_availability(frequency="project", by="windfarm").squeeze()
        outputs["energy_availability"] = metrics.production_based_availability(frequency="project", by="windfarm").squeeze()
        outputs["net_capacity_factor"] = metrics.capacity_factor(which="net", frequency="project", by="windfarm").squeeze()
        outputs["gross_capacity_factor"] = metrics.capacity_factor(which="gross", frequency="project", by="windfarm").squeeze()
        outputs["scheduled_task_completion_rate"] = metrics.task_completion_rate(which="scheduled", frequency="project").squeeze()
        outputs["unscheduled_task_completion_rate"] = metrics.task_completion_rate(which="unscheduled", frequency="project").squeeze()
        outputs["combined_task_completion_rate"] = metrics.task_completion_rate(which="both", frequency="project").squeeze()
        outputs["total_equipment_cost"] = metrics.equipment_costs(frequency="project", by_equipment=False).squeeze()
        
        # TODO: Do we need individual vessel/vehicle breakdowns?
        # TODO: are dataframe outputs ok, or different type?
        outputs["equipment_cost_breakdown"] = metrics.equipment_costs(frequency="project", by_equipment=False)
        outputs["equipment_utilization_rate"] =  metrics.service_equipment_utilization(frequency="project")
        outputs["equipment_dispatch_summary"] = metrics.dispatch_summary(frequency="project")
        outputs["vessel_crew_hours_at_sea"] = metrics.vessel_crew_hours_at_sea(frequency="project", by_equipment=True).squeeze()
        
        outputs["vessel_crew_hours_at_sea"] = metrics.vessel_crew_hours_at_sea(frequency="project", by_equipment=False).squeeze()
        outputs["total_tows"] = metrics.number_of_tows(frequency="project").squeeze()
        outputs["direct_labor"] = metrics.labor_costs(frequency="project", by_type=False).squeeze()
        outputs["materials_by_subassembly"] = metrics.component_costs(frequency="project", by_category=False, by_action=False)  # TODO: are dataframe outputs ok, or different type?
        outputs["total_materials"] = outputs["materials_by_subassembly"].values.sum()
        
        fixed_costs = metrics.project_fixed_costs(frequency="project", resolution="medium")
        outputs["indirect_labor"] = fixed_costs[["labor"]].squeeze()
        outputs["total_fixed_costs"] = fixed_costs.values.sum()
        
        outputs["equipment_opex"] = opex.equipment_cost
        
        # NOTE: emissions need assumptions, so it's excluded
        # TODO: process times, request summary, power production, NPV (requires discount rate and offtake)
