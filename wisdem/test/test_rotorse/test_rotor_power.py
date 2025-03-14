import os
import unittest

import numpy as np
import openmdao.api as om
import numpy.testing as npt

import wisdem.rotorse.rotor_power as rp

# Load in airfoil and blade shape inputs for NREL 5MW
ARCHIVE = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + "regulation.npz"
NPZFILE = np.load(ARCHIVE)


def fillprob(prob, n_pc, n_span):
    prob.setup()
    for k in NPZFILE.files:
        prob[k] = NPZFILE[k]

    prob.set_val("v_min", 4.0, units="m/s")
    prob.set_val("v_max", 25.0, units="m/s")
    prob.set_val("rated_power", 5e6, units="W")
    prob.set_val("omega_min", 0.0, units="rpm")
    prob.set_val("omega_max", 100.0, units="rpm")
    prob.set_val("control_maxTS", 90.0, units="m/s")
    prob.set_val("tsr_operational", 10.0)
    prob.set_val("control_pitch", 0.0, units="deg")
    prob.set_val("gearbox_efficiency", 0.975)
    prob.set_val("generator_efficiency", 0.975 * np.ones(n_pc))
    prob.set_val("lss_rpm", np.linspace(0.1, 100, n_pc))
    prob.set_val("drivetrainType", "GEARED")

    prob.set_val("Rhub", 1.0, units="m")
    prob.set_val("Rtip", 70.0, units="m")
    prob.set_val("hub_height", 100.0, units="m")
    prob.set_val("precone", 0.0, units="deg")
    prob.set_val("tilt", 0.0, units="deg")
    prob.set_val("yaw", 0.0, units="deg")
    prob.set_val("precurve", np.zeros(n_span), units="m")
    prob.set_val("precurveTip", 0.0, units="m")
    prob.set_val("presweep", np.zeros(n_span), units="m")
    prob.set_val("presweepTip", 0.0, units="m")

    prob.set_val("shearExp", 0.25)
    prob.set_val("nSector", 4)
    prob.set_val("tiploss", True)
    prob.set_val("hubloss", True)
    prob.set_val("wakerotation", True)
    prob.set_val("usecd", True)

    return prob


class TestServo(unittest.TestCase):
    def testGust(self):
        inputs = {}
        outputs = {}
        discrete_inputs = {}
        discrete_outputs = {}

        myobj = rp.GustETM(std=2.5)

        inputs["V_mean"] = 10.0 * np.ones(1)
        inputs["V_hub"] = 15.0 * np.ones(1)
        discrete_inputs["turbulence_class"] = "A"
        myobj.compute(inputs, outputs, discrete_inputs, discrete_outputs)
        sigma = 0.32 * (0.072 * 8.0 * 3.5 + 10.0)
        expect = 15.0 + 2.5 * sigma
        self.assertEqual(outputs["V_gust"], expect)

        # Test lower case
        discrete_inputs["turbulence_class"] = "c"
        myobj.compute(inputs, outputs, discrete_inputs, discrete_outputs)
        sigma = 0.24 * (0.072 * 8.0 * 3.5 + 10.0)
        expect = 15.0 + 2.5 * sigma
        self.assertEqual(outputs["V_gust"], expect)

        # Test bad class
        discrete_inputs["turbulence_class"] = "d"
        try:
            myobj.compute(inputs, outputs, discrete_inputs, discrete_outputs)
        except ValueError:
            self.assertTrue(True)

    def testStall(self):
        inputs = {}
        outputs = {}

        myobj = rp.NoStallConstraint()

        (n_span, n_aoa, n_Re, n_tab) = NPZFILE["airfoils_cl"].shape

        inputs["airfoils_cl"] = NPZFILE["airfoils_cl"]
        inputs["airfoils_cd"] = NPZFILE["airfoils_cd"]
        inputs["airfoils_cm"] = NPZFILE["airfoils_cm"]
        inputs["airfoils_aoa"] = NPZFILE["airfoils_aoa"]
        inputs["min_s"] = 0.25
        r = NPZFILE["r"]
        r_hub = NPZFILE["r"][0]
        r_tip = NPZFILE["r"][-1]
        inputs["s"] = (r - r_hub) / (r_tip - r_hub)
        inputs["aoa_along_span"] = 7. * np.ones(len(r))
        inputs["stall_margin"] = np.array([ 3. ])

        modeling_options = {}
        modeling_options["WISDEM"] = {}
        modeling_options["WISDEM"]["RotorSE"] = {}
        modeling_options["WISDEM"]["RotorSE"]["n_span"] = n_span
        modeling_options["WISDEM"]["RotorSE"]["n_aoa"] = n_aoa
        modeling_options["WISDEM"]["RotorSE"]["n_Re"] = n_Re
        modeling_options["WISDEM"]["RotorSE"]["n_tab"] = n_tab

        outputs["stall_angle_along_span"] = np.zeros(len(r))
        outputs["no_stall_constraint"] = np.zeros(len(r))

        myobj.compute(inputs, outputs)

        ref_no_stall_constraint = np.array([0.        , 0.        ,
                             0.        , 0.        , 0.        ,
            0.        , 0.        , 0.77009342, 0.80530567, 0.83153911,
            0.85911535, 0.89343367, 0.97975052, 1.07592565, 1.11609355,
            1.13403252, 1.14891246, 1.14568097, 1.14014398, 1.12239983,
            1.07454375, 1.07115146, 1.07115146, 1.07115146, 1.07115146,
            1.07115146, 1.07115146, 1.07115146, 1.07115146, 1.07115146])
        
        ref_stall_angle_along_span = np.array([1.00000000e-06, 6.24217266e+01, 
                                               3.04993295e+00, 3.86108996e+01,
                2.45945626e+01, 1.84737813e+01, 1.35576462e+01, 1.29854375e+01,
                1.24176450e+01, 1.20258925e+01, 1.16398805e+01, 1.11927727e+01,
                1.02066799e+01, 9.29432250e+00, 8.95982239e+00, 8.81808929e+00,
                8.70388331e+00, 8.72843333e+00, 8.77082210e+00, 8.90948100e+00,
                9.30627534e+00, 9.33574791e+00, 9.33574791e+00, 9.33574791e+00,
                9.33574791e+00, 9.33574791e+00, 9.33574791e+00, 9.33574791e+00,
                9.33574791e+00, 9.33574791e+00])

        npt.assert_almost_equal(outputs["no_stall_constraint"], ref_no_stall_constraint)
        npt.assert_almost_equal(outputs["stall_angle_along_span"], ref_stall_angle_along_span)

    def testRegulationTrajectory(self):
        prob = om.Problem(reports=False)

        (n_span, n_aoa, n_Re, n_tab) = NPZFILE["airfoils_cl"].shape
        n_pc = 22

        modeling_options = {}
        modeling_options["WISDEM"] = {}
        modeling_options["WISDEM"]["RotorSE"] = {}
        modeling_options["WISDEM"]["RotorSE"]["n_span"] = n_span
        modeling_options["WISDEM"]["RotorSE"]["n_aoa"] = n_aoa
        modeling_options["WISDEM"]["RotorSE"]["n_Re"] = n_Re
        modeling_options["WISDEM"]["RotorSE"]["n_tab"] = n_tab
        modeling_options["WISDEM"]["RotorSE"]["regulation_reg_III"] = True
        modeling_options["WISDEM"]["RotorSE"]["n_pc"] = n_pc
        modeling_options["WISDEM"]["RotorSE"]["n_pc_spline"] = n_pc

        prob.model.add_subsystem(
            "powercurve", rp.RegulatedPowerCurve(modeling_options=modeling_options), promotes=["*"]
        )
        prob = fillprob(prob, n_pc, n_span)

        # All reg 2: no maxTS, no max rpm, no power limit
        prob["omega_max"] = 1e3
        prob["control_maxTS"] = 1e5
        prob["rated_power"] = 1e16
        prob.run_model()

        grid0 = np.cumsum(np.abs(np.diff(np.cos(np.linspace(-np.pi / 4.0, np.pi / 2.0, n_pc)))))
        grid1 = (grid0 - grid0[0]) / (grid0[-1] - grid0[0])
        V_expect0 = grid1 * (prob["v_max"] - prob["v_min"]) + prob["v_min"]
        V_spline = np.linspace(prob["v_min"], prob["v_max"], n_pc)
        irated = 12

        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        npt.assert_equal(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_tsr)
        npt.assert_equal(prob["pitch"], np.zeros(n_pc))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_allclose(prob["Cp"], prob["Cp"][0])
        npt.assert_allclose(prob["Cp_aero"], prob["Cp_aero"][0])
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp, myCp[0], rtol=1e-6)
        self.assertGreater(myCp[0], 0.4)
        self.assertGreater(0.5, myCp[0])
        npt.assert_allclose(myCp, prob["Cp"], rtol=1e-6)
        npt.assert_array_less(prob["P"][:-2], prob["P"][1:-1])
        npt.assert_array_less(prob["Q"][:-2], prob["Q"][1:-1])
        npt.assert_array_less(prob["T"][:-2], prob["T"][1:-1])
        self.assertEqual(prob["rated_V"], V_expect1[-1])
        self.assertAlmostEqual(prob["rated_Omega"][0], Omega_tsr[-1], 5)
        self.assertEqual(prob["rated_pitch"], 0.0)

        # Test no maxTS, max rpm, no power limit
        prob["omega_max"] = 15.0
        prob["control_maxTS"] = 1e5
        prob["rated_power"] = 1e16
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.minimum(Omega_tsr, 15.0)
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_equal(prob["pitch"][:irated], 0.0)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][(irated + 1) :]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:-2], prob["P"][1:-1])
        npt.assert_array_less(prob["Q"][:-2], prob["Q"][1:-1])
        npt.assert_array_less(prob["T"][:-2], prob["T"][1:-1])
        self.assertAlmostEqual(prob["rated_V"], V_expect1[-1], 3)
        self.assertAlmostEqual(prob["rated_Omega"][0], 15.0)
        self.assertEqual(prob["rated_pitch"], 0.0)
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[:irated], myCp[0])
        npt.assert_allclose(myCp[:irated], prob["Cp"][:irated])

        # Test maxTS, no max rpm, no power limit
        prob["omega_max"] = 1e3
        prob["control_maxTS"] = 105.0
        prob["rated_power"] = 1e16
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        # V_expect1[irated] = 105./10.
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.minimum(Omega_tsr, 105.0 / 70.0 / 2 / np.pi * 60)
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_equal(prob["pitch"][:irated], 0.0)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][irated:]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:-2], prob["P"][1:-1])
        npt.assert_array_less(prob["Q"][:-2], prob["Q"][1:-1])
        npt.assert_array_less(prob["T"][:-2], prob["T"][1:-1])
        self.assertEqual(prob["rated_V"], V_expect1[-1])
        self.assertAlmostEqual(prob["rated_Omega"][0], Omega_expect[-1])
        self.assertEqual(prob["rated_pitch"], 0.0)
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[:irated], myCp[0])
        npt.assert_allclose(myCp[:irated], prob["Cp"][:irated])

        # Test no maxTS, no max rpm, power limit
        prob["omega_max"] = 1e3
        prob["control_maxTS"] = 1e4
        prob["rated_power"] = 5e6
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.minimum(Omega_tsr, prob["rated_Omega"])
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_equal(prob["pitch"][:irated], 0.0)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][(irated + 1) :]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:irated], prob["P"][1 : (irated + 1)])
        npt.assert_allclose(prob["P"][irated:], 5e6, rtol=1e-4, atol=0)
        # npt.assert_array_less(prob['Q'], prob['Q'][1:])
        npt.assert_array_less(prob["T"], prob["T"][irated] + 1e-1)
        # print('RATED T',prob["T"][irated])
        # self.assertEqual(prob['rated_V'], V_expect1[-1])
        self.assertAlmostEqual(prob["rated_Omega"][0], Omega_expect[-1])
        self.assertEqual(prob["rated_pitch"], 0.0)
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[:irated], myCp[0])
        npt.assert_allclose(myCp[:irated], prob["Cp"][:irated])

        # Test min & max rpm, no power limit
        prob["omega_min"] = 7.0
        prob["omega_max"] = 15.0
        prob["control_maxTS"] = 1e5
        prob["rated_power"] = 1e16
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        # V_expect1[irated] = 15.*70*2*np.pi/(10.*60.)
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.maximum(np.minimum(Omega_tsr, 15.0), 7.0)
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][Omega_expect != Omega_tsr]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:-2], prob["P"][1:-1])
        npt.assert_array_less(prob["Q"][:-2], prob["Q"][1:-1])
        npt.assert_array_less(prob["T"][:-2], prob["T"][1:-1])
        self.assertEqual(prob["rated_V"], V_expect1[-1])
        self.assertAlmostEqual(prob["rated_Omega"][0], 15.0)
        self.assertEqual(prob["rated_pitch"], 0.0)
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[Omega_expect == Omega_tsr], myCp[6])
        npt.assert_allclose(myCp[Omega_expect == Omega_tsr], prob["Cp"][Omega_expect == Omega_tsr])

        # Test min & max rpm, normal power
        prob["omega_min"] = 7.0
        prob["omega_max"] = 14.0
        prob["control_maxTS"] = 1e5
        prob["rated_power"] = 5e6
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        # V_expect1[irated] = 14.*70*2*np.pi/(10.*60.)
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.maximum(np.minimum(Omega_tsr, 14.0), 7.0)
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][Omega_expect != Omega_tsr]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:irated], prob["P"][1 : (irated + 1)])
        npt.assert_allclose(prob["P"][irated:], 5e6, rtol=1e-4, atol=0)
        npt.assert_array_less(prob["T"], prob["T"][irated] + 1e-1)
        self.assertAlmostEqual(prob["rated_Omega"][0], 14.0)
        self.assertLess(0.0, prob["rated_pitch"])
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[Omega_expect == Omega_tsr][:-1], myCp[6])
        npt.assert_allclose(myCp[Omega_expect == Omega_tsr][:-1], prob["Cp"][Omega_expect == Omega_tsr][:-1])

        # Test fixed pitch
        prob["omega_min"] = 0.0
        prob["omega_max"] = 15.0
        prob["control_maxTS"] = 1e5
        prob["rated_power"] = 1e16
        prob["control_pitch"] = 5.0
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        # V_expect1[irated] = 15.*70*2*np.pi/(10.*60.)
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.minimum(Omega_tsr, 15.0)
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_equal(prob["pitch"][:irated], 5.0)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][irated:]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:-2], prob["P"][1:-1])
        npt.assert_array_less(prob["Q"][:-2], prob["Q"][1:-1])
        npt.assert_array_less(prob["T"][:-2], prob["T"][1:-1])
        self.assertAlmostEqual(prob["rated_V"], V_expect1[-1], 3)
        self.assertAlmostEqual(prob["rated_Omega"][0], 15.0)
        self.assertEqual(prob["rated_pitch"], 5.0)
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[:irated], myCp[0])
        npt.assert_allclose(myCp[:irated], prob["Cp"][:irated])

    def testRegulationTrajectoryNoRegion3(self):
        prob = om.Problem(reports=False)

        # Load in airfoil and blade shape inputs for NREL 5MW
        (n_span, n_aoa, n_Re, n_tab) = NPZFILE["airfoils_cl"].shape
        n_pc = 22

        modeling_options = {}
        modeling_options["WISDEM"] = {}
        modeling_options["WISDEM"]["RotorSE"] = {}
        modeling_options["WISDEM"]["RotorSE"]["n_span"] = n_span
        modeling_options["WISDEM"]["RotorSE"]["n_aoa"] = n_aoa
        modeling_options["WISDEM"]["RotorSE"]["n_Re"] = n_Re
        modeling_options["WISDEM"]["RotorSE"]["n_tab"] = n_tab
        modeling_options["WISDEM"]["RotorSE"]["regulation_reg_III"] = False
        modeling_options["WISDEM"]["RotorSE"]["n_pc"] = n_pc
        modeling_options["WISDEM"]["RotorSE"]["n_pc_spline"] = n_pc

        prob.model.add_subsystem(
            "powercurve", rp.RegulatedPowerCurve(modeling_options=modeling_options), promotes=["*"]
        )
        prob = fillprob(prob, n_pc, n_span)

        # All reg 2: no maxTS, no max rpm, no power limit
        prob["omega_max"] = 1e3
        prob["control_maxTS"] = 1e5
        prob["rated_power"] = 1e16
        prob.run_model()

        grid0 = np.cumsum(np.abs(np.diff(np.cos(np.linspace(-np.pi / 4.0, np.pi / 2.0, n_pc)))))
        grid1 = (grid0 - grid0[0]) / (grid0[-1] - grid0[0])
        V_expect0 = grid1 * (prob["v_max"] - prob["v_min"]) + prob["v_min"]
        V_spline = np.linspace(prob["v_min"], prob["v_max"], n_pc)
        irated = 12

        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        npt.assert_equal(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_tsr)
        npt.assert_equal(prob["pitch"], np.zeros(n_pc))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_allclose(prob["Cp"], prob["Cp"][0], rtol=1e-6)
        npt.assert_allclose(prob["Cp_aero"], prob["Cp_aero"][0])
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp, myCp[0], rtol=1e-6)
        self.assertGreater(myCp[0], 0.4)
        self.assertGreater(0.5, myCp[0])
        npt.assert_allclose(myCp, prob["Cp"], rtol=1e-6)
        npt.assert_array_less(prob["P"][:-2], prob["P"][1:-1])
        npt.assert_array_less(prob["Q"][:-2], prob["Q"][1:-1])
        npt.assert_array_less(prob["T"][:-2], prob["T"][1:-1])
        self.assertEqual(prob["rated_V"], V_expect1[-1])
        self.assertAlmostEqual(prob["rated_Omega"][0], Omega_tsr[-1], 5)
        self.assertEqual(prob["rated_pitch"], 0.0)

        # Test no maxTS, no max rpm, power limit
        prob["omega_max"] = 1e3
        prob["control_maxTS"] = 1e4
        prob["rated_power"] = 5e6
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.minimum(Omega_tsr, prob["rated_Omega"])
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_equal(prob["pitch"], 0.0)
        # npt.assert_array_less(0.0, np.abs(prob['pitch'][(irated+1):]))
        npt.assert_allclose(prob["Cp"][: (irated + 1)], prob["Cp_aero"][: (irated + 1)] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:irated], prob["P"][1 : (irated + 1)])
        npt.assert_allclose(prob["P"][irated:], 5e6, rtol=1e-6, atol=0)
        # npt.assert_equal(prob['Q'][(irated+1):], prob['Q'][irated])
        npt.assert_equal(prob["T"][(irated + 1) :], 0.0)
        npt.assert_array_less(prob["T"], prob["T"][irated] + 1e-1)
        # self.assertEqual(prob['rated_V'], V_expect1[-1])
        self.assertAlmostEqual(prob["rated_Omega"][0], Omega_expect[-1])
        self.assertEqual(prob["rated_pitch"], 0.0)
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[:irated], myCp[0])
        npt.assert_allclose(myCp[:irated], prob["Cp"][:irated])

    def testRegulationTrajectory_PeakShaving(self):
        prob = om.Problem(reports=False)

        (n_span, n_aoa, n_Re, n_tab) = NPZFILE["airfoils_cl"].shape
        n_pc = 22

        modeling_options = {}
        modeling_options["WISDEM"] = {}
        modeling_options["WISDEM"]["RotorSE"] = {}
        modeling_options["WISDEM"]["RotorSE"]["n_span"] = n_span
        modeling_options["WISDEM"]["RotorSE"]["n_aoa"] = n_aoa
        modeling_options["WISDEM"]["RotorSE"]["n_Re"] = n_Re
        modeling_options["WISDEM"]["RotorSE"]["n_tab"] = n_tab
        modeling_options["WISDEM"]["RotorSE"]["regulation_reg_III"] = True
        modeling_options["WISDEM"]["RotorSE"]["n_pc"] = n_pc
        modeling_options["WISDEM"]["RotorSE"]["n_pc_spline"] = n_pc

        prob.model.add_subsystem(
            "powercurve", rp.RegulatedPowerCurve(modeling_options=modeling_options), promotes=["*"]
        )
        prob = fillprob(prob, n_pc, n_span)

        # All reg 2: no maxTS, no max rpm, no power limit
        prob["omega_max"] = 1e3
        prob["control_maxTS"] = 1e5
        prob["rated_power"] = 1e16
        prob["ps_percent"] = 0.8
        prob.run_model()

        grid0 = np.cumsum(np.abs(np.diff(np.cos(np.linspace(-np.pi / 4.0, np.pi / 2.0, n_pc)))))
        grid1 = (grid0 - grid0[0]) / (grid0[-1] - grid0[0])
        V_expect0 = grid1 * (prob["v_max"] - prob["v_min"]) + prob["v_min"]
        V_spline = np.linspace(prob["v_min"], prob["v_max"], n_pc)
        irated = 12

        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        npt.assert_equal(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_tsr)
        npt.assert_equal(prob["pitch"], np.zeros(n_pc))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_allclose(prob["Cp"], prob["Cp"][0], rtol=1e-6)
        npt.assert_allclose(prob["Cp_aero"], prob["Cp_aero"][0])
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp, myCp[0], rtol=1e-6)
        self.assertGreater(myCp[0], 0.4)
        self.assertGreater(0.5, myCp[0])
        npt.assert_allclose(myCp, prob["Cp"], rtol=1e-6)
        npt.assert_array_less(prob["P"][:-2], prob["P"][1:-1])
        npt.assert_array_less(prob["Q"][:-2], prob["Q"][1:-1])
        npt.assert_array_less(prob["T"][:-2], prob["T"][1:-1])
        self.assertEqual(prob["rated_V"], V_expect1[-1])
        self.assertAlmostEqual(prob["rated_Omega"][0], Omega_tsr[-1], 5)
        self.assertEqual(prob["rated_pitch"], 0.0)

        # Test no maxTS, max rpm, no power limit
        prob["omega_max"] = 15.0
        prob["control_maxTS"] = 1e5
        prob["rated_power"] = 1e16
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.minimum(Omega_tsr, 15.0)
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_equal(prob["pitch"][:irated], 0.0)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][(irated + 1) :]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:-2], prob["P"][1:-1])
        npt.assert_array_less(prob["Q"][:-2], prob["Q"][1:-1])
        npt.assert_array_less(prob["T"][:-2], prob["T"][1:-1])
        self.assertAlmostEqual(prob["rated_V"], V_expect1[-1], 3)
        self.assertAlmostEqual(prob["rated_Omega"][0], 15.0)
        self.assertEqual(prob["rated_pitch"], 0.0)
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[:irated], myCp[0])
        npt.assert_allclose(myCp[:irated], prob["Cp"][:irated])

        # Test maxTS, no max rpm, no power limit
        prob["omega_max"] = 1e3
        prob["control_maxTS"] = 105.0
        prob["rated_power"] = 1e16
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        # V_expect1[irated] = 105./10.
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.minimum(Omega_tsr, 105.0 / 70.0 / 2 / np.pi * 60)
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_equal(prob["pitch"][:irated], 0.0)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][irated:]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:-2], prob["P"][1:-1])
        npt.assert_array_less(prob["Q"][:-2], prob["Q"][1:-1])
        npt.assert_array_less(prob["T"][:-2], prob["T"][1:-1])
        self.assertEqual(prob["rated_V"], V_expect1[-1])
        self.assertAlmostEqual(prob["rated_Omega"][0], Omega_expect[-1])
        self.assertEqual(prob["rated_pitch"], 0.0)
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[:irated], myCp[0])
        npt.assert_allclose(myCp[:irated], prob["Cp"][:irated])

        # Test no maxTS, no max rpm, power limit
        prob["omega_max"] = 1e3
        prob["control_maxTS"] = 1e4
        prob["rated_power"] = 5e6
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.minimum(Omega_tsr, prob["rated_Omega"])
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"][:irated], Omega_expect[:irated])
        npt.assert_equal(prob["pitch"][: (irated - 1)], 0.0)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][irated:]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:irated], prob["P"][1 : (irated + 1)])
        npt.assert_allclose(prob["P"][irated:], 5e6, rtol=1e-4, atol=0)
        npt.assert_array_less(prob["T"], 0.8 * 880899)  # From print out in first test
        self.assertAlmostEqual(prob["rated_Omega"][0], Omega_expect[-1])
        self.assertGreater(prob["rated_pitch"], 0.0)
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[: (irated - 1)], myCp[0])
        npt.assert_allclose(myCp[: (irated - 1)], prob["Cp"][: (irated - 1)])

        # Test min & max rpm, no power limit
        prob["omega_min"] = 7.0
        prob["omega_max"] = 15.0
        prob["control_maxTS"] = 1e5
        prob["rated_power"] = 1e16
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        # V_expect1[irated] = 15.*70*2*np.pi/(10.*60.)
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.maximum(np.minimum(Omega_tsr, 15.0), 7.0)
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][Omega_expect != Omega_tsr]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:-2], prob["P"][1:-1])
        npt.assert_array_less(prob["Q"][:-2], prob["Q"][1:-1])
        npt.assert_array_less(prob["T"][:-2], prob["T"][1:-1])
        self.assertEqual(prob["rated_V"], V_expect1[-1])
        self.assertAlmostEqual(prob["rated_Omega"][0], 15.0)
        self.assertEqual(prob["rated_pitch"], 0.0)
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[Omega_expect == Omega_tsr], myCp[6])
        npt.assert_allclose(myCp[Omega_expect == Omega_tsr], prob["Cp"][Omega_expect == Omega_tsr])

        # Test min & max rpm, normal power
        prob["omega_min"] = 7.0
        prob["omega_max"] = 14.0
        prob["control_maxTS"] = 1e5
        prob["rated_power"] = 5e6
        prob.run_model()
        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        # V_expect1[irated] = 14.*70*2*np.pi/(10.*60.)
        Omega_tsr = V_expect1 * 10 * 60 / 70.0 / 2.0 / np.pi
        Omega_expect = np.maximum(np.minimum(Omega_tsr, 14.0), 7.0)
        npt.assert_allclose(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())
        npt.assert_allclose(prob["Omega"], Omega_expect)
        npt.assert_array_less(0.0, np.abs(prob["pitch"][Omega_expect != Omega_tsr]))
        npt.assert_array_almost_equal(prob["Cp"], prob["Cp_aero"] * 0.975 * 0.975)
        npt.assert_array_less(prob["P"][:irated], prob["P"][1 : (irated + 1)])
        npt.assert_allclose(prob["P"][irated:], 5e6, rtol=1e-4, atol=0)
        npt.assert_array_less(prob["T"], 0.8 * 880899)  # From print out in first test
        self.assertAlmostEqual(prob["rated_Omega"][0], 14.0)
        self.assertLess(0.0, prob["rated_pitch"])
        myCp = prob["P"] / (0.5 * 1.225 * V_expect1**3.0 * np.pi * 70**2)
        npt.assert_allclose(myCp[Omega_expect == Omega_tsr][:-1], myCp[6])
        npt.assert_allclose(myCp[Omega_expect == Omega_tsr][:-1], prob["Cp"][Omega_expect == Omega_tsr][:-1])

    def testRegulationTrajectory_reindex(self):
        prob = om.Problem(reports=False)

        debug_archive = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + "debug.npz"
        debug_npz = np.load(debug_archive)

        (n_span, n_aoa, n_Re, n_tab) = debug_npz["airfoils_cl"].shape
        n_pc = 50

        modeling_options = {}
        modeling_options["WISDEM"] = {}
        modeling_options["WISDEM"]["RotorSE"] = {}
        modeling_options["WISDEM"]["RotorSE"]["n_span"] = n_span
        modeling_options["WISDEM"]["RotorSE"]["n_aoa"] = n_aoa
        modeling_options["WISDEM"]["RotorSE"]["n_Re"] = n_Re
        modeling_options["WISDEM"]["RotorSE"]["n_tab"] = n_tab
        modeling_options["WISDEM"]["RotorSE"]["regulation_reg_III"] = True
        modeling_options["WISDEM"]["RotorSE"]["n_pc"] = n_pc
        modeling_options["WISDEM"]["RotorSE"]["n_pc_spline"] = n_pc

        prob.model.add_subsystem(
            "powercurve", rp.RegulatedPowerCurve(modeling_options=modeling_options), promotes=["*"]
        )
        prob.setup()
        for k in debug_npz.files:
            prob[k] = debug_npz[k]

        prob.run_model()
        grid0 = np.cumsum(np.abs(np.diff(np.cos(np.linspace(-np.pi / 4.0, np.pi / 2.0, n_pc)))))
        grid1 = (grid0 - grid0[0]) / (grid0[-1] - grid0[0])
        V_expect0 = grid1 * (prob["v_max"] - prob["v_min"]) + prob["v_min"]
        V_spline = np.linspace(prob["v_min"], prob["v_max"], n_pc)

        V_expect1 = np.sort(np.r_[V_expect0, prob["rated_V"]])
        npt.assert_equal(prob["V"], V_expect1)
        npt.assert_equal(prob["V_spline"], V_spline.flatten())


def suite():
    suite = [
        unittest.TestLoader().loadTestsFromTestCase(TestServo),
    ]
    return unittest.TestSuite(suite)


if __name__ == "__main__":
    result = unittest.TextTestRunner().run(suite())

    if result.wasSuccessful():
        exit(0)
    else:
        exit(1)
