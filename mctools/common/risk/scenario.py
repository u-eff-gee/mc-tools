from pathlib import Path

from mctools.common.risk.data import Data
from mctools.common.risk.level import depth_first_search
from mctools.common.risk.zone import ROOTFileInput, Zone


class Scenario:
    def __init__(
        self,
        name: str,
        data: Data,
        root_file_name: Path | None = None,
        scale_file_name: Path | None = None,
    ):
        self.name = name
        self.data = data
        self.root_file_name = root_file_name
        self.scale_file_name = scale_file_name

        for source in self.data.sources:
            for base_level in depth_first_search(data.sources[source]):
                if isinstance(base_level, Zone):
                    hist_name = base_level.hist
                    base_level.hist = ROOTFileInput(
                        root_file_name=self.root_file_name,
                        histogram_name=hist_name,
                        scale_file_name=scale_file_name,
                    )

    def evaluate(self):
        self.data.evaluate()
