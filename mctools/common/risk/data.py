from mctools.common.risk.level import BaseLevel, Level
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
            values.append(level.value)
        self.value = max(values)


class Data:
    def __init__(
        self,
        sources: dict[str, Level],
        cross_level_combinations: dict[str, SourceCombination] | None = None,
    ):
        self.sources = sources
        self.set_sub_level_paths()
        self.cross_level_combinations: dict[str, SourceCombination] = {}
        if cross_level_combinations is not None:
            self.cross_level_combinations = cross_level_combinations

    def set_sub_level_paths(self, separator: str = "."):
        for source in self.sources:
            self.sources[source].path = source
            self.sources[source].set_sub_level_paths(separator=separator)

    def evaluate(self):
        for source in self.sources:
            self.sources[source].evaluate()

        for combo in self.cross_level_combinations:
            self.cross_level_combinations[combo].set_sources(self.sources)
            self.cross_level_combinations[combo].evaluate()
