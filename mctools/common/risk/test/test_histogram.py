import unittest

from mctools.common.risk.test.input_histogram import create_test_histogram


class TestHistogram(unittest.TestCase):
    def test_histogram(self):
        hist = create_test_histogram()

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

        self.assertEqual(hist.GetYaxis().GetBinLowEdge(0), -1.0)
        self.assertEqual(hist.GetYaxis().GetBinCenter(0), -0.5)
        self.assertEqual(hist.GetYaxis().GetBinUpEdge(0), 0.0)
        self.assertEqual(hist.GetYaxis().GetBinLowEdge(1), 0.0)
        self.assertEqual(hist.GetYaxis().GetBinCenter(1), 0.5)
        self.assertEqual(hist.GetYaxis().GetBinUpEdge(1), 1.0)

        self.assertEqual(hist.GetZaxis().GetBinLowEdge(0), -1.0)
        self.assertEqual(hist.GetZaxis().GetBinCenter(0), -0.5)
        self.assertEqual(hist.GetZaxis().GetBinUpEdge(0), 0.0)
        self.assertEqual(hist.GetZaxis().GetBinLowEdge(1), 0.0)
        self.assertEqual(hist.GetZaxis().GetBinCenter(1), 0.5)
        self.assertEqual(hist.GetZaxis().GetBinUpEdge(1), 1.0)
