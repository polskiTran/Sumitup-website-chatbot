import sys
from datetime import datetime
from urllib.parse import urlparse

from flow import create_support_bot_flow


def get_domain_from_url(url):
    """Extract domain from URL for allowed_domains"""
    parsed = urlparse(url)
    return parsed.netloc.lower()


def main():
    # Get command line arguments
    if len(sys.argv) < 3:
        print(
            "Usage: python main.py <start_url1> [start_url2] ... '<initial_question>' [instruction]"
        )
        print(
            "Example: python main.py https://example.com 'What is your return policy?'"
        )
        sys.exit(1)

    # Argument parsing logic...
    if len(sys.argv) >= 4 and not sys.argv[-1].startswith(("http://", "https://")):
        start_urls = sys.argv[1:-2]
        initial_question = sys.argv[-2]
        instruction = sys.argv[-1]
    else:
        start_urls = sys.argv[1:-1]
        initial_question = sys.argv[-1]
        # instruction = "Provide helpful and accurate answers based on the website content."
        current_date = datetime.now().strftime("%Y-%m-%d")
        # add current date to instruction
        instruction = (
            "Current date: "
            + current_date
            + "\n"
            + (open("instruction.md", "r", encoding="utf-8").read())
        )

    # Validate URLs
    for url in start_urls:
        if not url.startswith(("http://", "https://")):
            print(
                f"Error: '{url}' is not a valid URL. URLs must start with http:// or https://"
            )
            sys.exit(1)

    domains = [d for d in (get_domain_from_url(url) for url in start_urls) if d]

    # Initialize shared store. This state will be preserved across conversations.
    shared = {
        "conversation_history": [],
        "instruction": instruction,
        "allowed_domains": list(set(domains)),
        "max_iterations": 5,
        "max_pages": 100,
        "content_max_chars": 100000,
        "max_urls_per_iteration": 10,
        # URL tracking state
        "all_discovered_urls": start_urls.copy(),
        "visited_urls": set(),
        "url_content": {},
        "url_graph": {},
        # Per-run state (will be set in the loop)
        "user_question": "",
        "urls_to_process": [],
        "current_iteration": 0,
        "final_answer": None,
    }

    support_bot_flow = create_support_bot_flow()

    # --- Conversational Loop ---
    is_first_run = True
    while True:
        if is_first_run:
            shared["user_question"] = initial_question
            # For the first run, process the starting URLs
            shared["urls_to_process"] = list(range(len(start_urls)))
            is_first_run = False
        else:
            try:
                follow_up_question = input(
                    "\nAsk a follow-up question (or press Ctrl+C to exit): "
                )
                if not follow_up_question.strip():
                    continue
                shared["user_question"] = follow_up_question
                # For subsequent runs, the agent must decide to explore
                shared["urls_to_process"] = []
            except (EOFError, KeyboardInterrupt):
                print("\n\nExiting.")
                break

        print(f"\n=== Answering: '{shared['user_question']}' ===")
        print("=" * 50)

        # Reset per-run state
        shared["current_iteration"] = 0
        shared["final_answer"] = None

        support_bot_flow.run(shared)

        print("\n" + "=" * 50)
        if shared["final_answer"]:
            print("Final Answer:")
            print(shared["final_answer"])
            # Add to conversation history
            shared["conversation_history"].append(
                {"user": shared["user_question"], "bot": shared["final_answer"]}
            )
        else:
            print("No final answer was generated.")

        print(f"\nExploration Summary:")
        print(f"- Visited {len(shared['visited_urls'])} pages")
        print(f"- Discovered {len(shared['all_discovered_urls'])} total URLs")


if __name__ == "__main__":
    main()
