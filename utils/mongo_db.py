import logging

from pymongo import MongoClient

from config import settings
from helpers.helpers import build_dynamic_query
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
def mongodb_vector_search(query: str, limit: int = 50, pre_filter_query: dict = {}):
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
    client = MongoClient(
        settings.mongodb_uri,
    )
    collection = client[settings.mongodb_database][settings.mongodb_collection_name]

    logger.info(f"Pre filter query in vector search: {pre_filter_query}")

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
    for doc in cursor:
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
    client.close()
    return cleaned_results


def mongodb_query_search(query: dict, limit: int = 50):
    """
    Search for newsletters in mongodb using query search
    Args:
        query (dict): The query to search for
        limit (int): The number of results to return
    Returns:
        list[dict]: The list of results
    """
    # connect to mongo db
    client = MongoClient(
        settings.mongodb_uri,
    )
    collection = client[settings.mongodb_database][settings.mongodb_collection_name]

    logger.info(f"Pre filter query in query search: {query}")

    # query search
    cursor = collection.find(query).limit(limit)

    # clean results
    cleaned_results = []
    for doc in cursor:
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
    client.close()
    return cleaned_results


if __name__ == "__main__":
    from datetime import datetime
    from pprint import pprint

    def main():
        # test date range filter
        date1 = "2025-07-10"
        date2 = "2025-07-13"
        # date3 = "2025-07-12"
        date_timestamp1 = int(datetime.strptime(date1, "%Y-%m-%d").timestamp() * 1000)
        date_timestamp2 = int(datetime.strptime(date2, "%Y-%m-%d").timestamp() * 1000)

        # build query
        pre_filter_query = build_dynamic_query(
            start_date="2025-07-10",
            end_date="2025-07-14",
            sender_name=["TLDR AI", "Ben Lorica"],
        )
        # run test vector search
        print("(*) Running test vector search...")
        pprint(
            mongodb_vector_search(
                "Windsurf acquisition", pre_filter_query=pre_filter_query, limit=10
            )
        )

        # run test query search
        print("\n\n(*) Running test query search...")
        pprint(mongodb_query_search(pre_filter_query, limit=30))

    main()
