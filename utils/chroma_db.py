from datetime import datetime

import chromadb

from config import settings


def chromadb_vector_search(query: str, limit: int = 10, filter: dict = None):
    """
    Search for newsletters in chromadb using vector search
    Args:
        query (str): The query to search for
        limit (int): The number of results to return
        filter (dict): The filter to apply to the search
    Returns:
        list[dict]: The list of results
    """
    # connect to chromadb
    client = chromadb.CloudClient(
        api_key=settings.chromadb_api_key,
        tenant=settings.chromadb_tenant,
        database=settings.chromadb_database,
    )
    try:
        collection = client.get_collection(name=settings.chromadb_collection_name)
    except Exception as e:
        print(f"Error getting collection: {e}.")
    results = collection.query(
        query_texts=[query],
        where=filter,
        n_results=limit,
    )
    response = []
    for metadata, document in zip(results["metadatas"], results["documents"]):
        response.append({"metadata": metadata, "document": document})
    return response


def chromadb_query_search(query: dict = {}, limit: int = 10):
    """
    Search for newsletters in chromadb using query search
    Args:
        query (str): The query to search for
        limit (int): The number of results to return
    Returns:
        list[dict]: The list of results
    """
    # connect to chromadb
    client = chromadb.CloudClient(
        api_key=settings.chromadb_api_key,
        tenant=settings.chromadb_tenant,
        database=settings.chromadb_database,
    )
    try:
        collection = client.get_collection(name=settings.chromadb_collection_name)
    except Exception as e:
        print(f"Error getting collection: {e}.")
    results = collection.get(where=query)

    # construct result with metadatas and documents
    response = []
    for metadata, document in zip(results["metadatas"], results["documents"]):
        response.append({"metadata": metadata, "document": document})
    return results


if __name__ == "__main__":
    import asyncio
    from pprint import pprint

    # test data
    date1 = "2025-07-10"
    date2 = "2025-07-13"
    date3 = "2025-07-15"
    date_timestamp1 = int(datetime.strptime(date1, "%Y-%m-%d").timestamp() * 1000)
    date_timestamp2 = int(datetime.strptime(date2, "%Y-%m-%d").timestamp() * 1000)

    # query
    query = "Windsurf acquisition"
    limit = 5
    # pre filter query
    # pre_filter_query = {
    #     "internal_date": {
    #         "$gte": date_timestamp1,
    #         "$lt": date_timestamp2,
    #     }
    # }
    pre_filter_query = {"received_datetime": date3}
    # chroma_filter = {
    #     "date_timestamp": {
    #         "$gte": int(datetime.strptime(date1, "%Y-%m-%d").timestamp())
    #     }
    # }
    # chroma_filter = {
    #     "$and": [
    #         {"date": "2025-07-06"},
    #         {"date": "2025-07-07"},
    #         {"date": "2025-07-08"},
    #         {"date": "2025-07-09"},
    #         {"date": "2025-07-10"},
    #         {"date": "2025-07-11"},
    #         {"date": "2025-07-12"},
    #     ]
    # }
    chroma_filter = {"$and": [{"date": date3}, {"sender_name": "TLDR AI"}]}
    # chroma_filter = {"date": date3}

    async def run():
        print("---------------------------------------------------")
        print("---------------------------------------------------")
        print("chromadb_vector_search")
        pprint(chromadb_vector_search(query, limit, chroma_filter))
        # print("---------------------------------------------------")
        # print("---------------------------------------------------")
        # print("chromadb_query_search")
        # pprint(await chromadb_query_search(chroma_filter, limit))

    asyncio.run(run())
