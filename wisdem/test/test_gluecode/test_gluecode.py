import os
import unittest

from wisdem.glue_code.runWISDEM import run_wisdem

test_dir = (
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
    + os.sep
    + "examples"
    + os.sep
    + "02_reference_turbines"
    + os.sep
)
fname_modeling_options = test_dir + "modeling_options.yaml"
fname_analysis_options = test_dir + "analysis_options.yaml"


class TestRegression(unittest.TestCase):
    def test5MW(self):
        ## NREL 5MW
        fname_wt_input = test_dir + "nrel5mw.yaml"

        wt_opt, _, _ = run_wisdem(fname_wt_input, fname_modeling_options, fname_analysis_options)

        self.assertAlmostEqual(wt_opt["rotorse.rp.AEP"][0] * 1.0e-6, 23.657430209476644, 2)
        self.assertAlmostEqual(
            wt_opt["rotorse.blade_mass"][0], 16419.8666989212, 2
        )  # new value: improved interpolation
        self.assertAlmostEqual(wt_opt["financese.lcoe"][0] * 1.0e3, 53.6013221527, 1)
        self.assertAlmostEqual(wt_opt["rotorse.rs.tip_pos.tip_deflection"][0], 4.4583909369, 1)
        self.assertAlmostEqual(wt_opt["towerse.z_param"][-1], 87.7, 2)

    def test15MW(self):
        ## IEA 15MW
        fname_wt_input = test_dir + "IEA-15-240-RWT.yaml"
        wt_opt, _, _ = run_wisdem(fname_wt_input, fname_modeling_options, fname_analysis_options)

        self.assertAlmostEqual(wt_opt["rotorse.rp.AEP"][0] * 1.0e-6, 77.90375792369237, 1)
        self.assertAlmostEqual(
            wt_opt["rotorse.blade_mass"][0], 68208.64259481194, 1
        )  # new value: improved interpolation
        self.assertAlmostEqual(wt_opt["financese.lcoe"][0] * 1.0e3, 82.92352084553283, 1)
        self.assertAlmostEqual(wt_opt["rotorse.rs.tip_pos.tip_deflection"][0], 25.831844078972203, 1)
        self.assertAlmostEqual(wt_opt["towerse.z_param"][-1], 144.386, 3)

    def test3p4MW(self):
        ## IEA 3.4MW
        fname_wt_input = test_dir + "IEA-3p4-130-RWT.yaml"
        wt_opt, _, _ = run_wisdem(fname_wt_input, fname_modeling_options, fname_analysis_options)

        self.assertAlmostEqual(wt_opt["rotorse.rp.AEP"][0] * 1.0e-6, 13.5859495051, 1)
        self.assertAlmostEqual(
            wt_opt["rotorse.blade_mass"][0], 14528.4450828773, 1
        )  # new value: improved interpolation
        self.assertAlmostEqual(wt_opt["financese.lcoe"][0] * 1.0e3, 39.5223317758, 1)
        self.assertAlmostEqual(wt_opt["rotorse.rs.tip_pos.tip_deflection"][0], 8.0836109779, 1)
        self.assertAlmostEqual(wt_opt["towerse.z_param"][-1], 108.0, 3)


if __name__ == "__main__":
    unittest.main()
