import unittest

from mctools.common.risk.level import Level


class TestGetMax(unittest.TestCase):
    def test_level(self):
        Level(
            name="L2",
            sub_levels={
                "L1_0": Level(sub_levels={"L0_0": Level(), "L0_1": Level()}),
                "L1-1": Level(sub_levels={"L0_0": Level(), "L0_1": Level()}),
            },
        )
