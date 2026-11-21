"""Global settings and configuration for OmniPDF2MD."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime configuration."""

    model_config = SettingsConfigDict(env_prefix="OMNIPDF_", env_file=".env", extra="ignore")

    default_batch_size: int = 15
    default_ocr_langs: list[str] = ["en", "vi"]
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5vl"
    default_image_dpi: int = 200
    default_output_dir: Path = Path("output")


settings = Settings()
