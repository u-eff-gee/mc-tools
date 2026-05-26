#!/usr/bin/env python3

import sys, argparse, struct
import numpy as np
from os import path
from math import sqrt
from mctools.fluka.io.recordio import read_record
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

class DetsuwReader:
    def __init__(self, fname):
        self.handle = open(fname, 'rb')

        data = read_record(self.handle)
        self.runtit, self.runtim, self.wctot, self.nctot, self.mctot = struct.unpack("=80s32sf2i", data)
        self.runtit = self.runtit.decode('utf-8').strip()
        self.runtim = self.runtim.decode('utf-8').strip()
        assert self.runtim == "********    Sum file    ********"
        self.nps = self.nctot + 1.0e9*self.mctot

    def __del__(self):
        self.handle.close()

    def reset(self):
        self.chname = None
        self.nbin   = None

        self.ebins = []
        self.val   = []
        self.err   = []

    def read(self):
        self.reset()

        data = read_record(self.handle)
        if data is None:
            return False
        ndet,self.chname,self.nbin,emin,ebin,self.ecut = struct.unpack("=i10si3f", data)
        self.chname = self.chname.decode('utf-8').strip()

        data = read_record(self.handle)
        iv = struct.unpack("=%ii" % self.nbin, data)

        for i in range(self.nbin+1):
            self.ebins.append(emin + i * ebin)

        for i in range(self.nbin):
            weibin = iv[i] / self.nps
            weierr = 1.0/sqrt(max(iv[i],1))
            self.val.append(weibin)
            self.err.append(weierr*weibin)

        return True

def main():
    """Convert DETECT binary output into a ROOT TH1F histogram.

    """

    parser = argparse.ArgumentParser(description=main.__doc__,
                                     epilog="Homepage: https://github.com/kbat/mc-tools")
    parser.add_argument('detsuw', type=str, help='detsuw binary output')
    parser.add_argument('root', type=str, nargs='?', help='output ROOT file name', default="")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, dest='verbose', help='Explain what is being done')

    args = parser.parse_args()

    if not path.isfile(args.detsuw):
        print("detsuw2root: File %s does not exist." % args.detsuw, file=sys.stderr)
        return 1

    if args.root == "":
        rootFileName = "%s%s" % (args.detsuw,".root")
    else:
        rootFileName = args.root

    root_file = ROOT.TFile(rootFileName, "recreate")

    reader = DetsuwReader(args.detsuw)
    while reader.read():
        hist = ROOT.TH1F(reader.chname, "nps = %g #bullet E_{cut} = %g GeV;Energy deposition [GeV];Counts/primary" % (reader.nps, reader.ecut), reader.nbin, np.array(reader.ebins))
        for i in range(reader.nbin):
            hist.SetBinContent(i+1, reader.val[i])
            hist.SetBinError(i+1, reader.err[i])
        hist.Write()

    root_file.Close()


if __name__=="__main__":
    sys.exit(main())
