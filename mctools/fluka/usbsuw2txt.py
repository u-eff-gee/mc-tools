#!/usr/bin/env python3

import sys, argparse
from os import path
import numpy as np
from mctools import fluka
from mctools.fluka.io.readers import UsrbinFile, unpack_floats

def getEdges(xmin, xmax, nbins):
    """Return bin edges for an equidistant axis.

    """

    dx = (xmax - xmin)/nbins
    x = np.arange(xmin, xmax, dx).tolist()
    x.append(xmax)
    return x

def main():
    """Convert USRBIN binary output into plain text.

       Format: min and max edges of the bin along each axis followed by the value and its relative error.
    """

    parser = argparse.ArgumentParser(description=main.__doc__,
                                     epilog="Homepage: https://github.com/kbat/mc-tools")
    parser.add_argument('usbsuw', type=str, help='USRBIN binary output')
    parser.add_argument('out', type=str, nargs='?', help='output ASCII file name', default="")
    parser.add_argument('-f', action='store_true', default=False, dest='force', help='overwrite output file')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, dest='verbose', help='explain what is being done')

    args = parser.parse_args()

    if not path.isfile(args.usbsuw):
        print("usbsuw2txt: File %s does not exist." % args.usbsuw, file=sys.stderr)
        return 1

    if args.out == "":
        outFileName = "%s%s" % (args.usbsuw,".txt")
    else:
        outFileName = args.out

    if not args.force and path.isfile(outFileName):
        print("usbsuw2txt: File %s already exists. Use '-f' to overwrite." % outFileName, file=sys.stderr)
        return 1

    reader = UsrbinFile()
    reader.read_header(args.usbsuw)

    num_detectors = len(reader.detectors)

    if args.verbose:
        reader.describe_header()
        print("\n%d tallies found:" % num_detectors)
        for i in range(num_detectors):
            reader.describe_detector(i)
            print("")

    with open(outFileName, "w") as fout:
        for i in range(num_detectors):
            values = unpack_floats(reader.read_detector_data(i))
            errors = unpack_floats(reader.read_statistics(i))
            det = reader.detectors[i]

            title = fluka.particle.get(det.score, "unknown")
            axes = ""
            if det.type % 10 in (0, 3, 4, 5, 6):  # cartesian
                axes = "xmin xmax ymin ymax zmin zmax value relerr"
            elif det.type % 10 in (1, 7):
                axes = "rmin        rmax         phimin       phimax       zmin         zmax         value       relerr"

            x = getEdges(det.xlow, det.xhigh, det.nx)
            y = getEdges(det.ylow, det.yhigh, det.ny)
            z = getEdges(det.zlow, det.zhigh, det.nz)

            print(f"# {title}", file=fout)
            print(f"# {axes}", file=fout)

            for ix in range(det.nx):
                for iy in range(det.ny):
                    for iz in range(det.nz):
                        gbin = ix + iy * det.nx + iz * det.nx * det.ny
                        print(
                            f"{x[ix]:>12.5e} {x[ix+1]:>12.5e} {y[iy]:>12.5e} {y[iy+1]:>12.5e} "
                            f"{z[iz]:>12.5e} {z[iz+1]:>12.5e} {values[gbin]:>12.5e} {errors[gbin]:>.4f}",
                            file=fout,
                        )

if __name__=="__main__":
    sys.exit(main())
