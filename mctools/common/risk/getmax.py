from abc import ABC, abstractmethod
import copy
import ctypes
from functools import cached_property
from io import StringIO
from pathlib import Path
import sys
from typing import Type
import warnings

import ROOT

ROOT.PyConfig.IgnoreCommandLineOptions = True


class Value:
    def __init__(self, val, err, bin_index, threshold=1.0e-20):
        self.val = val
        self.err = err
        self.relerr = 100.0  # \percent
        if val >= threshold:
            self.relerr = 100.0 * err / val
        else:
            warnings.warn(
                f"Value smaller than the user-defined threshold of {threshold}"
                "encountered. Arbitrarily setting its relative uncertainty to 100%."
            )
        self.bin_index = bin_index

    def __gt__(self, other):
        if isinstance(other, Value):
            return self.val > other.val
        return NotImplemented

    def __str__(self):
        return f"{self.val:.3g} ± {self.err:.1g}   {self.relerr:.1f} %"


class Zone:
    def __init__(
        self,
        name,
        title,
        hist,
        area,
        xmin=None,
        xmax=None,
        ymin=None,
        ymax=None,
        zmin=None,
        zmax=None,
    ):
        for coord, lo, hi in (("x", xmin, xmax), ("y", ymin, ymax), ("z", zmin, zmax)):
            if (lo is None) != (hi is None):
                raise ValueError(
                    f"Zone '{name}': {coord}min and {coord}max must both be set or both be unset"
                )
        self.name = name
        self.title = title
        self.xmin, self.xmax = xmin, xmax
        self.ymin, self.ymax = ymin, ymax
        self.zmin, self.zmax = zmin, zmax
        self.hist = hist
        self.area = area  # container area

    @cached_property
    def value(self):
        eps = 1e-3
        for axis, lo, hi in (
            (self.hist.GetXaxis(), self.xmin, self.xmax),
            (self.hist.GetYaxis(), self.ymin, self.ymax),
            (self.hist.GetZaxis(), self.zmin, self.zmax),
        ):
            if lo is not None:
                if abs(lo - hi) < eps:
                    lo, hi = lo - eps, hi + eps
                axis.SetRangeUser(lo, hi)
        b = self.hist.GetMaximumBin()
        val = self.hist.GetBinContent(b)
        err = self.hist.GetBinError(b)

        for axis in (self.hist.GetXaxis(), self.hist.GetYaxis(), self.hist.GetZaxis()):
            axis.SetRange()

        # if val < 1e-6:
        #         print(self.full_name, val, file=sys.stderr)
        return Value(val, err, b)

    def getValue(self):
        return self.value

    @property
    def full_name(self):
        return f"{self.area.full_name}.{self.name}"

    def Print(self, vals: list[float] | None = None, errs: list[float] | None = None):
        m = self.getValue()
        i, j, k = ctypes.c_int(0), ctypes.c_int(0), ctypes.c_int(0)
        self.hist.GetBinXYZ(m.bin_index, i, j, k)
        x = self.hist.GetXaxis().GetBinCenter(i.value)
        y = self.hist.GetYaxis().GetBinCenter(j.value)
        z = self.hist.GetZaxis().GetBinCenter(k.value)

        print(
            f"{self.title}: {m}\t coordinates: {x:.4f} {y:.4f} {z:.4f} \t {self.full_name}"
        )

        # print > 0.5 uSv/h in stderr:
        if m.val > 0.5 and not self.title.strip().startswith("One"):
            print(
                f"\033[31m Above 0.5 µSv/h: \033[0m {self.title}: {m}", file=sys.stderr
            )

        if vals is not None:
            vals.append(m.val)
        if errs is not None:
            errs.append(m.relerr)


class Area:
    """Area - a container for zones

    0m, 1m, Bulk, Duct, Max
    """

    def __init__(self, name, title, region, getHist=None):
        self.name = name
        self.title = title
        self.zones: list[Zone] = []
        # if true then just a collection of already existing zones for max calculation
        self.isVirtual = False
        self.region = region  # containing region
        self._getHist = getHist
        self.hist = None

    def checkZoneName(self, name):
        if name in [z.name for z in self.zones]:
            print(f"Error: zone {name} already exists", file=sys.stderr)
            sys.exit(1)

    def addZone(
        self,
        name,
        title,
        xmin=None,
        xmax=None,
        ymin=None,
        ymax=None,
        zmin=None,
        zmax=None,
        hist=None,
    ):
        self.checkZoneName(name)
        if isinstance(hist, str):
            if self._getHist is None:
                raise RuntimeError(
                    f"addZone '{name}': hist={hist!r} is a string but no getHist "
                    f"callable was provided to Region/Area"
                )
            hist = self._getHist(hist)
        z = Zone(
            name,
            title,
            hist if hist is not None else self.hist,
            self,
            xmin=xmin,
            xmax=xmax,
            ymin=ymin,
            ymax=ymax,
            zmin=zmin,
            zmax=zmax,
        )
        self.zones.append(z)
        return z

    def addZoneDefined(self, z, newName=None):
        """
        add already-defined zone into the zone list
        newName must be defined if a zone with z.name already exists
        """
        if newName is not None:
            new_zone = copy.copy(z)
            new_zone.name = newName
        self.checkZoneName(new_zone.name)
        self.zones.append(new_zone)

    def addZoneMax(self, name="Max", zones=None, title=None):
        if zones is None:  # use all zones
            zones = [z.name for z in self.zones]
            if title is None:
                title = f" * Maximum over the whole {self.region.name}.{self.name} area"
            return self.addZoneMax(name, zones, title)
        # use the specified zones only
        if title is None:
            title = " * Maximum of the " + " ".join(list(zones)) + " zones"
        a = Area(name, title, self)
        for _name in zones:
            z = self.getZone(_name)
            if z is None:
                print(f"Not found: {_name}", file=sys.stderr)
                sys.exit(1)
            a.zones.append(z)
        self.zones.append(a)
        a.isVirtual = True
        return a

    def getZone(self, name):
        """Return zone by its name"""
        # generator expression:
        z = next((obj for obj in self.zones if obj.name == name), None)
        if z is None:
            raise LookupError(f"Zone not found: {name}")
        return z

    def getValue(self):
        values = []
        for z in self.zones:
            values.append(z.getValue())
        return max(values)

    @property
    def full_name(self):
        return f"{self.region.name}.{self.name}"

    def Print(self, vals: list[float] | None = None, errs: list[float] | None = None):
        if self.isVirtual:
            print(f"{self.title}:", self.getValue())
        else:
            for z in self.zones:
                z.Print(vals=vals, errs=errs)


class Region:
    """Region - a container for areas

    Inside, Klystron, AccessSide, Access, Roof, Outside, Max
    """

    def __init__(self, name, title, getHist=None):
        self.name = name
        self.title = title
        self.area: dict[str, Area] = {}
        self._getHist = getHist

    def checkAreaName(self, name):
        if name in self.area:
            print(f"Error: area {name} already exists", file=sys.stderr)
            sys.exit(1)

    def addArea(self, name):
        self.checkAreaName(name)
        self.area[name] = Area(name, "", self, getHist=self._getHist)
        return self.area[name]

    def getArea(self, name):
        return self.area[name]

    def addAreaMax(self, name="Max"):
        areas = self.area.copy()
        self.checkAreaName(name)
        self.area[name] = Area(
            name, f"* Maximum over the whole {self.name} region", self
        )
        self.area[name].isVirtual = True
        for a in areas.values():
            self.area[name].zones.append(a)

    def Print(self, vals: list[float] | None = None, errs: list[float] | None = None):
        print("#", self.title)
        for a in self.area.values():
            a.Print(vals=vals, errs=errs)


class Scenario:
    """Scenario - a container for configurations"""

    def __init__(
        self,
        name: str,
        root_file_name: Path | None = None,
        scale_file_name: Path | None = None,
    ):
        self.name = name
        self.root_file_name = root_file_name
        self.scale_file_name = scale_file_name
        self.configurations: list[Configuration] = []

    def addConfig(self, c):
        self.configurations.append(c)

    def getConfig(self, name):
        """Return configuration by its name"""
        # generator expression:
        c = next((obj for obj in self.configurations if obj.name == name), None)
        if c is None:
            raise LookupError(f"Configuration not found: {name}")
        return c

    def getValue(self, config, region, area, zone):
        c = self.getConfig(config)
        r = c.getRegion(region)
        a = r.getArea(area)
        z = a.getZone(zone)
        return z.getValue()

    def setValue(self, config, region, area, zone, value):
        c = self.getConfig(config)
        r = c.getRegion(region)
        a = r.getArea(area)
        z = a.getZone(zone)
        z.value = value

    def Print(self, config, region, area, zone):
        val = self.getValue(config, region, area, zone)
        print(f"{self.name}.{config}.{region}.{area}.{zone}", val)


class Configuration(ABC):
    def __init__(self, name, rootfname=None, scalefname="scale.txt"):
        self.name = name
        self.regions: list[Region] = []

        if rootfname is None:
            rootfname = name + ".root"

        self.scale = self.getScale(scalefname)

        self._hists = {}
        self._rootfile = ROOT.TFile(rootfname)

        self.evaluate()

    @abstractmethod
    def evaluate(self): ...

    def getScale(self, fname):
        with open(fname, encoding="utf-8") as f:
            return float(f.readline())

    def getHist(self, hname):
        """Load and cache a histogram from the ROOT file. Only valid during __init__."""
        if hname not in self._hists:
            h = self._rootfile.Get(hname)
            assert h, f"Histogram {hname} is not found in {self._rootfile.GetName()}"
            h.Scale(self.scale)
            h.SetDirectory(0)
            self._hists[hname] = h
        return self._hists[hname]

    def addRegion(self, name, title):
        r = Region(name, title, getHist=self.getHist)
        self.regions.append(r)
        return r

    def getRegion(self, name):
        """Return region by its name"""
        # generator expression:
        r = next((obj for obj in self.regions if obj.name == name), None)
        if r is None:
            raise LookupError(f"Region not found: {name}")
        return r


class Case:
    def __init__(
        self,
        name: str,
        scenarios: list[Scenario],
        configuration_names: list[str],
        configuration: Type[Configuration],
    ):
        self.name = name
        self.scenarios = scenarios
        self.configuration_names = configuration_names
        self.configuration = configuration

    def initialize(self):
        for scenario in self.scenarios:
            for configuration_name in self.configuration_names:
                scenario.addConfig(
                    self.configuration(
                        name=configuration_name,
                        # ROOT.TFile() incompatible with pathlib.Path
                        rootfname=str(scenario.root_file_name),
                        scalefname=scenario.scale_file_name,
                    )
                )

            createMaxConfiguration(s=scenario)

    def toLaTeX(
        self,
        command_output_file_name: Path | None = None,
        variable_output_file_name: Path | None = None,
    ):
        commands = self.createLaTeXCommands()
        if command_output_file_name is not None:
            with open(
                command_output_file_name, "w", encoding="utf-8"
            ) as command_output_file:
                command_output_file.write(commands)
        else:
            print(commands)

        variables = self.createAllVariableLaTeX(
            command_output_file_name=command_output_file_name
        )
        if variable_output_file_name is not None:
            with open(
                variable_output_file_name, "w", encoding="utf-8"
            ) as variable_output_file:
                variable_output_file.write(variables)
        else:
            print(variables)

    def createLaTeXCommands(self) -> str:
        buffer = [
            "% This file is generated by getmax.py. Don't edit it by hand.\n"
            "\\definecolor{abovequater}{HTML}{ff8b00} % for dose rates > 0.25 uSv/h\n"
            "\\definecolor{abovehalf}{HTML}{ff0000}   % for dose rates > 0.5 uSv/h\n"
            "\\newcommand\\bigerror{\\textcolor{red}{(BIG ERROR!)}}\n"
            "\\NewDocumentCommand\\rate{mmmmg}{%\n"
            "  % 1: scenario\n"
            "  % 2: region\n"
            "  % 3: area\n"
            "  % 4: zone\n"
        ]

        for scenario in self.scenarios:
            buffer.append(
                f"% Scenario: {scenario.name}\n"
                r"  \ifthenelse{\equal{#1}{"
                f"{scenario.name}"
                "}}{\n"
            )
            for region in scenario.configurations[0].regions:
                buffer.append(r"      \ifthenelse{\equal{#2}{" f"{region.name}" "}}{\n")
                for area in region.area:
                    buffer.append(
                        r"        \ifthenelse{\equal"
                        "{#3}{" + f"{area}"
                        "}}{% "
                        f"{region.area[area].full_name}\n"
                    )
                    for zone in region.area[area].zones:
                        buffer.append(
                            r"          \ifthenelse{\equal{#4}{"
                            f"{zone.name}"
                            "}}{"
                            f"{getPrintedValue(value=zone.getValue())}"
                            "}{"
                            f"% {zone.full_name}\n"
                        )
                    buffer.append(
                        "        " + ("}" * len(region.area[area].zones)) + "\n"
                    )
                    buffer.append("      }{}%\n")
                buffer.append("    }{}%\n")
            buffer.append("  }{}%\n")
        buffer.append("}%\n")
        return "".join(buffer)

    def createAllVariableLaTeX(self, command_output_file_name: Path) -> str:
        buffer = [
            r"\documentclass{article}"
            "\n\n"
            r"\usepackage{ifthen}"
            "\n"
            r"\usepackage{siunitx}"
            "\n"
            r"\sisetup{round-mode = uncertainty, round-precision = 1}"
            "\n"
            r"\usepackage{tikz}"
            "\n"
            "\n"
            r"\usepackage{xstring}"
            "\n"
            "\n"
            r"\usepackage{xparse}"
            "\n"
            "\n\n"
            r"\input{"
            f"{command_output_file_name}"
            "}\n\n"
            r"\newcommand\print{%"
            "\n"
            r"  \scenario.\region.\area.\zone : \value"
            "\n}\n\n"
            r"\begin{document}"
            "\n"
            r"\tableofcontents"
            "\n"
        ]

        for scenario in self.scenarios:
            buffer.append(r"\section{" f"{scenario.name}" "}")
            buffer.append(r"\def\scenario{" f"{scenario.name}" "}\n")
            for configuration in scenario.configurations:
                for region in configuration.regions:
                    buffer.append(r"\def\region{" f"{region.name}" "}\n")
                    for area in region.area.keys():
                        buffer.append(r"\def\area{" f"{region.area[area].name}" "}\n")
                        for zone in region.area[area].zones:
                            buffer.append(r"\def\zone{" f"{zone.name}" "}\n")
                            buffer.append(
                                r"\def\value{\rate{"
                                f"{scenario.name}"
                                "}{"
                                f"{region.name}"
                                "}{"
                                f"{region.area[area].name}"
                                "}{"
                                f"{zone.name}"
                                "}}\n"
                                r"\print"
                                "\n\n"
                            )
        buffer.append(r"\end{document}")
        return "".join(buffer)


def getPrintedValue(val=None, err=None, value: Value | None = None):
    """Return a string with the value to be printed

    If value is zero, no error is printed
    """
    if value is not None:
        val = value.val
        err = value.err

    epsilon = 1e-10
    color = ""
    bigerror = ""
    if val > 0.25:
        color = "[color=abovequater]"
    if val > 0.5:
        color = "[color=abovehalf]"

    if abs(val) > epsilon and err / val > 0.2:
        bigerror = " \\bigerror"
    return (
        "\\num{0.0}"
        if abs(val) < epsilon
        else "\\num%s{%f +- %f}%s" % (color, val, err, bigerror)
    )


def createMaxConfiguration(s: Scenario):
    """Create 'Max' configuration for the given scenario"""
    try:
        cmax = copy.deepcopy(s.getConfig("1A"))
    except LookupError:
        raise (
            ValueError(
                "The scenario must contain a configuration with "
                "the name '1A' which will be used as a template for the 'Max' "
                "scenario."
            )
        )
    cmax.name = "Max"
    s.addConfig(cmax)

    for c in s.configurations:
        if c.name == "Max":
            continue
        for r in c.regions:
            for a in r.area.keys():
                for z in r.getArea(a).zones:
                    vmax = s.getValue(cmax.name, r.name, a, z.name)
                    v = s.getValue(c.name, r.name, a, z.name)
                    if v > vmax:
                        s.setValue(cmax.name, r.name, a, z.name, v)


def find_scenario_root_files(path: Path = Path.cwd()) -> list[str]:
    root_files = []
    for element in path.iterdir():
        if element.suffix == ".root":
            root_files.append(element.stem)
    return root_files


def printRate(confnames, configuration: Type[Configuration], root="."):
    path = Path(root)

    all_confnames = list(confnames) + ["Max"]

    buffer = StringIO()
    print("% This file is generated by getmax.py. Don't edit it by hand.", file=buffer)
    print("%", file=buffer)
    print("% Usage:", file=buffer)
    print("%    (let's assume this file is called 'rates.tex')", file=buffer)
    print(
        r"% 1. Load this file in your document preamble: \input{rates.tex}", file=buffer
    )
    print(
        "% 2. If needed, redefine the 'abovequater' and 'abovehalf' colours as"
        "well as the 'bigerror' command after loading rates.tex. For instance:",
        file=buffer,
    )
    print("% \\definecolor{abovequater}{HTML}{000000}", file=buffer)
    print("% \\definecolor{abovehalf}{HTML}{000000}", file=buffer)
    print("% \\renewcommand\\bigerror{}", file=buffer)
    print(file=buffer)
    print(
        "\\definecolor{abovequater}{HTML}{ff8b00} % for dose rates > 0.25 uSv/h",
        file=buffer,
    )
    print(
        "\\definecolor{abovehalf}{HTML}{ff0000}   % for dose rates > 0.5 uSv/h",
        file=buffer,
    )
    print(
        "\\newcommand\\bigerror{\\textcolor{red}{(BIG ERROR!)}} %"
        "postfix for values with relative error above 20%",
        file=buffer,
    )
    print(file=buffer)
    print("\\NewDocumentCommand\\rate{mmmmg}{%", file=buffer)
    print("  % 1: scenario", file=buffer)
    print("  % 2: configuration", file=buffer)
    print("  % 3: region", file=buffer)
    print("  % 4: area", file=buffer)
    print("  % 5: zone", file=buffer)

    for folder in path.iterdir():
        if not folder.name.startswith("conf-"):
            continue
        sname = folder.name.removeprefix("conf-")
        print("% Scenario:", sname, file=buffer)

        s = Scenario(sname)
        for name in confnames:
            rootfname = f"{folder}/{name}.root"
            scalefname = f"{folder}/scale.txt"
            c = configuration(name=name, rootfname=rootfname, scalefname=scalefname)
            s.addConfig(c)

        createMaxConfiguration(s)

        print(r"  \\ifthenelse{\equal" + "{#1}{%s}}{" % sname, end="%\n", file=buffer)
        for cname in all_confnames:
            print(
                r"    \\ifthenelse{\equal" + "{#2}{%s}}{" % cname,
                end="%\n",
                file=buffer,
            )

            c = s.getConfig(cname)
            for r in c.regions:
                print(
                    r"      \\ifthenelse{\equal" + "{#3}{%s}}{" % r.name,
                    end="%\n",
                    file=buffer,
                )
                for a in r.area.keys():
                    print(
                        r"        \\ifthenelse{\equal" + "{#4}{%s}}{" % a,
                        end="%\n",
                        file=buffer,
                    )
                    nspace = 10
                    if a == "Max":
                        value = r.area[a].getValue()
                        val = value.val
                        err = value.err
                        print(
                            " " * nspace,
                            "\\IfValueTF{#5}{\\textcolor{red}{Error: The Zone argument"
                            "must be removed with the Max area}}{%s}"
                            % getPrintedValue(val, err),
                            end=f"% {r.area[a].full_name}\n",
                            file=buffer,
                        )
                    else:
                        for z in r.getArea(a).zones:
                            value = s.getValue(cname, r.name, a, z.name)
                            val = value.val
                            err = value.err
                            print(
                                " " * nspace,
                                r"\\ifthenelse{\equal"
                                + "{#5}{%s}}{%s}{"
                                % (z.name, getPrintedValue(val, err)),
                                end=f"% {z.full_name}\n",
                                file=buffer,
                            )
                            nspace += 1
                    print(" " * 10, "}" * (nspace - 10), end="%\n", file=buffer)
                    print("        }{}%", file=buffer)
                print("      }{}%", file=buffer)
            print("    }{}%", file=buffer)
        print("    }{}%", file=buffer)
    print("}%", file=buffer)
    print(buffer.getvalue(), end="")
