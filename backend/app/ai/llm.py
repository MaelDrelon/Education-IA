from functools import lru_cache

from ..config import settings


def use_fake() -> bool:
    """Mode simulé : permet de développer et tester sans clé API."""
    return settings.llm_provider == "fake"


@lru_cache
def anthropic_client():
    import anthropic
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquante (ou mettre LLM_PROVIDER=fake)")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)
