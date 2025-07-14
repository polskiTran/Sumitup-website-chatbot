from typing import Dict, List

from google.genai import types
from pydantic import EmailStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google
    google_gemini_genai_api_token: str
    google_gemini_genai_model: str = "gemini-2.5-flash-lite-preview-06-17"
    google_gemini_embedding_model: str = "gemini-embedding-exp-03-07"
    google_gemini_genai_model_backup: str = "gemini-2.5-flash"
    google_gemini_genai_cleanup_prompt_path: str = (
        "helpers/system_instructions/google_gemini_llm_cleanup_prompt.md"
    )
    google_gemini_embedding_config: types.EmbedContentConfig = types.EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=3072,
    )

    # Popular tech newsletters to monitor
    target_newsletters: List[Dict[str, str]] = [
        {"name": "TLDR", "email": "dan@tldrnewsletter.com"},
        {"name": "Tech Brew", "email": "crew@morningbrew.com"},
        {
            "name": "ByteByteGo",
            "email": "bytebytego@substack.com",
        },
        {"name": "Last Week In AI", "email": "lastweekinai+news@substack.com"},
        {"name": "Ben Lorica", "email": "gradientflow@substack.com"},  # gradientflow
        {"name": "ChinAI Newsletter", "email": "chinai@substack.com"},
    ]

    tldr_newsletters_group_names: list[str] = [
        "TLDR AI",
        "TLDR",
        "TLDR Web Dev",
        "TLDR Product",
        "TLDR Founders",
        "TLDR Data",
        "TLDR Fintech",
        "TLDR Marketing",
        "TLDR Design",
        "TLDR Crypto",
        "TLDR InfoSec",
        "TLDR DevOps",
    ]
    # Logger
    logger_level: str = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # TEST:
    # test newsletter name
    test_newsletter_name: str = "TLDR_AI_Jun_10"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create a global settings instance
settings = Settings()
