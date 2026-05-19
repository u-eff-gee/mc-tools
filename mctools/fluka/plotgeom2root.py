#!/usr/bin/env python3

import sys, argparse, os, struct
from array import array
from mctools.fluka.flair import fortran
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)


def main():
    """Convert PLOTGEOM output into a ROOT TMultiGraph object

    """

    parser = argparse.ArgumentParser(description=main.__doc__,
                                     epilog="Homepage: https://github.com/kbat/mc-tools")
    parser.add_argument('plotgeom', type=str, nargs='*', help='list of plotgeom files')
    parser.add_argument('-o', dest='root', type=str, help='output ROOT file name', default="")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, dest='verbose', help='print what is being done')
    parser.add_argument('-f', '--force', action='store_true', default=False, dest='overwrite', help='overwrite the output ROOT file')

    args = parser.parse_args()

    for f in args.plotgeom:
        if not os.path.isfile(f):
            sys.exit("plotgeom2root: File %s does not exist." % f)

    wlength = 0
    title = ""
    for plotgeom in args.plotgeom:
        if args.root == "":
            rootFileName = "%s%s" % (plotgeom,".root")
        else:
            rootFileName = args.root

        if not args.overwrite and os.path.isfile(rootFileName):
            sys.exit("%s exists. Use '-f' to overwrite it." % rootFileName)

        with open(plotgeom, 'rb') as f:
            data = fortran.read(f)
            size = len(data)
            if size != 80:
                sys.exit("Format error [title]")
            decoded = struct.unpack("=80s", data)[0].decode('utf-8')
            if '***COMPRESSED***' in decoded:
                sys.exit(f"{plotgeom}: compressed PLOTGEOM files are not supported")
            title = decoded.strip()
            if args.verbose:
                print("Title:",title)

            data = fortran.read(f)
            size = len(data)
            if size != 14*4:
                print("Format error [basis]")
            # http://www.fluka.org/fluka.php?id=man_onl&sub=63
            X0,Y0,Z0,X1,Y1,Z1,TYX,TYY,TYZ,TXX,TXY,TXZ,XAXLEN,YAXLEN = struct.unpack("=14f", data)
            if args.verbose:
                print("Bottom left corner:",X0,Y0,Z0)
                print("Top right corner:",X1,Y1,Z1)
                print("Direction cosines of horizontal axis:",TXX,TXY,TXZ)
                print("Direction cosines of vertical axis:",TYX,TYY,TYZ)
                print("horizontal/vertical axes length:",XAXLEN,YAXLEN)
#                print(X0,Y0,Z0,X1,Y1,Z1,TYX,TYY,TYZ,TXX,TXY,TXZ,XAXLEN,YAXLEN)

            # Determine plane type from direction cosines of the picture axes.
            # The picture x-axis is (TXX,TXY,TXZ) and y-axis is (TYX,TYY,TYZ).
            # If both axes have no Z component the picture lies in the XY plane, etc.
            tol = 1e-3
            if abs(TXZ) < tol and abs(TYZ) < tol:
                plane = "xy"
            elif abs(TXY) < tol and abs(TYY) < tol:
                plane = "xz"
            elif abs(TXX) < tol and abs(TYX) < tol:
                plane = "yz"
            else:
                plane = "arbitrary"

            if args.verbose:
                print(f"Plane == {plane}")

            if plane == "xy":
                xtitle, ytitle = "x [cm]", "y [cm]"
            elif plane == "xz":
                xtitle, ytitle = "x [cm]", "z [cm]"
            elif plane == "yz":
                xtitle, ytitle = "y [cm]", "z [cm]"
            else:
                xtitle = f"({TXX:.3g}, {TXY:.3g}, {TXZ:.3g}) [cm]"
                ytitle = f"({TYX:.3g}, {TYY:.3g}, {TYZ:.3g}) [cm]"

            data = fortran.read(f)
            size = len(data)
            if size==8:
                NWORMS,dummy = struct.unpack("=2i", data)

            i = 0
            fout = ROOT.TFile(rootFileName, "recreate", plotgeom)
            mg = ROOT.TMultiGraph("mg", f"{title};{xtitle};{ytitle}")
            while True:
                i = i + 1
                data = fortran.read(f)
                if data is None:
                    break
                size = len(data)

                if size == 12:
                    windex,dummy,wlength = struct.unpack("=3i",data)
                elif size==8:
                    pass
#                    tmp = struct.unpack("=2i", data)
                elif size==24:
                    pass
#                    tmp = struct.unpack("=3i3f", data)
                else:
                    coord = struct.unpack("=%df" % (wlength*2),data) # pairs of x,y

                    # Worm coordinates are in the picture's local frame.
                    # Convert to real 3D coordinates using direction cosines:
                    #   real = origin + x_local*(TXX,TXY,TXZ) + y_local*(TYX,TYY,TYZ)
                    x_local = coord[::2]
                    y_local = coord[1::2]
                    x3d = [X0 + xi*TXX + yi*TYX for xi, yi in zip(x_local, y_local)]
                    y3d = [Y0 + xi*TXY + yi*TYY for xi, yi in zip(x_local, y_local)]
                    z3d = [Z0 + xi*TXZ + yi*TYZ for xi, yi in zip(x_local, y_local)]

                    if plane == "xy":
                        x, y = x3d, y3d
                    elif plane == "xz":
                        x, y = x3d, z3d
                    elif plane == "yz":
                        x, y = y3d, z3d
                    elif plane == "arbitrary":
                        x, y = list(x_local), list(y_local)
                    else:
                        print(f"ERROR: Plane is {plane} - not supported", file=sys.stderr)
                        return 1

                    g = ROOT.TGraph(len(x), array('f', x), array('f', y))
                    g.SetName("g%d" % i)
                    mg.Add(g)

        mg.Write()
        fout.Close()


if __name__=="__main__":
    sys.exit(main())
