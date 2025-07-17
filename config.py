import asyncio
from datetime import datetime
from typing import Dict, List

from google.genai import types
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Gemini
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

    # ChromaDB
    chromadb_api_key: str
    chromadb_tenant: str
    chromadb_database: str = "sumitup-dev"
    chromadb_collection_name: str = "newsletters"

    # MongoDB
    mongodb_uri: str
    mongodb_database: str = "sumitup-dev"
    mongodb_collection_name: str = "newsletters"

    # Tavily search
    tavily_search_api_key: str

    # Langfuse
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_project: str = "sumitup"
    pocketflow_tracing_debug: bool

    # system instructions
    system_instructions_path: str = "prompts/instruction.md"
    today_date: str = datetime.now().strftime("%Y-%m-%d")
    system_instructions: str = (
        f"\nToday's date: {today_date}\n" + open(system_instructions_path, "r").read()
    )

    # shared store
    shared_store: Dict[str, any] = {
        "websocket": "",
        "instruction": system_instructions,
        "conversation_history": [],
        "user_question": "",
        "search_query": "",
        "knowledge_base": "",
        "progress_queue": asyncio.Queue(),
        "current_url": "",
        "current_page_context": {},
        "final_answer": "",
    }

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
    logger_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # TEST:
    # test newsletter name
    test_newsletter_name: str = "TLDR_AI_Jun_10"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create a global settings instance
settings = Settings()
