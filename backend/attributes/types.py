from dataclasses import dataclass, asdict
from typing import Literal, TypedDict

FilteringVariant = Literal["multi_select", "range", "toggle"]


class AttributeTypeDict(TypedDict):
    category: Literal["filtering"]
    variant: FilteringVariant


@dataclass(frozen=True)
class FilteringAttributeType:
    """Metadata describing how an attribute should behave in the UI."""

    category: Literal["filtering"] = "filtering"
    variant: FilteringVariant = "multi_select"

    def asdict(self) -> AttributeTypeDict:
        return asdict(self)  # type: ignore[return-value]


AttributeType = FilteringAttributeType
