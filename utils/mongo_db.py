import logging
from datetime import datetime

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
# MongoDB tool calls
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


# ------------------------------
# MongoDB chat session saving/loading
# ------------------------------
def create_chat_session(chat_session_shared_store: dict):
    """
    Create a chat session in mongodb
    Args:
        chat_session_shared_store (dict): The chat session shared store to create
    Returns:
        str: The session ID of the created session
    """
    # connect to mongo db
    client = MongoClient(settings.mongodb_uri)
    collection = client[settings.mongodb_database][
        settings.mongodb_chat_session_collection_name
    ]
    # exclude progress queue from chat session shared store
    chat_session_shared_store_copy = chat_session_shared_store.copy()
    chat_session_shared_store_copy.pop("progress_queue", None)

    # create session ID with microseconds for uniqueness
    session_id = datetime.now().strftime("%Y/%m/%d-%H:%M:%S.%f")[
        :-3
    ]  # Remove last 3 digits of microseconds

    # create chat session
    chat_session_doc = {
        "chat_session_id": session_id,
        "chat_session_shared_store": chat_session_shared_store_copy,
        "chat_session_conversation_history": chat_session_shared_store_copy.get(
            "conversation_history", []
        ),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # save chat session
    try:
        collection.insert_one(chat_session_doc)
        logger.info(f"Created chat session: {session_id}")
        return session_id
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        return None
    finally:
        # disconnect from mongo db
        client.close()


def save_chat_session(chat_session_id: str, chat_session_shared_store: dict):
    """
    Save a chat session to mongodb
    Args:
        chat_session_id (str): The id of the chat session
        chat_session_shared_store (dict): The chat session shared store to save
    """
    # connect to mongo db
    client = MongoClient(settings.mongodb_uri)
    collection = client[settings.mongodb_database][
        settings.mongodb_chat_session_collection_name
    ]

    # exclude progress queue from chat session shared store
    chat_session_shared_store_copy = chat_session_shared_store.copy()
    chat_session_shared_store_copy.pop("progress_queue", None)

    chat_session_doc = {
        "chat_session_shared_store": chat_session_shared_store_copy,
        "chat_session_conversation_history": chat_session_shared_store_copy.get(
            "conversation_history", []
        ),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    # save chat session
    try:
        collection.update_one(
            {"chat_session_id": chat_session_id},
            {"$set": chat_session_doc},
        )
        logger.info(f"Saved chat session: {chat_session_id}")
    except Exception as e:
        logger.error(f"Error saving chat session: {e}")

    # disconnect from mongo db
    client.close()


def load_chat_session(chat_session_id: str):
    """
    Load a chat session from mongodb
    Args:
        chat_session_id (str): The id of the chat session
    """
    # connect to mongo db
    client = MongoClient(settings.mongodb_uri)
    collection = client[settings.mongodb_database][
        settings.mongodb_chat_session_collection_name
    ]

    # get chat session
    try:
        chat_session = collection.find_one({"chat_session_id": chat_session_id})
        if not chat_session:
            logger.error(f"Chat session not found: {chat_session_id}")
            return None
        logger.info(f"Loaded chat session: {chat_session_id}")
    except Exception as e:
        logger.error(f"Error loading chat session: {e}")
        return None

    # disconnect from mongo db
    client.close()
    return chat_session


def get_all_chat_sessions_ids():
    """
    Get all chat session ids from mongodb
    """
    # connect to mongo db
    client = MongoClient(settings.mongodb_uri)
    collection = client[settings.mongodb_database][
        settings.mongodb_chat_session_collection_name
    ]

    # get all chat session ids
    try:
        chat_session_ids = collection.distinct("chat_session_id")
        if not chat_session_ids:
            logger.error("No chat sessions found")
            return None
        logger.info(f"Loaded all chat session ids: {chat_session_ids}")
    except Exception as e:
        logger.error(f"Error loading all chat session ids: {e}")
        return None

    # disconnect from mongo db
    client.close()

    return chat_session_ids


def delete_chat_session(chat_session_id: str):
    """
    Delete a chat session from mongodb
    Args:
        chat_session_id (str): The id of the chat session
    """
    # connect to mongo db
    client = MongoClient(settings.mongodb_uri)
    collection = client[settings.mongodb_database][
        settings.mongodb_chat_session_collection_name
    ]

    # delete chat session
    try:
        collection.delete_one({"chat_session_id": chat_session_id})
        logger.info(f"Deleted chat session: {chat_session_id}")
    except Exception as e:
        logger.error(f"Error deleting chat session: {e}")

    # disconnect from mongo db
    client.close()


if __name__ == "__main__":
    import time
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

    def test_chat_session():
        # test chat session
        chat_session_shared_store = {
            "conversation_history": [
                {"user": "Hello, how are you?"},
                {"bot": "I'm good, thank you!"},
                {"user": "What is the weather in Tokyo?"},
                {"bot": "It's sunny!"},
            ],
            "user_question": "What is the weather in Tokyo?",
        }
        create_chat_session(chat_session_shared_store)
        time.sleep(5)
        chat_session_ids = get_all_chat_sessions_ids()
        chat_session = load_chat_session(chat_session_ids[0])
        chat_session_shared_store["current_knowledge_base"] = "Tokyo is sunny right now"
        save_chat_session(chat_session_ids[0], chat_session_shared_store)
        pprint(chat_session)

    # main()
    test_chat_session()
