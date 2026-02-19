import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from attributes.llm import LLMExtractConfig, llm_generate_text
from attributes.types import AttributeType

logger = logging.getLogger(__name__)


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

    @property
    def llm_extract_config(self) -> Optional[LLMExtractConfig]:
        """Override to enable LLM extraction. Default: None (LLM not used)."""
        return None

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

    def extract_with_llm(self, project_data: Dict[str, Any]) -> Any:
        """
        Extract attribute value, optionally refining with LLM.

        1. Call extract(project_data) to get raw_value
        2. If llm_extract_config is None, return raw_value as-is
        3. Format the user prompt with {value}=raw_value and project_data keys
        4. Call LLM, validate with condition, retry up to max_retries on failure
        5. If all retries fail validation, return last LLM result with a warning
        """
        raw_value = self.extract(project_data)

        config = self.llm_extract_config
        if config is None:
            return raw_value

        # Build the user prompt
        format_kwargs = {**project_data, "value": raw_value}
        user_prompt = config.user_prompt_template.format_map(
            _SafeFormatDict(format_kwargs)
        )

        last_result = None
        for attempt in range(1, config.max_retries + 1):
            try:
                result = llm_generate_text(
                    config.system_prompt,
                    user_prompt,
                    base_url=config.base_url,
                    model_name=config.model_name,
                )
                if config.response_parser is not None:
                    result = config.response_parser(result).strip()
                last_result = result

                if config.condition is None or config.condition(result):
                    return result

                logger.warning(
                    "[%s] LLM result failed condition (attempt %d/%d): %r",
                    self.key, attempt, config.max_retries, result,
                )
            except Exception as e:
                logger.warning(
                    "[%s] LLM call failed (attempt %d/%d): %s",
                    self.key, attempt, config.max_retries, e,
                )
                last_result = last_result  # keep previous result if any

        # All retries exhausted
        if last_result is not None:
            logger.warning(
                "[%s] All %d retries failed condition; returning last LLM result: %r",
                self.key, config.max_retries, last_result,
            )
            return last_result

        logger.warning(
            "[%s] All %d retries failed; falling back to raw extract value: %r",
            self.key, config.max_retries, raw_value,
        )
        return raw_value


class _SafeFormatDict(dict):
    """Dict that returns '{key}' for missing keys instead of raising KeyError."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
