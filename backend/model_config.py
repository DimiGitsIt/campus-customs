"""Single place that constructs the PydanticAI model. Every agent file
imports get_model() from here instead of constructing its own model or
hardcoding a model name string.

Uses Portkey as an OpenAI-compatible gateway: an AsyncOpenAI client pointed
at Portkey's base URL, wrapped in PydanticAI's OpenAIChatModel/OpenAIModel
(whichever the installed pydantic_ai version provides) via OpenAIProvider.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DEFAULT_MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

try:
    from pydantic_ai.models.openai import OpenAIChatModel as _OpenAIModelClass
except ImportError:  # older pydantic_ai only has OpenAIModel
    from pydantic_ai.models.openai import OpenAIModel as _OpenAIModelClass

from pydantic_ai.providers.openai import OpenAIProvider

_model = None


def get_model():
    """Return a singleton PydanticAI model wired through Portkey."""
    global _model
    if _model is not None:
        return _model

    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set in the environment/.env")

    model_name = os.environ.get("MODEL_NAME", DEFAULT_MODEL_NAME) or DEFAULT_MODEL_NAME

    client = AsyncOpenAI(api_key=api_key, base_url=PORTKEY_BASE_URL)
    provider = OpenAIProvider(openai_client=client)
    # gpt-6-luna rejects function tools combined with reasoning_effort on the
    # chat completions endpoint unless reasoning_effort is explicitly 'none'.
    _model = _OpenAIModelClass(
        model_name,
        provider=provider,
        settings={"openai_reasoning_effort": "none"},
    )
    return _model
