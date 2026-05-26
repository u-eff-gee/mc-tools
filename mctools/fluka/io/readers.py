"""Readers for FLUKA binary output files."""

from __future__ import annotations

import io
import math
import re
import struct
from dataclasses import dataclass

from . import bmath
from .recordio import read_record, skip_record

try:
    import numpy
except ImportError:  # pragma: no cover - optional dependency
    numpy = None

_DETECTOR_LINE = re.compile(r"^ ?# ?Detector ?n?:\s*\d*\s*(.*)\s*", re.MULTILINE)
_BLOCK_LINE = re.compile(r"^ ?# ?Block ?n?:\s*\d*\s*(.*)\s*", re.MULTILINE)


def unpack_floats(payload: bytes) -> tuple[float, ...]:
    """Unpack a raw byte payload into native floats."""

    return struct.unpack("=%df" % (len(payload) // 4), payload)


@dataclass
class DetectorRecord:
    """A mutable record object populated by the FLUKA readers."""

    index: int = 0
    name: str = ""


class FlukaBinaryFile:
    """Base class for FLUKA USRxxx-style binary files."""

    def __init__(self, filename: str | None = None):
        self.reset()
        if filename is not None:
            self.read_header(filename)

    def reset(self) -> None:
        self.filename = ""
        self.title = ""
        self.time = ""
        self.weight = 0.0
        self.n_cases = 0
        self.n_batches = 0
        self.detectors: list[DetectorRecord] = []
        self.data_offset = -1
        self.stats_offset = -1

    def read_header(self, filename: str):
        self.reset()
        self.filename = filename
        handle = open(self.filename, "rb")

        payload = read_record(handle)
        if payload is None:
            raise IOError("Invalid USRxxx file")

        size = len(payload)
        overflow = 0
        if size == 116:
            title, time, self.weight = struct.unpack("=80s32sf", payload)
            self.n_cases = 1
            self.n_batches = 1
        elif size == 120:
            title, time, self.weight, self.n_cases = struct.unpack("=80s32sfi", payload)
            self.n_batches = 1
        elif size == 124:
            title, time, self.weight, self.n_cases, self.n_batches = struct.unpack("=80s32sfii", payload)
        elif size == 128:
            title, time, self.weight, self.n_cases, overflow, self.n_batches = struct.unpack("=80s32sfiii", payload)
        elif size == 136:
            title, time, self.weight, self.n_cases, overflow, self.n_batches, _, _ = struct.unpack(
                "=80s32sfiiiii", payload
            )
        else:
            raise IOError("Invalid USRxxx file")

        if overflow > 0:
            self.n_cases = self.n_cases + overflow * 1000000000

        self.title = title.strip().decode()
        self.time = time.strip().decode()
        return handle

    def read_detector_data(self, index: int) -> bytes:
        handle = open(self.filename, "rb")
        skip_record(handle)
        for _ in range(2 * index):
            skip_record(handle)
        skip_record(handle)
        payload = read_record(handle)
        handle.close()
        return payload

    def read_statistics(self, index: int) -> bytes | None:
        if self.stats_offset < 0:
            return None
        handle = open(self.filename, "rb")
        handle.seek(self.stats_offset)
        for _ in range(index):
            skip_record(handle)
        payload = read_record(handle)
        handle.close()
        return payload

    def describe_header(self) -> None:
        print("File   : ", self.filename)
        print("Title  : ", self.title)
        print("Time   : ", self.time)
        print("Weight : ", self.weight)
        print("NCase  : ", self.n_cases)
        print("NBatch : ", self.n_batches)


class ResidualNucleiFile(FlukaBinaryFile):
    """Reader for RESNUCLEi output files."""

    def read_header(self, filename: str):
        handle = super().read_header(filename)
        self.isomer_count = 0

        if self.n_cases <= 0:
            self.has_evolution = True
            self.n_cases = -self.n_cases
            payload = read_record(handle)
            if payload is None:
                raise IOError("Invalid RESNUCLEi file")
            n_regions = (len(payload) - 4) // 8
            self.irrdt = struct.unpack("=i%df" % (2 * n_regions), payload)
        else:
            self.has_evolution = False
            self.irrdt = None

        for _ in range(1000):
            payload = read_record(handle)
            if payload is None:
                break

            size = len(payload)
            self.irrdt = None

            if size == 14:
                if payload[:8] == b"ISOMERS:":
                    self.isomer_count = struct.unpack("=10xi", payload)[0]
                    payload = read_record(handle)
                    payload = read_record(handle)
                    if payload is None:
                        break
                    size = len(payload)
                if payload[:10] == b"STATISTICS":
                    self.stats_offset = handle.tell()
                    break
            elif size != 38:
                raise IOError("Invalid RESNUCLEi file header size=%d" % size)

            nb, raw_name, det_type, region, volume, mhigh, zhigh, nmzmin = struct.unpack("=i10siif3i", payload)
            det = DetectorRecord(index=nb, name=raw_name.strip().decode())
            det.type = det_type
            det.region = region
            det.volume = volume
            det.mhigh = mhigh
            det.zhigh = zhigh
            det.nmzmin = nmzmin
            self.detectors.append(det)

            if self.has_evolution:
                payload = read_record(handle)
                self.t_decay = struct.unpack("=f", payload)[0]
            else:
                self.t_decay = 0.0

            size = det.zhigh * det.mhigh * 4
            if size != skip_record(handle):
                raise IOError("Invalid RESNUCLEi file")

        handle.close()
        return None

    def read_detector_data(self, index: int) -> bytes:
        handle = open(self.filename, "rb")
        skip_record(handle)
        if self.has_evolution:
            skip_record(handle)

        for _ in range(index):
            skip_record(handle)
            if self.has_evolution:
                skip_record(handle)
            skip_record(handle)
            if self.isomer_count:
                skip_record(handle)
                skip_record(handle)

        skip_record(handle)
        if self.has_evolution:
            skip_record(handle)
        payload = read_record(handle)
        handle.close()
        return payload

    def read_isomers(self, index: int):
        if self.isomer_count < 0:
            return None

        handle = open(self.filename, "rb")
        skip_record(handle)
        if self.has_evolution:
            skip_record(handle)

        for _ in range(index):
            skip_record(handle)
            if self.has_evolution:
                skip_record(handle)
            skip_record(handle)
            if self.isomer_count:
                skip_record(handle)
                skip_record(handle)

        skip_record(handle)
        if self.has_evolution:
            skip_record(handle)
        skip_record(handle)
        iso_header = read_record(handle)
        iso_payload = read_record(handle)
        handle.close()
        return iso_header, iso_payload

    def read_statistics(self, index: int):
        if self.stats_offset < 0:
            return None

        handle = open(self.filename, "rb")
        handle.seek(self.stats_offset)
        nskip = 7 * index if self.isomer_count else 6 * index
        for _ in range(nskip):
            skip_record(handle)

        total = read_record(handle)
        mass = read_record(handle)
        mass_error = read_record(handle)
        charge = read_record(handle)
        charge_error = read_record(handle)
        payload = read_record(handle)
        if self.isomer_count:
            iso = read_record(handle)
        else:
            iso = None
        handle.close()
        return total, mass, mass_error, charge, charge_error, payload, iso

    def describe_detector(self, index: int | None = None) -> None:
        if index is None:
            self.describe_header()
            return
        det = self.detectors[index]
        print("Bin    : ", det.index)
        print("Title  : ", det.name)
        print("Type   : ", det.type)
        print("Region : ", det.region)
        print("Volume : ", det.volume)
        print("Mhigh  : ", det.mhigh)
        print("Zhigh  : ", det.zhigh)
        print("NMZmin : ", det.nmzmin)


class UsrbdxFile(FlukaBinaryFile):
    """Reader for USRBDX boundary crossing files."""

    def read_header(self, filename: str):
        handle = super().read_header(filename)

        for _ in range(1000):
            payload = read_record(handle)
            if payload is None:
                break
            size = len(payload)

            if size == 14:
                self.stats_offset = handle.tell()
                for det in self.detectors:
                    data = unpack_floats(read_record(handle))
                    det.total = data[0]
                    det.total_error = data[1]
                    for _ in range(6):
                        skip_record(handle)
                break
            if size != 78:
                raise IOError("Invalid USRBDX file")

            header = struct.unpack("=i10siiiifiiiffifffif", payload)
            det = DetectorRecord(index=header[0], name=header[1].strip().decode())
            det.type = header[2]
            det.dist = header[3]
            det.reg1 = header[4]
            det.reg2 = header[5]
            det.area = header[6]
            det.twoway = header[7]
            det.fluence = header[8]
            det.lowneu = header[9]
            det.elow = header[10]
            det.ehigh = header[11]
            det.ne = header[12]
            det.de = header[13]
            det.alow = header[14]
            det.ahigh = header[15]
            det.na = header[16]
            det.da = header[17]
            self.detectors.append(det)

            if det.lowneu:
                payload = read_record(handle)
                det.ngroup = struct.unpack("=i", payload[:4])[0]
                det.egroup = struct.unpack("=%df" % (det.ngroup + 1), payload[4:])
            else:
                det.ngroup = 0
                det.egroup = []

            size = (det.ngroup + det.ne) * det.na * 4
            if size != skip_record(handle):
                raise IOError("Invalid USRBDX file")

        handle.close()
        return None

    def read_detector_data(self, index: int) -> bytes:
        handle = open(self.filename, "rb")
        skip_record(handle)
        for i in range(index):
            skip_record(handle)
            if self.detectors[i].lowneu:
                skip_record(handle)
            skip_record(handle)

        skip_record(handle)
        if self.detectors[index].lowneu:
            skip_record(handle)
        payload = read_record(handle)
        handle.close()
        return payload

    def read_statistics(self, index: int):
        if self.stats_offset < 0:
            return None
        handle = open(self.filename, "rb")
        handle.seek(self.stats_offset)
        for _ in range(index):
            for _ in range(7):
                skip_record(handle)
        for _ in range(6):
            skip_record(handle)
        payload = read_record(handle)
        handle.close()
        return payload

    def describe_detector(self, index: int | None = None) -> None:
        if index is None:
            self.describe_header()
            return
        det = self.detectors[index]
        print("BDX    : ", det.index)
        print("Title  : ", det.name)
        print("Type   : ", det.type)
        print("Dist   : ", det.dist)
        print("Reg1   : ", det.reg1)
        print("Reg2   : ", det.reg2)
        print("Area   : ", det.area)
        print("2way   : ", det.twoway)
        print("Fluence: ", det.fluence)
        print("LowNeu : ", det.lowneu)
        print("Energy : [", det.elow, "..", det.ehigh, "] ne=", det.ne, "de=", det.de)
        if det.lowneu:
            print("LOWNeut : [", det.egroup[-1], "..", det.egroup[0], "] ne=", det.ngroup)
        print("Angle  : [", det.alow, "..", det.ahigh, "] na=", det.na, "da=", det.da)
        print("Total  : ", det.total, "+/-", det.total_error)


class UsrbinFile(FlukaBinaryFile):
    """Reader for USRBIN volumetric scoring files."""

    def read_header(self, filename: str):
        handle = super().read_header(filename)

        for _ in range(1000):
            payload = read_record(handle)
            if payload is None:
                break
            size = len(payload)

            if size == 14 and payload[:10] == b"STATISTICS":
                self.stats_offset = handle.tell()
                break
            if size != 86:
                raise IOError("Invalid USRBIN file")

            header = struct.unpack("=i10siiffifffifffififff", payload)
            det = DetectorRecord(index=header[0], name=header[1].strip().decode())
            det.type = header[2]
            det.score = header[3]

            det.xlow = float(bmath.format(header[4], 9))
            det.xhigh = float(bmath.format(header[5], 9))
            det.nx = header[6]
            if det.nx > 0 and det.type not in (2, 12, 8, 18):
                det.dx = (det.xhigh - det.xlow) / float(det.nx)
            else:
                det.dx = float(bmath.format(header[7], 9))

            det.ylow = float(bmath.format(header[8], 9))
            det.yhigh = float(bmath.format(header[9], 9))
            if det.type in (1, 11):
                if abs(det.ylow + math.pi) < 1e-6:
                    det.ylow = -math.pi
                if abs(det.yhigh - math.pi) < 1e-6:
                    det.yhigh = math.pi
                elif abs(det.yhigh - math.pi * 2) < 1e-6:
                    det.yhigh = 2 * math.pi
            det.ny = header[10]
            if det.ny > 0 and det.type not in (2, 12, 8, 18):
                det.dy = (det.yhigh - det.ylow) / float(det.ny)
            else:
                det.dy = float(bmath.format(header[11], 9))

            det.zlow = float(bmath.format(header[12], 9))
            det.zhigh = float(bmath.format(header[13], 9))
            det.nz = header[14]
            if det.nz > 0 and det.type not in (2, 12):
                det.dz = (det.zhigh - det.zlow) / float(det.nz)
            else:
                det.dz = float(bmath.format(header[15], 9))

            det.lntzer = header[16]
            det.bk = header[17]
            det.b2 = header[18]
            det.tc = header[19]

            self.detectors.append(det)

            size = det.nx * det.ny * det.nz * 4
            if skip_record(handle) != size:
                raise IOError("Invalid USRBIN file")

        handle.close()
        return None

    def read_detector_data(self, index: int) -> bytes:
        handle = open(self.filename, "rb")
        skip_record(handle)
        for _ in range(index):
            skip_record(handle)
            skip_record(handle)
        skip_record(handle)
        payload = read_record(handle)
        handle.close()
        return payload

    def read_array(self, index: int):
        payload = unpack_floats(self.read_detector_data(index))
        dims = [self.detectors[index].nx, self.detectors[index].ny, self.detectors[index].nz]
        return numpy.reshape(payload, dims, order="F")

    def read_statistics(self, index: int):
        if self.stats_offset < 0:
            return None
        handle = open(self.filename, "rb")
        handle.seek(self.stats_offset)
        for _ in range(index):
            skip_record(handle)
        payload = read_record(handle)
        handle.close()
        return payload

    def describe_detector(self, index: int | None = None) -> None:
        if index is None:
            self.describe_header()
            return
        det = self.detectors[index]
        print("Bin    : ", det.index)
        print("Title  : ", det.name)
        print("Type   : ", det.type)
        print("Score  : ", det.score)
        print("X      : [", det.xlow, "-", det.xhigh, "] x", det.nx, "dx=", det.dx)
        print("Y      : [", det.ylow, "-", det.yhigh, "] x", det.ny, "dy=", det.dy)
        print("Z      : [", det.zlow, "-", det.zhigh, "] x", det.nz, "dz=", det.dz)
        print("L      : ", det.lntzer)
        print("bk     : ", det.bk)
        print("b2     : ", det.b2)
        print("tc     : ", det.tc)


class MgdrawFile:
    """Reader for MGDRAW event files."""

    def __init__(self, filename: str | None = None):
        self.reset()
        if filename is not None:
            self.open(filename)

    def reset(self) -> None:
        self.filename = ""
        self.handle = None
        self.event_count = 0
        self.data = None

    def open(self, filename: str):
        self.reset()
        self.filename = filename
        try:
            self.handle = open(self.filename, "rb")
        except IOError:
            self.handle = None
        return self.handle

    def close(self) -> None:
        if self.handle is not None:
            self.handle.close()

    def read_event(self, type_id: int | None = None):
        payload = read_record(self.handle)
        if payload is None:
            return None
        if len(payload) != 20:
            raise IOError("Invalid MGDRAW file")

        ndum, mdum, jdum, edum, wdum = struct.unpack("=iiiff", payload)
        self.event_count += 1

        if ndum > 0:
            if type_id is None or type_id == 0:
                self.read_tracking(ndum, mdum, jdum, edum, wdum)
            else:
                skip_record(self.handle)
            return 0
        if ndum == 0:
            if type_id is None or type_id == 1:
                self.read_energy(mdum, jdum, edum, wdum)
            else:
                skip_record(self.handle)
            return 1
        if type_id is None or type_id == 2:
            self.read_source(-ndum, mdum, jdum, edum, wdum)
        else:
            skip_record(self.handle)
        return 2

    def read_tracking(self, ntrack, mtrack, jtrack, etrack, wtrack):
        self.ntrack = ntrack
        self.mtrack = mtrack
        self.jtrack = jtrack
        self.etrack = etrack
        self.wtrack = wtrack
        payload = read_record(self.handle)
        if payload is None:
            raise IOError("Invalid track event")
        fmt = "=%df" % (3 * (ntrack + 1) + mtrack + 1)
        self.data = struct.unpack(fmt, payload)
        return ntrack

    def read_energy(self, icode, jtrack, etrack, wtrack):
        self.icode = icode
        self.jtrack = jtrack
        self.etrack = etrack
        self.wtrack = wtrack
        payload = read_record(self.handle)
        if payload is None:
            raise IOError("Invalid energy deposition event")
        self.data = struct.unpack("=4f", payload)
        return icode

    def read_source(self, ncase, npflka, nstmax, tkesum, weipri):
        self.ncase = ncase
        self.npflka = npflka
        self.nstmax = nstmax
        self.tkesum = tkesum
        self.weipri = weipri

        payload = read_record(self.handle)
        if payload is None:
            raise IOError("Invalid source event")
        fmt = "=" + ("i8f" * npflka)
        self.data = struct.unpack(fmt, payload)
        return ncase


def tab_lis(filename: str, detector: int, block: int = -1):
    with open(filename, "r") as handle:
        raw_data = handle.read()

    dataset = raw_data.split("\n\n\n")

    if block != -1:
        datablock = dataset[detector].split("\n\n")
        part = io.StringIO(datablock[block])
    else:
        part = io.StringIO(dataset[detector])

    name = part.readline().split()[1]
    x_bin_min, x_bin_max, x_vals, x_err = numpy.loadtxt(part, unpack=True)
    return name, x_bin_min, x_bin_max, x_vals, x_err


class TablisReader:
    """Parse detector names from ``_tab.lis`` files."""

    def __init__(self, filename: str):
        self.filename = filename

    def read(self, filename: str | None = None):
        if filename is not None:
            self.filename = filename

        self.data = []

        try:
            handle = open(self.filename, "r")
        except IOError:
            return None

        detector_index = 1
        half = 0
        block = 1
        last_index = 0
        name = "Detector"
        first = None
        for line in handle:
            if line == "\n":
                half += 1
                if half == 2:
                    half = 0
                    detector_index += 1
            elif "#" in line:
                match = _DETECTOR_LINE.match(line)
                if match:
                    name = match.group(1)
                    pos = name.find("(")
                    if pos > 0:
                        name = name[:pos]
                    name = name.strip()
                    entry = "%d %s" % (detector_index, name)
                    last_index = detector_index
                    if not first:
                        first = entry
                    half = 0
                    block = 0
                    continue
                match = _BLOCK_LINE.match(line)
                if match:
                    half = 1
                    continue
                if last_index != detector_index:
                    last_index = detector_index
            else:
                if half == 1:
                    block += 1
                half = 0
        handle.close()
