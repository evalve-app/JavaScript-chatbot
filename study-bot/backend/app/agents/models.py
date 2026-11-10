"""Builds the LLM model object from settings (kept in one place so the model is easy to swap)."""

from functools import lru_cache

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import get_settings


@lru_cache
def get_chat_model() -> OpenAIChatModel:
    settings = get_settings()
    return OpenAIChatModel(settings.openai_model, provider=OpenAIProvider(api_key=settings.openai_api_key))
