#!/usr/bin/env python3

import sys, argparse, struct
from os import path
import numpy as np
from math import isclose
from mctools import fluka, getLogBins, getLinBins
from mctools.fluka.io.readers import FlukaBinaryFile, DetectorRecord, unpack_floats
from mctools.fluka.io.recordio import read_record, skip_record
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

def get_axes_title(det):
    # differential energy fluence/current
    # FLUKA manual: USRTRACK section
    energy = (208, 211) # ENERGY or EM-ENERGY
    ytitle = fluka.particle.get(det.dist, "undefined")
    if int(det.dist) in energy:
        ytitle += " tracklength [cm]" if isclose(det.volume, 1.0) else " energy fluence [cm^{-2}]"
    else:
        ytitle += " tracklength [cm/GeV]" if isclose(det.volume, 1.0) else " fluence [1/GeV/cm^{2}]"

    return ";Energy [GeV];" + ytitle

def energy_bins(det):
    """Return linear or logarithmic energy bins."""

    if det.type == -1:
        return getLogBins(det.ne, det.elow, det.ehigh)
    else:
        return getLinBins(det.ne, det.elow, det.ehigh)

def make_histogram(det):
    """Create the main detector histogram."""

    if det.ne == 0:
        print(f"WARNING: Not saving detector {det.name} into ROOT file since it has 0 energy bins: {det.elow} < E < {det.ehigh}")
        print("         This happens for neutron-contributing estimators if max scoring energy is below groupwise max energy, 20 MeV.")
        return None

    title = fluka.particle.get(det.dist, "undefined")
    title += " #diamond "
    title += "all regions" if int(det.reg) == -1 else "reg %d" % det.reg
    title += " #diamond "
    title += "%g cm^{3}" % det.volume
    title += " #diamond "
    title += "%g < E < %g GeV" % (det.elow, det.ehigh)
    title += get_axes_title(det)

    return ROOT.TH1F(det.name, title, det.ne, energy_bins(det))

def make_low_energy_neutron_histogram(det):
    """Create a histogram for the low-energy neutron contribution.

    """
    if det.lowneu:
        name = det.name + "_lowneu"
        title = name + get_axes_title(det)
        return ROOT.TH1F(name, title, det.ngroup, np.array(det.egroup[::-1]))
    else:
        return 0

class Usrtrack(FlukaBinaryFile):
    """ Reads the ustsuw binary output
        (USRTRACK / USRCOLL estimators)
    """
    def read_header(self, filename):
        """Read the file header info."""
        f = super().read_header(filename)
        # self.describe_header()

        while True:
            data = read_record(f)
            if data is None: break
            size = len(data)
#            print("size: ", size)

            if size == 14 and data.decode('utf8')[:10] == "STATISTICS":
                self.stats_offset = f.tell()
                for det in self.detectors:
                    data = unpack_floats(read_record(f))
                    det.total = data[0]
                    det.total_error = data[1]
                # for j in range(6):
                #     skip_record(f)
                break

            if size != 50: raise IOError("Invalid USRTRACK/USRCOLL file %d " % size)

            header = struct.unpack("=i10siiififfif", data)

            det = DetectorRecord()
            det.nb = header[0]
            det.name = header[1].decode('utf8').strip()  # track/coll name
            det.type = header[2]  # binning type: 1 - linear energy etc
            det.dist = header[3]  # distribution to be scored
            det.reg = header[4]  # region
            det.volume = header[5]  # volume (cm**3) of the detector
            det.lowneu = header[6]  # low-energy neutron flag
            det.elow = header[7]  # minimum energy [GeV]
            det.ehigh = header[8]  # maximum energy [GeV]
            det.ne = header[9]  # number of energy intervals
            det.de = header[10]  # energy bin width

            self.detectors.append(det)

            if det.lowneu:
                data = read_record(f)
                det.ngroup = struct.unpack("=i",data[:4])[0]
                det.egroup = struct.unpack("=%df"%(det.ngroup+1), data[4:])
                print(f"{det.name}: Low energy neutrons scored with {det.ngroup} groups")
            else:
                det.ngroup = 0
                det.egroup = ()

            size  = (det.ngroup+det.ne) * 4
            if size != skip_record(f):
                raise IOError("Invalid USRTRACK file")
        f.close()

    def describe_detector(self, i):
        """Describe one detector block."""
        det = self.detectors[i]
        print("Detector:", det.name)
        print(" binning type: ", det.type)
        print(" distribution to be scored:", det.dist)
        print(" region:", det.reg)
        print(" volume:", det.volume)
        print(" low energy neutrons:", det.lowneu)
        print(" %g < E < %g GeV / %d bins; bin width: %g" % (det.elow, det.ehigh, det.ne, det.de))

    def read_statistics(self, det, lowneu):
        """Read detector statistical data."""
        if self.stats_offset < 0: return None
        with open(self.filename,"rb") as f:
            f.seek(self.stats_offset)
            for i in range(det+3):  # check that 3 gives correct errors with 1 USRTRACK detector
                skip_record(f)  # skip previous detectors
            data = read_record(f)
        return data

    def read_detector_data(self, det, lowneu):
        """Read detector data."""
        f = open(self.filename, "rb")
        skip_record(f)  # Skip header
        for i in range(2*det):
            skip_record(f)  # Detector Header & Data
        skip_record(f)  # Detector Header
        if lowneu:
            skip_record(f)  # skip low-energy neutron data
        data = read_record(f)
        f.close()
        return data

def main():
    """Convert USRTRACK / USRCOLL binary output into ROOT histograms."""

    parser = argparse.ArgumentParser(description=main.__doc__,
                                     epilog="Homepage: https://github.com/kbat/mc-tools")
    parser.add_argument('usrtrack', type=str, help='USRTRACK / USRCOLL binary output')
    parser.add_argument('root', type=str, nargs='?', help='output ROOT file name', default="")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, dest='verbose', help='print what is being done')

    args = parser.parse_args()

    if not path.isfile(args.usrtrack):
        print("ustsuw2root: File %s does not exist." % args.usrtrack, file=sys.stderr)
        return 1

    if args.root == "":
        rootFileName = "%s%s" % (args.usrtrack,".root")
    else:
        rootFileName = args.root

    reader = Usrtrack()
    reader.read_header(args.usrtrack)

    num_detectors = len(reader.detectors)
    # print("ND:",ND)

    if args.verbose:
        #reader.describe_header()
        for i in range(num_detectors):
            reader.describe_detector(i)
            print("")

    root_file = ROOT.TFile(rootFileName, "recreate")
    for i in range(num_detectors):
        det = reader.detectors[i]
        values = unpack_floats(reader.read_detector_data(i, det.lowneu))
        errors = unpack_floats(reader.read_statistics(i, det.lowneu))

        # print("val",val, len(err))
        # print("err",err, len(err))
        assert len(values) == len(errors), "val and err length are different: %d %d" % (len(values), len(errors))

        h = make_histogram(det)
        hn = make_low_energy_neutron_histogram(det) # filled only if det.lowneu

        if h:
            n = h.GetNbinsX()
            assert n == det.ne, "n != det.ne"

            # print(i,n, len(values))
            for i in range(n):
                h.SetBinContent(i+1, values[i])
                h.SetBinError(i+1,   errors[n-i-1]*values[i])

            h.SetEntries(reader.weight)
            h.Write()

# not implemented - bugs with theINFN FLUKA, but it seems works with the CERN FLUKA
        if det.lowneu:
            # values_lowneu = values[det.ne::][::-1]
            # errors_lowneu = errors[det.ne::][::-1]
            n = hn.GetNbinsX()
            assert n == det.ngroup, "n != det.ngroup"
            # print(n, len(val_lowneu), len(err_lowneu))
            for i in range(n):
                hn.SetBinContent(i+1, values[-i-1])
                hn.SetBinError(i+1,   errors[-i-1]*values[-i-1])

            hn.SetEntries(reader.weight)
            hn.Write()

    root_file.Close()

if __name__=="__main__":
    sys.exit(main())
