from tavily import TavilyClient

from config import settings

tavily_client = TavilyClient(api_key=settings.tavily_search_api_key)


def web_search(query: str):
    return tavily_client.search(query)


def url_extractor(url: str):
    return tavily_client.extract(url)


if __name__ == "__main__":
    from pprint import pprint

    # search web
    # pprint(web_search("NVIDIA current stock price?"))
    # extract url
    res = url_extractor(
        "https://substack.com/redirect/f23b48e2-9d22-48b5-891e-a91cbbc82fa8?j=eyJ1IjoiNXM4M296In0.tGNGSdtmlCx12UO5VTFY50vjzjDXKZsMTxKEYVZUdc8"
    )
    pprint(res)
    # pprint(res["results"][0]["raw_content"])
