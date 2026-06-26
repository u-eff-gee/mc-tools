from mctools.common.risk.level import BaseLevel, depth_first_search_with_path, Level
from mctools.common.risk.value import Value


class SourceCombination(BaseLevel):
    def __init__(self, combination: list[list[str]], name: str = "", title: str = ""):
        super().__init__(name=name, title=title)
        self.combination = combination
        self.sources: dict[str, Level] | None = None

    def set_sources(self, sources: dict[str, Level]):
        self.sources = sources

    def evaluate(self):
        values: list[Value] = []
        for source in self.combination:
            level: BaseLevel = self.sources[source[0]]
            for lvl in source[1:]:
                level = level[lvl]
            values.append(level.get_max_value())
        self.value = max(values)


class Data:
    def __init__(
        self,
        sources: dict[str, Level],
        cross_level_combinations: dict[str, SourceCombination] | None = None,
    ):
        self.sources = sources
        self.cross_level_combinations: dict[str, SourceCombination] = {}
        if cross_level_combinations is not None:
            self.cross_level_combinations = cross_level_combinations

    def set_sub_level_paths(self, separator: str = ".", path_prefix: str = ""):
        for source in self.sources:
            self.sources[source].path = path_prefix + source
            self.sources[source].set_sub_level_paths(separator=separator)
        for combo in self.cross_level_combinations:
            self.cross_level_combinations[combo].name = combo
            self.cross_level_combinations[combo].path = path_prefix + combo

    def get_results(self) -> tuple[tuple[str], Value]:
        """Return the results as a flat list"""
        data: tuple[tuple[str], Value] = []
        for source in self.sources:
            data.append(
                ((self.sources[source].path,), self.sources[source].get_max_value())
            )
            for path, zone in depth_first_search_with_path(self.sources[source]):
                data.append((path, zone.get_max_value()))
        for combo in self.cross_level_combinations:
            data.append(
                (
                    (self.cross_level_combinations[combo].path,),
                    self.cross_level_combinations[combo].get_max_value(),
                )
            )
        return data
    
    def __getitem__(self, key: str):
        if key in self.sources:
            return self.sources[key]
        return self.cross_level_combinations[key]

    def evaluate(self):
        for source in self.sources:
            self.sources[source].evaluate()

        for combo in self.cross_level_combinations:
            self.cross_level_combinations[combo].set_sources(self.sources)
            self.cross_level_combinations[combo].evaluate()
