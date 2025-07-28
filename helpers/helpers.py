import wave
from datetime import datetime, timedelta
from pprint import pprint
from typing import Any, Dict, List, Optional, Union


def is_empty(val):
    return val is None or val == ""


def build_and_filter(*conds):
    return {"$and": [c for c in conds if c]}


def build_dynamic_query(
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sender_name: Optional[Union[str, List[str]]] = None,
    additional_filters: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Build a MongoDB query with date filters, single/multiple sender_name, and other fields.

    Args:
        date (str, optional): Exact date ('YYYY-MM-DD').
        start_date (str, optional): Start date ('YYYY-MM-DD').
        end_date (str, optional): End date ('YYYY-MM-DD').
        sender_name (str | list, optional): Single sender or list of senders.
        additional_filters (dict, optional): Any other MongoDB filters.

    Returns:
        dict: MongoDB query dictionary.
    """

    query = {}
    if start_date == "None" or start_date == "":
        start_date = None
    if end_date == "None" or end_date == "":
        end_date = None
    if sender_name == "None" or sender_name == "":
        sender_name = None

    # Date filter
    if start_date and end_date:
        if start_date == end_date:  # exact date
            query["received_datetime"] = start_date
        else:  # date range
            start = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            end = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
            query["internal_date"] = {"$gte": start, "$lt": end}
    else:  # None date range
        end = int(datetime.now().timestamp() * 1000)
        start = int((datetime.now() - timedelta(days=5)).timestamp() * 1000)
        query["internal_date"] = {"$gte": start, "$lt": end}

    # Sender filter (single or multiple)
    if sender_name:
        if isinstance(sender_name, list):
            query["sender_name"] = {"$in": sender_name}
        else:
            query["sender_name"] = sender_name

    # Additional filters
    if additional_filters:
        query.update(additional_filters)

    pprint(query)
    return query


# Set up the wave file to save the output:
def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


if __name__ == "__main__":
    print(
        build_dynamic_query(
            start_date="2025-07-10",
            end_date="2025-07-14",
            sender_name=["TLDR AI", "Ben Lorica"],
        )
    )
