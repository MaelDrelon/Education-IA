from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./app.db"
    jwt_secret: str = "change-me-en-prod-cle-de-32-caracteres-min"
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173"

    # IA : "fake" (simulé, sans clé), "anthropic" (API Claude) ou "ollama" (modèle local)
    llm_provider: str = "fake"
    anthropic_api_key: str | None = None
    llm_model: str = "claude-sonnet-5-5"

    # Ollama : modèle local, doit gérer les appels d'outils (ex. qwen3, llama3.1, mistral-small)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    ollama_timeout: float = 300.0  # secondes ; un modèle local sur CPU peut être lent


settings = Settings()
