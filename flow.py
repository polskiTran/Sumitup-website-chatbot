from pocketflow import Flow, Node

from config import settings
from nodes import (
    AnswerDatabaseSearch,
    AnswerQuestion,
    DatabaseAgent,
    DecideAction,
    ReadCurrentPage,
    ReadThisLink,
    SearchDatabase,
    SearchWeb,
)
from tracing import TracingConfig, trace_flow
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

# ------------------------------
# Tracing
# ------------------------------
# config = TracingConfig.from_env()
config = TracingConfig(
    langfuse_secret_key=settings.langfuse_secret_key,
    langfuse_public_key=settings.langfuse_public_key,
    langfuse_host=settings.langfuse_host,
    debug=settings.pocketflow_tracing_debug,
    # trace_outputs=False,
    # trace_errors=False,
)


# ------------------------------
# Flow
# ------------------------------
@trace_flow(flow_name="SumitupSupportBot", config=config)
class SupportBotFlow(Flow):
    def __init__(self, start_node: Node):
        super().__init__(start=start_node)


def create_support_bot_flow():
    """Create and return the Sumitup AI support assistant flow."""
    # Create nodes
    search_database_node = SearchDatabase(max_retries=3, wait=10)
    answer_question_node = AnswerQuestion(max_retries=3, wait=10)
    decide_action_node = DecideAction(max_retries=3, wait=3)
    web_search_node = SearchWeb(max_retries=3, wait=10)
    current_page_context_node = ReadCurrentPage(max_retries=3, wait=10)
    read_this_link_node = ReadThisLink(max_retries=3, wait=10)
    database_agent_node = DatabaseAgent(max_retries=3, wait=10)
    answer_database_search_node = AnswerDatabaseSearch(max_retries=3, wait=10)

    # Connect nodes with transitions
    decide_action_node - "search-database" >> database_agent_node
    decide_action_node - "search-web" >> web_search_node
    decide_action_node - "read-this-link" >> read_this_link_node
    decide_action_node - "read-current-page" >> current_page_context_node
    decide_action_node - "answer" >> answer_question_node

    database_agent_node - "search-database" >> search_database_node
    database_agent_node - "answer-search-database" >> answer_database_search_node

    search_database_node - "decide" >> database_agent_node
    web_search_node - "decide" >> decide_action_node
    read_this_link_node - "decide" >> decide_action_node
    current_page_context_node - "decide" >> decide_action_node
    # visualize the flow
    # print(build_mermaid(Flow(start=decide_action_node)))

    # Create flow starting with decide_action_node
    # return Flow(start=current_page_context_node)
    return SupportBotFlow(start_node=decide_action_node)


if __name__ == "__main__":
    support_bot_flow = create_support_bot_flow()
    print(build_mermaid(support_bot_flow))
