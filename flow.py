from pocketflow import Flow

from nodes import (
    AnswerQuestion,
    CurrentPageContext,
    DecideAction,
    SearchDatabase,
    WebSearch,
)
from utils.visualize import build_mermaid

# def create_support_bot_flow():
#     """Create and return an AI support assistant flow."""
#     # Create nodes
#     crawl_node = CrawlAndExtract(max_retries=3, wait=10)
#     agent_node = AgentDecision(max_retries=3, wait=10)
#     draft_answer_node = DraftAnswer(max_retries=3, wait=10)

#     # Connect nodes with transitions
#     crawl_node >> agent_node
#     agent_node - "explore" >> crawl_node  # Loop back for more exploration
#     (
#         agent_node - "answer" >> draft_answer_node
#     )  # Go to answer generation (includes refusals)

#     # visualize the flow
#     print(build_mermaid(Flow(start=crawl_node)))

#     # Create flow starting with crawl node
#     return Flow(start=crawl_node)


def create_support_bot_flow():
    """Create and return the Sumitup AI support assistant flow."""
    # Create nodes
    search_database_node = SearchDatabase(max_retries=3, wait=10)
    answer_question_node = AnswerQuestion(max_retries=3, wait=10)
    decide_action_node = DecideAction(max_retries=3, wait=10)
    web_search_node = WebSearch(max_retries=3, wait=10)
    current_page_context_node = CurrentPageContext(max_retries=3, wait=10)

    # Connect nodes with transitions
    current_page_context_node - "decide" >> decide_action_node
    decide_action_node - "database-search" >> search_database_node
    decide_action_node - "web-search" >> web_search_node
    decide_action_node - "answer" >> answer_question_node
    search_database_node - "decide" >> decide_action_node
    web_search_node - "decide" >> decide_action_node

    # visualize the flow
    # print(build_mermaid(Flow(start=decide_action_node)))

    # Create flow starting with decide_action_node
    return Flow(start=current_page_context_node)


support_bot_flow = create_support_bot_flow()

if __name__ == "__main__":
    print(build_mermaid(support_bot_flow))
