from abc import ABC, abstractmethod
from typing import Any, Dict

from attributes.types import AttributeType


class BaseAttribute(ABC):
    """
    Base class for defining project attributes.
    Users should inherit from this class to define custom attributes.
    """

    @property
    @abstractmethod
    def key(self) -> str:
        """
        Unique identifier for the attribute.
        This will be used as the column name in the database.
        Must be alphanumeric and lowercase.
        """
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable name for the attribute.
        This will be used in the UI.
        """
        pass

    @property
    @abstractmethod
    def attr_type(self) -> AttributeType:
        """
        Additional metadata describing how this attribute should be handled.
        This is primarily used to drive UI behaviours such as filtering styles.
        """
        pass

    @abstractmethod
    def extract(self, project_data: Dict[str, Any]) -> Any:
        """
        Calculate the attribute value from the project data.

        Args:
            project_data: A dictionary containing project metadata and content.
                          It typically includes 'original_filename', 'title', 'slide_count', etc.

        Returns:
            The calculated value for the attribute.
            Should be a simple type (str, int, float, bool) suitable for DB storage.
        """
        pass
