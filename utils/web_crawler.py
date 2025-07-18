import asyncio

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig


def crawl_webpage(url, delay_after_load=2):
    """
    Crawl webpage to extract markdown content and all links using crawl4ai.
    This is a synchronous wrapper around an async implementation.
    """

    async def _async_crawl():
        # crawl4ai uses playwright, which may need to be installed via:
        # pip install playwright
        # python -m playwright install

        # Configure the crawler to wait for network idle, and then add a fixed
        # delay to allow for JavaScript rendering.
        config = CrawlerRunConfig(
            wait_until="load",
            delay_before_return_html=delay_after_load,
        )

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url, config=config)

            if not result or not result.success:
                raise Exception(
                    f"Failed to crawl {url}. Error: {result.error_message if result else 'Unknown error'}"
                )

            # The main content is in result.markdown
            clean_text = result.markdown

            # Links are in result.links, categorized. Extract just the href.
            all_link_objects = result.links.get("internal", []) + result.links.get(
                "external", []
            )
            links = [link.get("href") for link in all_link_objects if link.get("href")]

            return clean_text, links

    # This runs the async function and returns the result.
    return asyncio.run(_async_crawl())


if __name__ == "__main__":
    test_url = "https://github.com/The-Pocket/PocketFlow/blob/main/.cursorrules"
    test_url2 = "https://substack.com/redirect/2ae98519-a1b3-41b8-bbd9-18f5f6ab9d1d?j=eyJ1IjoiNXM4M296In0.tGNGSdtmlCx12UO5VTFY50vjzjDXKZsMTxKEYVZUdc8"

    content, links = crawl_webpage(test_url2)

    if content:
        print(f"Content length: {len(content)}")
        print(
            f"Content preview: {content[:100000]}{'...' if len(content) > 100000 else ''}"
        )

    if links:
        print(f"\nFound {len(links)} unique links:")
        for link in links[:5]:
            print(f"  {link}")

        if len(links) > 5:
            print(f"  ... and {len(links) - 5} more")
