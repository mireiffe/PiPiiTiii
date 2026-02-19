"""
LLM extraction support for attributes.

Provides LLMExtractConfig dataclass and a synchronous llm_generate_text helper
that calls OpenAI-compatible /chat/completions endpoints.
"""

import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TRUST_ENV = os.environ.get("TRUST_ENV", "true").lower() == "true"


@dataclass(frozen=True)
class LLMExtractConfig:
    """Declarative configuration for LLM-based attribute extraction."""

    system_prompt: str
    user_prompt_template: str  # {value} = extract() result; project_data keys also available
    condition: Optional[Callable[[str], bool]] = None  # validation function for LLM output
    max_retries: int = 3
    base_url: Optional[str] = None  # per-attribute override (falls back to ATTR_LLM_BASE_URL env)
    model_name: Optional[str] = None  # per-attribute override (falls back to ATTR_LLM_MODEL env)


def llm_generate_text(
    system_prompt: str,
    user_prompt: str,
    *,
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
) -> str:
    """
    Synchronous helper that calls an OpenAI-compatible /chat/completions endpoint.

    Falls back to ATTR_LLM_* environment variables when not provided.
    API key is read from ATTR_LLM_API_KEY (fallback: LLM_API_KEY).
    """
    endpoint = base_url or os.getenv("ATTR_LLM_BASE_URL", "https://api.openai.com/v1")
    endpoint = endpoint.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint = f"{endpoint}/chat/completions"

    model = model_name or os.getenv("ATTR_LLM_MODEL", "gpt-4o")
    api_key = os.getenv("ATTR_LLM_API_KEY") or os.getenv("LLM_API_KEY", "")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    with httpx.Client(timeout=60.0, trust_env=TRUST_ENV) as client:
        response = client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
