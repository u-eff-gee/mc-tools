"""BaseLevel associated with a ROOT TH3 histogram"""

import ROOT

from mctools.common.risk.level import BaseLevel
from mctools.common.risk.value import Value


class Limits:
    """Limits for a 1D variable"""

    def __init__(self, lower: float = float("-inf"), upper: float = float("inf")):
        self.lower = lower
        self.upper = upper


class Limits3D:
    """Box limits for a 3D variable"""

    def __init__(
        self, xlim: Limits = Limits(), ylim: Limits = Limits(), zlim: Limits = Limits()
    ):
        self.xlim = xlim
        self.ylim = ylim
        self.zlim = zlim


class Zone(BaseLevel):
    """BaseLevel associated with a ROOT TH3 histogram

    It is possible to use box constraints to limit the range of bins that are searched
    for the maximum value. The constraints are applied to the bin centers.
    """

    def __init__(
        self,
        hist: ROOT.TH3F | ROOT.TH3D,
        lim: Limits3D = Limits3D(),
        name: str = "",
        title: str = "",
    ):
        super().__init__(name=name, title=title)
        self.hist = hist
        self.lim = lim

    def evaluate(self):
        """Find the maximum value in the (constrained) TH3"""
        max_val = float("-inf")
        max_err = max_x = max_y = max_z = 0.0
        for n_x in range(self.hist.GetNbinsX()):
            x = self.hist.GetXaxis().GetBinCenter(n_x)
            if self.lim.xlim.lower <= x < self.lim.xlim.upper:
                for n_y in range(self.hist.GetNbinsY()):
                    y = self.hist.GetYaxis().GetBinCenter(n_y)
                    if self.lim.ylim.lower <= y < self.lim.ylim.upper:
                        for n_z in range(self.hist.GetNbinsZ()):
                            z = self.hist.GetYaxis().GetBinCenter(n_z)
                            if z >= self.lim.zlim.lower <= z < self.lim.zlim.upper:
                                if self.hist.GetBinContent(n_x, n_y, n_z) > max_val:
                                    max_val = self.hist.GetBinContent(n_x, n_y, n_z)
                                    max_err = self.hist.GetBinError(n_x, n_y, n_z)
                                    max_x = x
                                    max_y = y
                                    max_z = z
        self.value = Value(
            val=max_val,
            err=max_err,
            x=max_x,
            y=max_y,
            z=max_z,
        )
