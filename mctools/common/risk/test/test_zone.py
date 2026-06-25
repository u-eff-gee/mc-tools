import unittest

import ROOT

from mctools.common.risk.zone import Limits, Limits3D, Zone


class TestZone(unittest.TestCase):
    def test_zone(self):
        # Create test histogram
        hist = ROOT.TH3F("th3", "th3", 2, 0.0, 2.0, 2, 0.0, 2.0, 2, 0.0, 2.0)
        value = 0.0
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    hist.SetBinContent(i, j, k, value)
                    hist.SetBinError(i, j, k, value * 0.1)
                    value += 1.0

        # Check content of test histogram
        self.assertEqual(hist.GetBinContent(0, 0, 0), 0.0)
        self.assertEqual(hist.GetBinContent(0, 0, 1), 1.0)
        self.assertEqual(hist.GetBinContent(0, 1, 0), 2.0)
        self.assertEqual(hist.GetBinContent(0, 1, 1), 3.0)
        self.assertEqual(hist.GetBinContent(1, 0, 0), 4.0)
        self.assertEqual(hist.GetBinContent(1, 0, 1), 5.0)
        self.assertEqual(hist.GetBinContent(1, 1, 0), 6.0)
        self.assertEqual(hist.GetBinContent(1, 1, 1), 7.0)

        self.assertEqual(hist.GetXaxis().GetBinLowEdge(0), -1.0)
        self.assertEqual(hist.GetXaxis().GetBinCenter(0), -0.5)
        self.assertEqual(hist.GetXaxis().GetBinUpEdge(0), 0.0)
        self.assertEqual(hist.GetXaxis().GetBinLowEdge(1), 0.0)
        self.assertEqual(hist.GetXaxis().GetBinCenter(1), 0.5)
        self.assertEqual(hist.GetXaxis().GetBinUpEdge(1), 1.0)

        # 1) No Condition
        zone = Zone(hist=hist)
        zone.evaluate()
        self.assertEqual(zone.value.val, 7.0)
        self.assertAlmostEqual(zone.value.err, 0.7, places=15)
        self.assertEqual(zone.value.x, 0.5)
        self.assertEqual(zone.value.y, 0.5)
        self.assertEqual(zone.value.z, 0.5)

        # 2) Single Condition
        # Demonstrate that the bin center is compared to the given limits.
        # Upper limit exactly on bin edge
        zone = Zone(hist=hist, lim=Limits3D(zlim=Limits(upper=0.0)))
        zone.evaluate()
        self.assertEqual(zone.value.val, 6.0)
        self.assertAlmostEqual(zone.value.err, 0.6, places=15)
        self.assertEqual(zone.value.x, 0.5)
        self.assertEqual(zone.value.y, 0.5)
        self.assertEqual(zone.value.z, -0.5)
        # Upper limit below bin edge
        zone = Zone(hist=hist, lim=Limits3D(zlim=Limits(upper=-0.1)))
        zone.evaluate()
        self.assertEqual(zone.value.val, 6.0)
        self.assertAlmostEqual(zone.value.err, 0.6, places=15)
        self.assertEqual(zone.value.x, 0.5)
        self.assertEqual(zone.value.y, 0.5)
        self.assertEqual(zone.value.z, -0.5)
        # Upper limit above bin edge, but lower than center
        zone = Zone(hist=hist, lim=Limits3D(zlim=Limits(upper=0.1)))
        zone.evaluate()
        self.assertEqual(zone.value.val, 6.0)
        self.assertAlmostEqual(zone.value.err, 0.6, places=15)
        self.assertEqual(zone.value.x, 0.5)
        self.assertEqual(zone.value.y, 0.5)
        self.assertEqual(zone.value.z, -0.5)
        # Upper limit above bin center
        zone = Zone(hist=hist, lim=Limits3D(zlim=Limits(upper=0.6)))
        zone.evaluate()
        self.assertEqual(zone.value.val, 7.0)
        self.assertAlmostEqual(zone.value.err, 0.7, places=15)
        self.assertEqual(zone.value.x, 0.5)
        self.assertEqual(zone.value.y, 0.5)
        self.assertEqual(zone.value.z, 0.5)

        # 3) Multiple conditions
        zone = Zone(
            hist=hist, lim=Limits3D(xlim=Limits(upper=0.0), zlim=Limits(lower=0.0))
        )
        zone.evaluate()
        self.assertEqual(zone.value.val, 3.0)
        self.assertAlmostEqual(zone.value.err, 0.3, places=15)
        self.assertEqual(zone.value.x, -0.5)
        self.assertEqual(zone.value.y, 0.5)
        self.assertEqual(zone.value.z, 0.5)

        zone = Zone(
            hist=hist,
            lim=Limits3D(
                xlim=Limits(upper=0.0), ylim=Limits(upper=0.0), zlim=Limits(lower=0.0)
            ),
        )
        zone.evaluate()
        self.assertEqual(zone.value.val, 1.0)
        self.assertAlmostEqual(zone.value.err, 0.1, places=15)
        self.assertEqual(zone.value.x, -0.5)
        self.assertEqual(zone.value.y, -0.5)
        self.assertEqual(zone.value.z, 0.5)
