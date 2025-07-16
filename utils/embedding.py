import logging
import time

from google import genai

from config import settings

# ------------------------------
# Logger
# ------------------------------
# capture module name and set level
logger = logging.getLogger(__name__)
logger.setLevel(settings.logger_level)

# Create console handler (stream logger to console) and set level to debug
console_handler = logging.StreamHandler()
console_handler.setLevel(settings.logger_level)  # Capture all levels

# Create formatter and add it to the handler
formatter = logging.Formatter(
    "\n🪵 [%(asctime)s] %(levelname)s in [%(module)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


console_handler.setFormatter(formatter)

# Add the handler to the logger if not already added
if not logger.hasHandlers():
    logger.addHandler(console_handler)


# ------------------------------
# Embedding
# ------------------------------
def embedding(query: str) -> list[float]:
    """Embed the query using the Gemini embedding model.

    Args:
        query (str): The query to embed
    Returns:
        list[float]: The embedded query as a list of floats
    """
    max_attempts = 10
    backoff = 1

    # connect to google gemini
    client = genai.Client(api_key=settings.google_gemini_genai_api_token)

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info("Embedding query...")
            result = client.models.embed_content(
                model=settings.google_gemini_embedding_model,
                contents=query,
                config=settings.google_gemini_embedding_config,
            )
            logger.info(
                f"Embedding done! Embedding length: {len(result.embeddings[0].values)}"
            )
            return result.embeddings[0].values
        except Exception as e:
            err_str = str(e).lower()
            if (
                "resource_exhausted" in err_str
                or "429" in err_str
                or "rate limit" in err_str
            ):
                logger.warning(
                    f"Embedding attempt {attempt} failed with RESOURCE_EXHAUSTED/429: {e}. Retrying in {backoff} seconds..."
                )
                if attempt == max_attempts:
                    logger.error(
                        f"Embedding failed after {max_attempts} attempts due to RESOURCE_EXHAUSTED/429."
                    )
                    raise Exception(f"Embedding failed after retries: {str(e)}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)  # Cap at 60s
                continue
            logger.error(f"Unexpected error generating embedding: {e}")
            raise Exception(f"Embedding failed: {str(e)}")


if __name__ == "__main__":
    query = "What is the weather in Tokyo?"
    embedding = embedding(query)
    print(embedding)
