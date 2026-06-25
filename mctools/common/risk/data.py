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
                level = level.sub_levels[lvl]
            values.append(level.value)
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

    def evaluate(self):
        for source in self.sources:
            self.sources[source].evaluate()

        for combo in self.cross_level_combinations:
            self.cross_level_combinations[combo].set_sources(self.sources)
            self.cross_level_combinations[combo].evaluate()
