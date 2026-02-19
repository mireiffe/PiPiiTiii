"""
LLM extraction support for attributes.

Provides LLMExtractConfig dataclass and a synchronous llm_generate_text helper
that calls OpenAI-compatible /chat/completions endpoints.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TRUST_ENV = os.environ.get("TRUST_ENV", "true").lower() == "true"
SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "settings.json"
)


@dataclass(frozen=True)
class LLMExtractConfig:
    """Declarative configuration for LLM-based attribute extraction."""

    system_prompt: str
    user_prompt_template: str  # {value} = extract() result; project_data keys also available
    condition: Optional[Callable[[str], bool]] = None  # validation function for LLM output
    max_retries: int = 3
    base_url: Optional[str] = None  # per-attribute override (falls back to settings.json)
    model_name: Optional[str] = None  # per-attribute override (falls back to settings.json)


def _load_llm_settings() -> dict:
    """Load LLM settings from settings.json."""
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("llm", {})
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def llm_generate_text(
    system_prompt: str,
    user_prompt: str,
    *,
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
) -> str:
    """
    Synchronous helper that calls an OpenAI-compatible /chat/completions endpoint.

    Falls back to settings.json for base_url / model_name when not provided.
    API key is read from the LLM_API_KEY environment variable.
    """
    llm_settings = _load_llm_settings()

    endpoint = base_url or llm_settings.get("api_endpoint", "https://api.openai.com/v1")
    endpoint = endpoint.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint = f"{endpoint}/chat/completions"

    model = model_name or llm_settings.get("model_name", "gpt-4o")
    api_key = os.getenv("LLM_API_KEY", "")

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
