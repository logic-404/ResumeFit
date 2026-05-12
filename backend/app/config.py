from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    openai_api_key: str

    extraction_model: str = "gpt-5.4-nano"
    generation_model: str = "gpt-5.4-mini"
    embedding_model: str = "text-embedding-3-small"

    langchain_tracing_v2: bool = False
    langchain_project: str = "resumefit"
    langchain_api_key: str = ""

    brave_search_api_key: str = ""

    app_env: str = "development"
    app_port: int = 8000
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    enable_web_search: bool = False
    enable_latex_compile: bool = True
    pdflatex_bin: str = "pdflatex"

    chroma_path: str = "./chroma_db"
    chroma_collection: str = "resume_chunks"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


settings = Settings()
