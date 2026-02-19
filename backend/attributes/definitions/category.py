from typing import Any, Dict

from attributes.base import BaseAttribute
from attributes.llm import LLMExtractConfig
from attributes.types import FilteringAttributeType

VALID_CATEGORIES = {"현상분석", "원인분석", "대책수립", "기타"}


class CategoryAttribute(BaseAttribute):
    @property
    def key(self) -> str:
        return "category"

    @property
    def display_name(self) -> str:
        return "Category"

    @property
    def attr_type(self) -> FilteringAttributeType:
        return FilteringAttributeType(variant="multi_select")

    @property
    def llm_extract_config(self) -> LLMExtractConfig:
        return LLMExtractConfig(
            system_prompt=(
                "당신은 기술 문서 분류 전문가입니다. "
                "주어진 제목과 파일명을 보고 아래 카테고리 중 하나로 분류하세요.\n"
                "카테고리: 현상분석, 원인분석, 대책수립, 기타\n"
                "반드시 카테고리 이름만 출력하세요."
            ),
            user_prompt_template=(
                "제목: {value}\n"
                "파일명: {original_filename}\n"
                "분류하세요."
            ),
            condition=lambda r: r in VALID_CATEGORIES,
            max_retries=3,
        )

    def extract(self, project_data: Dict[str, Any]) -> Any:
        return project_data.get("title", "")
