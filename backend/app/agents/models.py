"""Builds LLM model objects from settings (kept in one place so the model is easy to swap)."""

from functools import lru_cache

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import get_settings


@lru_cache
def chat_model_named(model_name: str) -> OpenAIChatModel:
    settings = get_settings()
    return OpenAIChatModel(model_name, provider=OpenAIProvider(api_key=settings.openai_api_key))


def get_chat_model() -> OpenAIChatModel:
    return chat_model_named(get_settings().openai_model)
