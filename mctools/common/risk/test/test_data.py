import unittest

from mctools.common.risk.data import Data, SourceCombination
from mctools.common.risk.level import Level
from mctools.common.risk.test.input_histogram import create_test_histogram
from mctools.common.risk.zone import Zone


class TestData(unittest.TestCase):
    def test_data(self):
        data = Data(
            sources={
                "L2_0": Level(
                    sub_levels={
                        "L1_0": Zone(hist=create_test_histogram("L1_0", 1.0)),
                        "L1_1": Zone(hist=create_test_histogram("L1_1", 2.0)),
                    }
                ),
                "L2_1": Level(
                    sub_levels={
                        "L1_0": Level(
                            sub_levels={
                                "L0_0": Zone(hist=create_test_histogram("L0_0", 3.0)),
                                "L0_1": Zone(hist=create_test_histogram("L0_1", 4.0)),
                            }
                        ),
                        "L1_1": Level(
                            sub_levels={
                                "L0_0": Zone(hist=create_test_histogram("L0_0p", 5.0)),
                                "L0_1": Zone(hist=create_test_histogram("L0_1p", 6.0)),
                            }
                        ),
                    }
                ),
            },
            cross_level_combinations={
                "c1": SourceCombination(
                    combination=[["L2_0"], ["L2_1", "L1_0", "L0_1"]]
                ),
                "c2": SourceCombination(
                    combination=[["L2_0"], ["L2_1", "L1_0", "L0_1"], ["L2_1", "L1_1"]]
                ),
            },
        )
        data.evaluate()
        # Level 2
        self.assertEqual(data.sources["L2_0"].value.val, 14.0)
        self.assertEqual(data.sources["L2_1"].value.val, 42.0)
        # Level 1
        self.assertEqual(data.sources["L2_0"]["L1_0"].value.val, 7.0)
        self.assertEqual(data.sources["L2_0"]["L1_1"].value.val, 14.0)
        self.assertEqual(data.sources["L2_1"]["L1_0"].value.val, 28.0)
        self.assertEqual(data.sources["L2_1"]["L1_1"].value.val, 42.0)
        # Level 0 (only for L2_1 branch)
        self.assertEqual(data.sources["L2_1"]["L1_0"]["L0_0"].value.val, 21.0)
        self.assertEqual(data.sources["L2_1"]["L1_0"]["L0_1"].value.val, 28.0)
        self.assertEqual(data.sources["L2_1"]["L1_1"]["L0_0"].value.val, 35.0)
        self.assertEqual(data.sources["L2_1"]["L1_1"]["L0_1"].value.val, 42.0)
        # Combinations
        self.assertEqual(data.cross_level_combinations["c1"].value.val, 28.0)
        self.assertEqual(data.cross_level_combinations["c2"].value.val, 42.0)
