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
    pprint(web_search("NVIDIA current stock price?"))
    # extract url
    # pprint(
    #     url_extractor(
    #         "https://polskitran.github.io/Sumitup-quartz-dev/2025-07-15/tldr-web-dev-2025-07-15"
    #     )
    # )
