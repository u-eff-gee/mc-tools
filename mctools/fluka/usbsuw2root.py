#!/usr/bin/env python3

import sys, argparse
from os import path
from mctools import fluka
from mctools.fluka.io.readers import UsrbinFile, unpack_floats
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

def main():
    """Convert USRBIN binary output into a ROOT TH3F histogram.

    """

    parser = argparse.ArgumentParser(description=main.__doc__,
                                     epilog="Homepage: https://github.com/kbat/mc-tools")
    parser.add_argument('usrbin', type=str, help='USRBIN binary output produced by usbsuw')
    parser.add_argument('root', type=str, nargs='?', help='output ROOT file name', default="")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, dest='verbose', help='Print some output')

    args = parser.parse_args()

    if not path.isfile(args.usrbin):
        print("usrbin2root: File %s does not exist." % args.usrbin, file=sys.stderr)
        return 1

    if args.root == "":
        rootFileName = "%s%s" % (args.usrbin,".root")
    else:
        rootFileName = args.root

    reader = UsrbinFile()
    reader.read_header(args.usrbin)

    num_detectors = len(reader.detectors)

    if args.verbose:
        reader.describe_header()
        print("\n%d tallies found:" % num_detectors)
        for i in range(num_detectors):
            reader.describe_detector(i)
            print("")

    root_file = ROOT.TFile(rootFileName, "recreate")
    for i in range(num_detectors):
        values = unpack_floats(reader.read_detector_data(i))
        errors = unpack_floats(reader.read_statistics(i))
        det = reader.detectors[i]

        title = fluka.particle.get(det.score, "unknown")
        dt = det.type % 10
        if   dt == 0:
            title += ";x [cm];y [cm];z [cm]"
        elif dt == 1:
            title += ";R [cm];#Phi [rad];z [cm]"
        elif dt == 2:
            title += ";Region"
        elif dt == 3:
            title += ";|x| [cm];y [cm];z [cm]"
        elif dt == 4:
            title += ";x [cm];|y| [cm];z [cm]"
        elif dt == 5:
            title += ";x [cm];y [cm];|z| [cm]"
        elif dt == 6:
            title += ";|x| [cm];|y| [cm];|z| [cm]"
        elif dt == 7:
            title += ";R [cm];#Phi [rad];|z| [cm]"
        elif dt == 8:
            title += ";MUSRBR;LUSRBL;FUSRBV"

        h = ROOT.TH3F(det.name, title, det.nx, det.xlow, det.xhigh, det.ny, det.ylow, det.yhigh, det.nz, det.zlow, det.zhigh)

        for i in range(det.nx):
            for j in range(det.ny):
                for k in range(det.nz):
                    gbin = i + j * det.nx + k * det.nx * det.ny
                    h.SetBinContent(i+1, j+1, k+1, values[gbin])
                    h.SetBinError(  i+1, j+1, k+1, errors[gbin]*values[gbin])
        h.SetEntries(reader.weight)
        h.Write()

    root_file.Close()

if __name__=="__main__":
    sys.exit(main())
