import unittest

from mctools.common.risk.zone import Limits, Limits3D, Zone
from mctools.common.risk.test.input_histogram import create_test_histogram


class TestZone(unittest.TestCase):
    def test_zone(self):
        # Create test histogram
        hist = create_test_histogram()

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
