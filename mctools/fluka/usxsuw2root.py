#!/usr/bin/env python3

import sys, argparse
from os import path
import numpy as np
from mctools import fluka, getLogBins, getLinBins
from mctools.fluka.io.readers import UsrbdxFile, unpack_floats
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

def decode_what1(n):
    """Decode WHAT(1) of a USRBDX card."""
    for i1 in (-2,-1,1,2):
        for i2 in (0,1):
            for i3 in (0,1):
                for i4 in (-1,0,1):
                    if (i1+10*i2+100*i3+10000*i4 == n):
                        return (i1,i2,i3,i4) # i3 is irrelevant - use bin.fluence instead
    print("usxsuw2root: what(1) == %d undefined" % n, file=sys.stderr)
    sys.exit(1)

def is_log_energy_axis(x):
    if x in (-2,-1):
        return True
    return False

def is_log_angle_axis(x):
    if x in (-2,2):
        return True
    return False

def get_axes_title(det):
    ztitle = "1/cm^{2}/GeV/sr"
    if int(det.dist) in (208,211): # differential energy fluence/current
        ztitle = "GeV/cm^{2}/GeV/sr"   # FLUKA manual page 247
    return ";Energy [GeV];#Omega [sr];" + ztitle
    # return {
    #     -2 : ";log10(Energy/GeV);log10(#Omega/sr);" + ztitle,
    #     -1 : ";log10(Energy/GeV);#Omega [sr];" + ztitle,
    #      1 : ";Energy [GeV];#Omega [sr];" + ztitle,
    #      2 : ";Energy [GeV];log10(#Omega/sr);" + ztitle,
    #     }[x]

def num_energy_bins(det):
    """Return the number of energy bins."""
    nebins = det.ne
    if det.lowneu and det.dist==8:
        nebins += det.ngroup
    return nebins

def energy_bins(det, axis_kind):
    """Return linear or logarithmic energy bins."""

    if is_log_energy_axis(axis_kind):
        return getLogBins(det.ne, det.elow, det.ehigh)
    else:
        return getLinBins(det.ne, det.elow, det.ehigh)

def angle_bins(det, axis_kind):
    """Return linear or logarithmic angular bins."""

    if is_log_angle_axis(axis_kind):
        return getLogBins(det.na, det.alow, det.ahigh)
    else:
        return getLinBins(det.na, det.alow, det.ahigh)

def histogram_title(det, what1):
    """Return the histogram title."""
    title = "%s %s #diamond reg %d %s %d #diamond %g cm^{2}" % (fluka.particle.get(det.dist, "undefined"), "fluence" if det.fluence else "current", det.reg1, "#leftrightarrow" if det.twoway else "#rightarrow", det.reg2, det.area)
    title += get_axes_title(det)
    return title

def make_histogram(det):
    """Create the main detector histogram."""

    what1 = decode_what1(det.type)[0]  # decoded WHAT(1)
    title = histogram_title(det, what1)

    nebins = num_energy_bins(det)
    ebins = energy_bins(det, what1)
    if det.lowneu and det.dist==8:
        ebins = np.concatenate((np.array(det.egroup[::-1]), energy_bins(det, what1)[1:]))

    return ROOT.TH2F(det.name, title, nebins, ebins, det.na, angle_bins(det, what1))

def make_low_energy_neutron_histogram(det):
    """Create a separate histogram for the low-energy neutron contribution."""
    what1 = decode_what1(det.type)[0]

    name = det.name + "_lowneu"
    title = "Contribution from low energy neutrons to " + histogram_title(det, what1)
    # print(det.ngroup, det.egroup[::-1])
    return ROOT.TH2F(name, title, det.ngroup, np.array(det.egroup[::-1]), det.na, angle_bins(det, what1))


def main():
    """Convert USRBDX binary output into ROOT histograms."""

    parser = argparse.ArgumentParser(description=main.__doc__,
                                     epilog="Homepage: https://github.com/kbat/mc-tools")
    parser.add_argument('usrbdx', type=str, help='USRBDX binary output')
    parser.add_argument('root', type=str, nargs='?', help='output ROOT file name', default="")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, dest='verbose', help='print what is being done')

    args = parser.parse_args()

    if not path.isfile(args.usrbdx):
        print("usxsuw2root: File %s does not exist." % args.usrbdx, file=sys.stderr)
        return 1

    if args.root == "":
        rootFileName = "%s%s" % (args.usrbdx,".root")
    else:
        rootFileName = args.root

    reader = UsrbdxFile()
    reader.read_header(args.usrbdx) # data file closed here

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
        errors = unpack_floats(reader.read_statistics(i))
        det = reader.detectors[i]
        lenval = len(values)

        assert lenval == len(errors)

        h = make_histogram(det)
        if det.lowneu and det.dist!=8:
            hn = make_low_energy_neutron_histogram(det)

#        print(det.name,det.lowneu,det.dist,"val:",len(val), det.ngroup, det.ne)
        if det.lowneu and det.dist==8: # 8 is NEUTRON
            lnval = values[-det.ngroup*det.na:][::-1]
            lnerr = errors[-det.ngroup*det.na:][::-1]
            v = ()
            e = ()
            for a in range(det.na,0,-1):
                i = det.ngroup*(a-1)
                j = det.ngroup*(a)
                v += lnval[i:j]
                e += lnerr[i:j]

                i=(det.na-a)*det.ne
                j=(det.na-a+1)*det.ne
                v += values[i:j]
                e += errors[i:j]

            values = v
            errors = e


        assert lenval == len(values), "%d != %d" % (lenval, len(values))
        assert lenval == len(errors), "%d != %d" % (lenval, len(errors))

        nebins = num_energy_bins(det)
        for i in range(nebins):
            for j in range(det.na):
                gbin = i + j * nebins
                h.SetBinContent(i+1, j+1, values[gbin])
                # why had to multiply by 15.91549 before?
                h.SetBinError(i+1, j+1, values[gbin]*errors[gbin])

        h.SetEntries(reader.weight)
        h.Write()

        # todo: use index [-gbin] instead of adding these two tuples
        nval = values[::-1] # double diff distribution - checked
        nerr = errors[::-1] # checked
        if det.lowneu and det.dist!=8:
            nebins = hn.GetNbinsX()
            assert nebins == det.ngroup, "n != det.ngroup"
            nabins = hn.GetNbinsY()
            assert nabins == det.na, "n != det.na"
            for i in range(nebins):
                for j in range(nabins):
                    gbin = i + j * nebins
                    hn.SetBinContent(i+1, j+1, nval[gbin])
                    hn.SetBinError(i+1, j+1, nerr[gbin]*nval[gbin])

            hn.Write()

    root_file.Close()

if __name__=="__main__":
    sys.exit(main())
