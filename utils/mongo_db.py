import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from config import settings
from utils.embedding import embedding

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
# MongoDB
# ------------------------------
class Database:
    client: Optional[AsyncIOMotorClient] = None


db = Database()


async def connect_to_mongo():
    """Create database connection"""
    try:
        db.client = AsyncIOMotorClient(
            settings.mongodb_uri,
            maxPoolSize=10,
            minPoolSize=10,
        )
        # logger.info("(*) Connected to MongoDB --------------------------------\n")
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}\n")
        raise e


async def disconnect_from_mongo():
    """Close database connection"""
    try:
        if db.client:
            db.client.close()
            # logger.info(
            #     "(*) Disconnected from MongoDB --------------------------------\n"
            # )
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}\n")
        raise e


async def mongodb_vector_search(
    query: str, limit: int = 5, pre_filter_query: dict = {}
):
    """
    Search for newsletters in mongodb using vector search
    Args:
        query (str): The query to search for
        limit (int): The number of results to return
        pre_filter_query (dict): The pre filter query to apply to the search
    Returns:
        list[dict]: The list of results
    """

    # connect to mongo db
    await connect_to_mongo()
    collection = db.client[settings.mongodb_database][settings.mongodb_collection_name]

    logger.info(f"Pre filter query: {pre_filter_query}")

    # vector search
    query_vector = embedding(query)
    cursor = collection.aggregate(
        [
            {
                "$vectorSearch": {
                    "queryVector": query_vector,
                    "path": "cleaned_md_embedding",
                    "numCandidates": 100,
                    "limit": limit,
                    "index": "vector_index",
                    "filter": pre_filter_query,
                }
            }
        ]
    )

    # clean results
    cleaned_results = []
    async for doc in cursor:
        cleaned_results.append(
            {
                "id": doc["_id"],
                "sender_name": doc["sender_name"],
                "sender_email": doc["sender_email"],
                "subject": doc["subject"],
                "received_datetime": doc["received_datetime"],
                "cleaned_md": doc["cleaned_md"],
            }
        )
    # disconnect from mongo db
    await disconnect_from_mongo()
    return cleaned_results


if __name__ == "__main__":
    import asyncio
    from pprint import pprint

    async def main():
        pprint(await mongodb_vector_search("Windsurf acquisition"))

    asyncio.run(main())
