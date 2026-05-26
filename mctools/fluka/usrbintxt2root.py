#!/usr/bin/env python3

import sys
import re
import argparse
from os import path
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True


def read_values(lines, start, count):
    values = []
    i = start
    while len(values) < count:
        tokens = lines[i].split()
        try:
            values.extend(float(v) for v in tokens)
        except ValueError:
            pass  # skip non-numeric lines (e.g. commentary)
        i += 1
    return values[:count]


def parse_axis(line):
    m = re.search(r'from\s+([-+\d.E]+)\s+to\s+([-+\d.E]+).*?(\d+)\s+bins', line)
    if not m:
        raise ValueError(f"Cannot parse axis line: {line.strip()}")
    return float(m.group(1)), float(m.group(2)), int(m.group(3))


def convert(infile, outfile, verbose):
    with open(infile) as f:
        lines = f.readlines()

    m = re.search(r'"([^"]+)"', lines[1])
    name = m.group(1).strip() if m else "h"

    xmin, xmax, nx = parse_axis(lines[2])
    ymin, ymax, ny = parse_axis(lines[3])
    zmin, zmax, nz = parse_axis(lines[4])
    n = nx * ny * nz

    data_start = err_start = None
    for i, line in enumerate(lines):
        if re.search(r'data follow', line, re.IGNORECASE):
            data_start = i + 2
        elif re.search(r'percentage errors follow', line, re.IGNORECASE):
            err_start = i + 2

    if data_start is None or err_start is None:
        print(f"usrbintxt2root: could not locate data sections in {infile}", file=sys.stderr)
        return 1

    values = read_values(lines, data_start, n)
    errors = read_values(lines, err_start, n)

    if verbose:
        print(f"Detector: {name}")
        print(f"  X: [{xmin}, {xmax}] cm, {nx} bins")
        print(f"  Y: [{ymin}, {ymax}] cm, {ny} bins")
        print(f"  Z: [{zmin}, {zmax}] cm, {nz} bins")

    h = ROOT.TH3F(name, name + ";x [cm];y [cm];z [cm]",
                  nx, xmin, xmax, ny, ymin, ymax, nz, zmin, zmax)

    # Data is stored as A(ix,iy,iz) in Fortran column-major order: ix varies fastest
    for iz in range(nz):
        for iy in range(ny):
            for ix in range(nx):
                gbin = ix + iy * nx + iz * nx * ny
                val = values[gbin]
                abs_err = val * errors[gbin] / 100.0
                h.SetBinContent(ix + 1, iy + 1, iz + 1, val)
                h.SetBinError(ix + 1, iy + 1, iz + 1, abs_err)

    f = ROOT.TFile(outfile, "recreate")
    h.Write()
    f.Close()
    print(f"Written: {outfile}")
    return 0


def main():
    """Convert FLUKA USRBIN ASCII text output to a ROOT TH3F histogram."""

    parser = argparse.ArgumentParser(description=main.__doc__,
                                     epilog="Homepage: https://github.com/kbat/mc-tools")
    parser.add_argument('txt', type=str, help='USRBIN text output file')
    parser.add_argument('root', type=str, nargs='?', help='output ROOT file name', default="")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, dest='verbose',
                        help='print detector info')

    args = parser.parse_args()

    if not path.isfile(args.txt):
        print(f"usrbintxt2root: File {args.txt} does not exist.", file=sys.stderr)
        return 1

    outfile = args.root if args.root else args.txt.replace('.txt', '.root')
    if outfile == args.txt:
        outfile = args.txt + '.root'

    return convert(args.txt, outfile, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
