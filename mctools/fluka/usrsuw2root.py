#!/usr/bin/env python3

import sys, argparse, struct
from os import path
import numpy as np
from mctools import fluka
from mctools.fluka.io.readers import ResidualNucleiFile, unpack_floats
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

def describe_detector_type(det):
    """Return a printable RESNUCLEi product category.

    """
    if int(det.type) == 1:
        return "Spallation products"
    elif int(det.type) == 2:
        return "Low-energy neutron products"
    elif int(det.type) == 3:
        return "All residual nuclei"
    else:
        return "unknown RESNUCLEI detector type"

def make_graph(name, title, values, errors):
    n = len(values)
    assert n == len(errors), "graph: length of values and errors differ"

    num_points = np.count_nonzero(values)  # number of points in the graph

    ge = ROOT.TGraphErrors(num_points)
    j = 0 # ge point index
    for i in range(n):
        x = i+1
        y = values[i]
        ey = errors[i]*values[i]
        if y>0.0:
            ge.SetPoint(j, x, y)
            ge.SetPointError(j, 0.0, ey)
            j = j+1

    ge.SetNameTitle(name, title)

    return ge

def make_mass_graph(det, A, errA):
    return make_graph(det.name+"A", describe_detector_type(det)+": Isotope yield as a function of mass number;A;Isotope yield [nuclei/cm^{3}/primary]", A, errA)

def make_atomic_graph(det, Z, errZ):
    return make_graph(det.name+"Z", describe_detector_type(det)+": Isotope yield as a function of atomic number;Z;Isotope yield [nuclei/cm^{3}/primary]", Z, errZ)

def describe_scoring_region(det):
    """Return the scoring region label."""
    if det.region == -1:
        return "all regions"
    else:
        return "region = %d" % det.region

def make_histogram(det):
    """Create the histogram for a RESNUCLEi detector.

    """

    title = "%s (excluding isomers): %s, volume = %g cm^{3};Z;A;Isotope yield [nuclei/cm^{3}/primary]" % (describe_detector_type(det), describe_scoring_region(det), det.volume)

    nz = det.zhigh-1
    na = det.mhigh+det.nmzmin+det.zhigh

    return ROOT.TH2F(det.name, title, nz, 1, nz+1, na, 1, na+1)

def make_isomer_histogram(det, values, errors):
    """Create the histogram for isomer yields."""
    n = len(values)
    assert n == len(errors), "make_isomer_histogram: different lengths of values and errors"

    title = "Isomers of %s: %s, volume = %g cm^{3};bin number;Isomer yield [nuclei/cm^{3}/primary]" % (describe_detector_type(det), describe_scoring_region(det), det.volume)

    return ROOT.TH1F(det.name+"iso", title, n, 1, n+1)


def main():
    """Convert RESNUCLEi binary output into ROOT histograms.

    """

    parser = argparse.ArgumentParser(description=main.__doc__,
                                     epilog="Homepage: https://github.com/kbat/mc-tools")
    parser.add_argument('usrsuw', type=str, help='RESNUCLEi binary output')
    parser.add_argument('root', type=str, nargs='?', help='output ROOT file name', default="")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, dest='verbose', help='print what is being done')

    args = parser.parse_args()

    if not path.isfile(args.usrsuw):
        print("usrsuw2root: File %s does not exist." % args.usrsuw, file=sys.stderr)
        return 1

    if args.root == "":
        rootFileName = "%s%s" % (args.usrsuw,".root")
    else:
        rootFileName = args.root

    reader = ResidualNucleiFile()
    reader.read_header(args.usrsuw) # data file is closed here

    num_detectors = len(reader.detectors)

    if args.verbose:
        reader.describe_header()
        print("\n%s %d %s found:" % ('*'*20, num_detectors, "estimator" if num_detectors==1 else "estimators"))
        for i in range(num_detectors):
            reader.describe_detector(i)
            print("")

    root_file = ROOT.TFile(rootFileName, "recreate")
    for i in range(num_detectors):
        values = unpack_floats(reader.read_detector_data(i))
        stat = reader.read_statistics(i)
        total, A, errA, Z, errZ, errors, isoErr = map(unpack_floats, stat)
        # isoErr = errors for the isomer data

#        print("isomers: ", reader.isomer_count, i)

        det = reader.detectors[i]
#        print(det.nb, det.name, det.type, det.region, det.mhigh, det.zhigh, det.nmzmin)

        if reader.isomer_count:
            iso = reader.read_isomers(i)
            isoHead = iso[0]
            L = struct.unpack("=10xi", isoHead)
            assert L[0] == len(isoErr), "Isomers: different size of Data and Error arrays"
            iso_data = struct.unpack("=%df" % L[0], iso[1])

            hIso = make_isomer_histogram(det, iso_data, isoErr)
            for j in range(1,L[0]):
                hIso.SetBinContent(j, iso_data[j])
                hIso.SetBinError(j, isoErr[j]*iso_data[j])

            # if det.name == "res126":
            #     print("L",L)
            #     print(len(isoData))
            #     print(i, len(isoErr))

        h = make_histogram(det)

        grA = make_mass_graph(det, A, errA)
        grZ = make_atomic_graph(det, Z, errZ)

        for z in range(1,det.zhigh+1):
            for j in range(1,det.mhigh+1):
                gbin = z-1+(j-1)*(det.zhigh)
                if values[gbin]>0.0:
                    # See the RDRESN program from the RESNUCLEi section of the Manual
                    a = j+det.nmzmin+2*z
                    h.SetBinContent(z,a,values[gbin])
                    h.SetBinError(z,a,errors[gbin]*values[gbin])

        h.Write()
        if reader.isomer_count:
            hIso.Write()
        grA.Write()
        grZ.Write()

    root_file.Close()

if __name__=="__main__":
    sys.exit(main())
