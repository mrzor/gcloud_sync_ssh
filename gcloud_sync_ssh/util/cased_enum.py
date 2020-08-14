from enum import Enum


class LowercaseStringEnum(str, Enum):
    def __init__(self, *args):
        cname = self.__class__.__name__

        if self.name.lower() != self.name:
            raise NameError("fname {self.name} must be lowercase in {cname}")

        if self.value.lower() != self.value:
            raise ValueError(f"value {self.value} must be lowercase in {cname}")

    @classmethod
    def _missing_(cls, value):
        return cls[value.lower()]


class UppercaseStringEnum(str, Enum):
    def __init__(self, *args):
        cname = self.__class__.__name__

        if self.name.upper() != self.name:
            raise NameError(f"name {self.name} must be uppercase in {cname}")

        if self.value.upper() != self.value:
            raise ValueError(f"value {self.value} must be uppercase in {cname}")

    @classmethod
    def _missing_(cls, value):
        return cls[value.upper()]
