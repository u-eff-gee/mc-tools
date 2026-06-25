"""Hierarchy of logical levels with associated sublevels"""

from abc import abstractmethod

from value import UnknownValue, Value


class BaseLevel:
    """Base level without sublevels"""

    def __init__(self, name: str = "", title: str = ""):
        self.name = name
        if self.name != "" and title == "":
            self.title = name
        self.value: Value = UnknownValue()

    def get_max_value(self) -> Value:
        """Retrieve the maximum value. If unknown, evaluate it first."""
        if isinstance(self.value, UnknownValue):
            self.evaluate()
        return self.value

    @abstractmethod
    def evaluate(self):
        """Evaluate the maximum value"""


class Level(BaseLevel):
    """Upper and intermediate level with sublevels"""

    def __init__(
        self,
        name: str = "",
        title: str = "",
        sub_levels: dict[str, "Level"] | None = None,
    ):
        super().__init__(name=name, title=title)
        if sub_levels is None:
            self.sub_levels: dict[str, Level] = {}
        else:
            self.sub_levels = sub_levels

    def evaluate(self):
        """Find the maximum value of all sublevels"""
        self.value = max(
            self.sub_levels[sub_level].get_max_value() for sub_level in self.sub_levels
        )
