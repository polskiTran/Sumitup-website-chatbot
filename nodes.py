import logging
import pprint
import time
from datetime import datetime

import yaml
from pocketflow import Node

from config import settings
from helpers.helpers import build_dynamic_query, is_empty
from utils.call_llm import call_llm
from utils.mongo_db import mongodb_query_search, mongodb_vector_search
from utils.web_search import url_extractor, web_search

# ------------------------------
# Logger
# ------------------------------
# capture module name and set level
logger = logging.getLogger(__name__)
logger.setLevel(settings.logger_level)

# Create console handler (stream logger to console) and set level to debug
console_handler = logging.StreamHandler()
console_handler.setLevel(settings.logger_level)  # Capture all levels

# Create formatter and add it to the handler. Add function name to the message and class name to the message
formatter = logging.Formatter(
    "\n🪵 [%(asctime)s] %(levelname)s in [%(module)s : %(funcName)s : ]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console_handler.setFormatter(formatter)
# Add the handler to the logger if not already added
if not logger.hasHandlers():
    logger.addHandler(console_handler)

# ==============================================================
# AGENTS
# ==============================================================


# ------------------------------
# DecideAction Agent
# ------------------------------
class DecideAction(Node):
    def prep(self, shared):
        """Prepare the context and question for the decision-making process."""
        # Get the current context - check if this is truly the first iteration
        current_knowledge_base = shared.get("current_knowledge_base", "")
        is_first_iteration = not current_knowledge_base or (
            isinstance(current_knowledge_base, str)
            and current_knowledge_base.strip() == ""
        )

        if is_first_iteration:
            current_knowledge_base = (
                "FIRST ITERATION: No previous research has been conducted yet."
            )
        else:
            # Check if the knowledge base contains error messages that might confuse the agent
            if isinstance(current_knowledge_base, str) and (
                "NOT_FOUND" in current_knowledge_base
                or "No documents found" in current_knowledge_base
            ):
                current_knowledge_base = (
                    "FIRST ITERATION: No previous research has been conducted yet."
                )

        # Get the question from the shared store
        user_question = shared["user_question"]
        instruction = shared["instruction"]
        conversation_history = shared.get("conversation_history", [])
        current_url = shared.get("current_url", "")
        current_page_context = shared.get("current_page_context", {}) or ""
        read_this_link = shared.get("read_this_link", "")

        # Handle agent decision context
        agent_decision = shared.get("agent_decision", "")
        if not agent_decision or (
            isinstance(agent_decision, str) and agent_decision.strip() == ""
        ):
            agent_decision = (
                "FIRST ITERATION: This is the initial decision for this question."
            )

        # log the current shared store
        logger.debug(
            "Current shared store in DecideAction: \n%s", pprint.pformat(shared)
        )
        # Return both for the exec step
        return {
            "user_question": user_question,
            "current_knowledge_base": current_knowledge_base,
            "instruction": instruction,
            "conversation_history": conversation_history,
            "current_url": current_url,
            "current_page_context": current_page_context,
            "read_this_link": read_this_link,
            "agent_decision": agent_decision,
            "is_first_iteration": is_first_iteration,
        }

    def exec(self, inputs):
        """Call the LLM to decide whether to search or answer."""
        user_question = inputs["user_question"]
        current_knowledge_base = inputs["current_knowledge_base"]
        instruction = inputs["instruction"]
        conversation_history = inputs["conversation_history"]
        current_url = inputs["current_url"]
        current_page_context = str({current_url: inputs["current_page_context"]})
        is_first_iteration = inputs["is_first_iteration"]

        # Format conversation history for the prompt
        history_str = ""
        if conversation_history:
            history_str += "CONVERSATION HISTORY:\n"
            for turn in conversation_history:
                history_str += f"User: {turn.get('user', 'No question yet')}\nBot: {turn.get('bot', 'No answer yet')}\n"
            history_str += "\n"

        logger.info("🤔 Agent deciding what to do next...")

        # Create a prompt to help the LLM decide what to do next with proper yaml formatting
        prompt = f"""
### CONTEXT
You are a research assistant on Sumitup - a digital tech newsletter database. 
You are given a user question and a context of what is available to you. Reflect on the user question and the context to decide what to do next - using tools to get more information or answer the question.
Always default to searching the database if you are unsure if the current knowledge is enough to satisfy the user's newsletters inquiry.
IMPORTANT: You are not limited to the current knowledge base: If the current knowledge base does not have enough information to answer the question, you should use the tools to get more information.

{"**FIRST ITERATION: This is the initial search for this question.**" if is_first_iteration else ""}

Guidelines: {instruction}
Question: {user_question}
Current Newsletters Page: {current_page_context}
Current Knowledge Base: {current_knowledge_base}

### ACTION SPACE
[1] search-database
  Description: Look up more information on the newsletters database (RECOMMENDED for newsletter-related queries)
  Parameters:
    - search-database-query (str): What to search for in the database

[2] search-web
  Description: Look up more information on the internet (use this if user need recent information and if the database search doesn't provide the information or if the user specify to use web search)
  Parameters:
    - search-web-query (str): What to search for on the internet

[3] read-this-link
  Description: Get the content from a user provided specific link (Must pick if user specifies to read a link). If content of link is already in the current knowledge base, DO NOT read the link again.
  Parameters:
    - read-this-link-query (str): The url of the link to read the content from

[4] read-current-page
  Description: Get the content from the current newsletter page (Must pick if user asks about the current newsletter page content. e.g. "Overview of the current newsletter page?")
  Parameters:
    - read-current-page-url (str): The url of the current page

[5] answer
  Description: Answer the question if current knowledge base has enough information to answer the question. If not, you should use the tools to get more information.
  Parameters:
    - answer (str): The answer to the question

### NEXT ACTION
Decide the next action based on the context and available actions.
Return your response in this format:

```yaml
thinking:  |
    <your step-by-step reasoning process>
action: <search-database | search-web | read-this-link | read-current-page | answer>
reason: <why you chose this action>
search-database-query: <specific search query if action is search-database>
search-web-query: <specific search query if action is search-web>
read-this-link-query: <specific url if action is read-this-link>
read-current-page-url: <specific url if action is read-current-page>
```
IMPORTANT: Make sure to:
1. Use proper indentation (4 spaces) for all multi-line fields
2. Use the | character for multi-line text fields
3. Keep single-line fields without the | character
"""

        # Call the LLM to make a decision
        response = call_llm(prompt)
        # debug print
        print("\n\n--------------------------------")
        print("(*) DecideAction Response:")
        print(response)
        print("--------------------------------\n\n")

        # Parse the response to get the decision
        try:
            if "```yaml" in response:
                yaml_str = response.split("```yaml")[1].split("```")[0].strip()
            elif "```" in response:
                yaml_str = response.split("```")[1].split("```")[0].strip()
            else:
                yaml_str = response.strip()

            # Clean up common YAML issues
            yaml_str = yaml_str.replace('"', "").replace("'", "")  # Remove quotes
            yaml_str = yaml_str.replace("...", "")  # Remove ellipsis

            decision = yaml.safe_load(yaml_str)

            # Validate the decision structure
            if not isinstance(decision, dict):
                raise ValueError("Decision must be a dictionary")

            required_fields = ["action"]  # "reason"
            for field in required_fields:
                if field not in decision:
                    raise ValueError(f"Missing required field: {field}")

            return decision

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.error(f"Raw response: {response}")
            raise e

    def exec_fallback(self, prep_res, exc):
        """Fallback when decision making fails."""
        logger.error(f"Error making decision: {exc}")
        return {
            "action": "answer",
            "reason": "Fallback: Defaulting to answer due to error",
            "answer": "I'm sorry, I encountered an error while making a decision. Please try again or rephrase your question.",
        }

    def post(self, shared, prep_res, exec_res):
        """Save the decision and determine the next step in the flow."""
        # save the decision
        shared["agent_decision"] = exec_res
        if exec_res["action"] == "search-database":
            # save the search query
            shared["search_query"] = exec_res["search-database-query"]
            logger.info(
                f"🔍 Agent decided to search database: {exec_res['search-database-query']}"
            )
            return "search-database"  # need to search more
        elif exec_res["action"] == "search-web":
            # save the search query
            shared["search_query"] = exec_res["search-web-query"]
            logger.info(
                f"🔍 Agent decided to search web: {exec_res['search-web-query']}"
            )
            return "search-web"  # need to search more
        elif exec_res["action"] == "read-this-link":
            # save the link
            shared["read_this_link"] = exec_res["read-this-link-query"]
            logger.info(
                f"🔍 Agent decided to read this link: {exec_res['read-this-link-query']}"
            )
            return "read-this-link"  # need to read more
        elif exec_res["action"] == "read-current-page":
            # save the url
            shared["current_url"] = exec_res["read-current-page-url"]
            logger.info(
                f"🔍 Agent decided to get the current page context: {exec_res['read-current-page-url']}"
            )
            return "read-current-page"  # need to get more
        else:
            logger.info("💡 Agent decided to answer the question")
            # update progress queue
            if "progress_queue" in shared:
                shared["progress_queue"].put_nowait(
                    "Gather enough information to answer the question..."
                )
            return "answer"  # got enough information to answer the question


# ------------------------------
# DatabaseAgent
# ------------------------------
class DatabaseAgent(Node):
    def prep(self, shared):
        """Get the database search query from the shared store."""
        # Check if this is the first iteration
        time.sleep(2)
        # add to progress queue
        if "progress_queue" in shared:
            shared["progress_queue"].put_nowait(
                "DatabaseAgent: Deciding the next action..."
            )
        logger.info("🤔 DatabaseAgent: Deciding the next action...")
        current_knowledge_base = shared.get("current_knowledge_base", "")
        is_first_iteration = not current_knowledge_base or (
            isinstance(current_knowledge_base, str)
            and current_knowledge_base.strip() == ""
        )

        if is_first_iteration:
            current_knowledge_base = (
                "FIRST ITERATION: No previous research has been conducted yet."
            )
        # else:
        #     # Check if the knowledge base contains error messages that might confuse the agent
        #     if isinstance(current_knowledge_base, str) and (
        #         "NOT_FOUND" in current_knowledge_base
        #         or "No documents found" in current_knowledge_base
        #     ):
        #         current_knowledge_base = (
        #             "FIRST ITERATION: No previous research has been conducted yet."
        #         )

        database_agent_decision = shared.get("database_agent_decision", "")
        if not database_agent_decision or (
            isinstance(database_agent_decision, str)
            and database_agent_decision.strip() == ""
        ):
            database_agent_decision = "FIRST ITERATION: This is the initial database search for this question."

        return {
            "search_query": shared["search_query"],
            "current_knowledge_base": current_knowledge_base,
            "database_agent_decision": database_agent_decision,
            "is_first_iteration": is_first_iteration,
            "user_question": shared["user_question"],
        }

    def exec(self, inputs):
        """Call the LLM to generate a search query for the database."""
        search_query = inputs["search_query"]
        current_knowledge_base = inputs["current_knowledge_base"]
        user_question = inputs["user_question"]
        database_agent_decision = inputs["database_agent_decision"]
        is_first_iteration = inputs["is_first_iteration"]
        current_date = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""
### CONTEXT
You are a research assistant on Sumitup - a digital tech newsletter database. 
You are given a user question and a context of what is available to you. Reflect on the user question and the context to decide what to do next - using tools to get more information or answer the question.
IMPORTANT: You are not limited to the current knowledge base: If the current knowledge base does not have enough information to answer the question, you should use the tools to get more information.
Database Search Query: {search_query}
User Question: {user_question}
Previous search results: {current_knowledge_base}
Current Date: {current_date}
Previous Decision: {database_agent_decision}

- Currently available newsletter sender in the database:
  - TLDR AI
  - TLDR
  - TLDR Web Dev
  - TLDR Product
  - TLDR Founders
  - TLDR Data
  - TLDR Fintech
  - TLDR Marketing
  - TLDR Design
  - TLDR Crypto
  - TLDR InfoSec
  - TLDR DevOps
  - Ben Lorica
  - ByteByteGo
  - Last Week in AI
  - ChinAI Newsletter
  - Tech Brew


{"**FIRST ITERATION: This is the initial database search for this question.**" if is_first_iteration else ""}

### ACTION SPACE
[1] search-database
  Description: Look up more information on the newsletters database
  Parameters:
    - vector-search-query (str): Natural language query for semantic search. To performs a semantic search using vector embeddings to find newsletters with conceptually similar content. Use for broad, thematic, or vague queries where exact keywords may not match (e.g., "emerging AI technologies" or "trends similar to generative AI"). (OPTIONAL)
    - sender-name (str): The newsletter sender name (optional)
    - start-date (str): The start date of search (optional)
    - end-date (str): The end date of search (optional)

[2] answer-search-database
  Description: Answer the question based on the database search results if search results are relevant to the question.

## YOUR DECISION:
Decide the next action based on the context and available actions. If result return empty, Simply report so along with the search query used. 
Note: Put same start and end date for exact date search. Assume year is current year. Assume week start on monday.
IMPORTANT: Only use vector-search-query if user question is asking about a specific topic, keywords else if the user questions only contain sender name and date do not use vector-search-query.

{"**IMPORTANT: Since this is the first iteration, you should start with search-database unless you have enough information to answer directly.**" if is_first_iteration else ""}

Return your response in this format:

```yaml
thinking: |
    <your step-by-step reasoning process - Is the current knowledge base enough to answer the question? If not, use the tools to get more information.>
action: <search-database | answer-search-database>
reason: <why you chose this action>
vector-search-query: <specific search query if action is search-database, if not needed, leave it blank>
start-date: <start date string (YYYY-MM-DD) if action is search-database, if not specified, leave it blank>
end-date: <end date string (YYYY-MM-DD) if action is search-database, if not specified, leave it blank>
sender-name: <sender name if action is search-database, if not specified, leave it blank>
```

IMPORTANT: Make sure to:
1. Use proper indentation (4 spaces) for all multi-line fields
2. Use the | character for multi-line text fields
3. Keep single-line fields without the | character
4. DO NOT use quotes around values (e.g., use: sender-name: TLDR Data, NOT "TLDR Data")
5. For dates, use YYYY-MM-DD format (e.g., 2025-07-13)
6. For sender names, use exact names like TLDR AI, TLDR Data, etc.
        """
        response = call_llm(prompt)
        # debug print
        print("\n\n--------------------------------")
        print("(*) DatabaseAgent Response:")
        print(response)
        print("--------------------------------\n\n")
        # Parse the response to get the decision
        try:
            if "```yaml" in response:
                yaml_str = response.split("```yaml")[1].split("```")[0].strip()
            elif "```" in response:
                yaml_str = response.split("```")[1].split("```")[0].strip()
            else:
                yaml_str = response.strip()

            # Clean up common YAML issues
            yaml_str = yaml_str.replace('"', "").replace("'", "")  # Remove quotes
            yaml_str = yaml_str.replace("...", "")  # Remove ellipsis

            decision = yaml.safe_load(yaml_str)

            # Validate the decision structure
            if not isinstance(decision, dict):
                raise ValueError("Decision must be a dictionary")

            required_fields = ["action"]  # "reason"
            for field in required_fields:
                if field not in decision:
                    raise ValueError(f"Missing required field: {field}")

            return decision

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.error(f"Raw response: {response}")
            raise e

    def exec_fallback(self, prep_res, exc):
        """Fallback when generating DatabaseAgent decision fails."""
        logger.error(f"Error generating DatabaseAgent decision: {exc}")
        return "Error generating DatabaseAgent decision: " + str(exc)

    def post(self, shared, prep_res, exec_res):
        """Save the decision and determine the next step in the flow."""
        # save the decision
        shared["database_agent_decision"] = exec_res
        # save the search query
        if exec_res["action"] == "search-database":
            # save the database search query
            shared["search-database-query"] = {
                "vector-search-query": exec_res.get("vector-search-query", "") or "",
                "sender-name": exec_res.get("sender-name", "") or "",
                "start-date": str(exec_res.get("start-date", "")) or "",
                "end-date": str(exec_res.get("end-date", "")) or "",
            }
            logger.info(
                f"🔍 Agent decided to search database: {shared['search-database-query']}"
            )
            return "search-database"
        else:
            # ready to answer the database search question
            return "answer-search-database"


# ==============================================================
# TOOLS
# ==============================================================


# ------------------------------
# SearchDatabase Tool
# ------------------------------
class SearchDatabase(Node):
    def prep(self, shared):
        """Get the search query from the shared store."""
        # update progress queue
        if "progress_queue" in shared:
            shared["progress_queue"].put_nowait(
                f"Searching for: {shared['search_query']} in the database..."
            )
        return shared["search-database-query"]

    def exec(self, inputs):
        """Search the database for the given query."""
        search_database_query = inputs

        vector_query = search_database_query["vector-search-query"]
        sender = search_database_query["sender-name"] or ""
        start_date = search_database_query["start-date"] or ""
        end_date = search_database_query["end-date"] or ""
        # debug print
        # print("\n\n--------------------------------")
        # print("(*) SearchDatabase Query:")
        # pprint.pprint(search_database_query)
        # print("--------------------------------\n\n")
        query = build_dynamic_query(
            sender_name=sender, start_date=start_date, end_date=end_date
        )
        # results = mongodb_query_search(query) TODO: remove this after testing
        if is_empty(vector_query):  # no vector search - normal query
            query = build_dynamic_query(
                sender_name=sender, start_date=start_date, end_date=end_date
            )
            results = mongodb_query_search(query)
        else:  # vector search
            if sender == "" and start_date == "" and end_date == "":
                results = mongodb_vector_search(vector_query)
            else:
                filter_dict = build_dynamic_query(
                    sender_name=sender, start_date=start_date, end_date=end_date
                )
                results = mongodb_vector_search(
                    vector_query, pre_filter_query=filter_dict
                )
        return results

    def exec_fallback(self, prep_res, exc):
        """Fallback when database search fails."""
        logger.error(f"Error searching the database: {exc}")
        return "decide"

    def post(self, shared, prep_res, exec_res):
        """Save the search results and go back to the decision node."""
        previous = shared.get("current_knowledge_base", "")
        if exec_res == []:
            shared["current_knowledge_base"] = (
                previous
                + "\n\n(*) DATABASE SEARCH: "
                + shared["search_query"]
                + "\nRESULTS: No documents found"
            )
        else:
            # # Add the search results to the context in the shared store
            # shared["current_knowledge_base"] = (
            #     previous
            #     + "\n\n(*) DATABASE SEARCH: "
            #     + shared["search_query"]
            #     + "\nRESULTS: "
            #     + yaml.dump(exec_res, allow_unicode=True)
            # )
            # replace the previous results with the new results
            shared["current_knowledge_base"] = (
                "\n\n(*) DATABASE SEARCH: "
                + shared["search_query"]
                + "\nRESULTS: "
                + yaml.dump(exec_res, allow_unicode=True)
            )
        return "decide"


# ------------------------------
# SearchWeb
# ------------------------------
class SearchWeb(Node):
    def prep(self, shared):
        """Get the question and context for answering."""
        # update progress queue
        if "progress_queue" in shared:
            shared["progress_queue"].put_nowait(
                f"Searching for {shared['search_query']} on the internet..."
            )
        return {
            "search_query": shared["search_query"],
        }

    def exec(self, inputs):
        """Search the web for the given question."""
        search_query = inputs["search_query"]
        return web_search(search_query)

    def exec_fallback(self, prep_res, exc):
        """Fallback when web search fails."""
        logger.error(f"Error searching the web: {exc}")
        return "decide"

    def post(self, shared, prep_res, exec_res):
        """Save the search results and go back to the decision node."""
        # logging, truncate the results to 1000 characters
        exec_res_str = str(exec_res)[:1000]
        logger.info(
            f"🔍 Web search results for {shared['search_query']}: {exec_res_str}"
        )

        # Add the search results to the context in the shared store
        previous = shared.get("current_knowledge_base", "")
        shared["current_knowledge_base"] = (
            previous
            + "\n\n(*) WEB SEARCH: "
            + shared["search_query"]
            + "\nRESULTS: "
            + yaml.dump(exec_res, allow_unicode=True)
        )
        logger.debug("Current shared store in SearchWeb: \n%s", pprint.pformat(shared))
        return "decide"


# ------------------------------
# ReadThisLink
# ------------------------------
class ReadThisLink(Node):
    def prep(self, shared):
        """Read the link and extract the content."""
        # update progress queue
        if "progress_queue" in shared:
            shared["progress_queue"].put_nowait(
                f"Reading the link {shared['read_this_link'][:50]}..."
            )
        return {
            "read_this_link": shared["read_this_link"],
        }

    def exec(self, inputs):
        """Read the link and extract the content."""
        read_this_link = inputs["read_this_link"]
        read_res = url_extractor(read_this_link)
        if read_res["results"] == []:
            return "unable_to_read"
        else:
            return read_res

    def exec_fallback(self, prep_res, exc):
        """Fallback when reading the link fails."""
        logger.error(f"Error reading the link: {exc}")
        return "Error reading the link: " + exc

    def post(self, shared, prep_res, exec_res):
        """Save the link content and go back to the decision node."""
        if exec_res == "unable_to_read":
            read_res = self.exec_fallback(prep_res, exec_res)
        else:
            read_res = exec_res["results"][0]["raw_content"]
        # Add the link content to the context in the shared store
        previous = shared.get("current_knowledge_base", "")
        shared["current_knowledge_base"] = (
            previous
            + "\n\n(*) READ THIS LINK TOOL CALL RESULT: {"
            + shared["read_this_link"]
            + "}\nLINK CONTENT: {"
            + read_res
            + "}"
        )
        return "decide"


# ------------------------------
# ReadCurrentPage
# ------------------------------
class ReadCurrentPage(Node):
    def prep(self, shared):
        """Get the current page url and current page context (if already in the shared store) from the shared store."""
        # update progress queue
        if "progress_queue" in shared:
            shared["progress_queue"].put_nowait(
                f"Getting current page context {shared['current_url']}..."
            )
        return {
            "current_url": shared.get("current_url", ""),
            "current_page_context": shared.get("current_page_context", {}),
        }

    def exec(self, inputs):
        """Get the current page context using url_extractor if not in the shared store."""
        current_url = inputs["current_url"]
        current_page_context = inputs["current_page_context"]
        if current_url == "":
            return "decide", "no_url"
        if current_page_context.get(current_url, "") == "":
            # shared store cache miss
            return url_extractor(current_url), "cache_miss"
        else:
            # shared store cache hit
            return current_page_context.get(current_url, ""), "cache_hit"

    def exec_fallback(self, prep_res, exc):
        """Fallback when current page context fails."""
        logger.error(f"Error getting current page context: {exc}")
        return "decide"

    def post(self, shared, prep_res, exec_res):
        """Save the current page context and go back to the decision node."""
        # logging, truncate the context to 1000 characters
        exec_res_str, exec_res_type = exec_res
        if exec_res_type == "no_url":
            return "decide"
        # save the current page context
        if exec_res_type == "cache_miss":
            shared["current_page_context"][shared["current_url"]] = exec_res_str
        else:
            # cache hit
            pass
        return "decide"


# ==============================================================
# ANSWERS AGENTS
# ==============================================================


# ------------------------------
# AnswerQuestion
# ------------------------------
class AnswerQuestion(Node):
    def prep(self, shared):
        """Get the question and context for answering."""
        # update progress queue
        if "progress_queue" in shared:
            shared["progress_queue"].put_nowait("Crafting final answer...")
        logger.debug(
            "Current shared store in AnswerQuestion: \n%s", pprint.pformat(shared)
        )
        return {
            "user_question": shared["user_question"],
            "current_knowledge_base": shared.get("current_knowledge_base", ""),
            "instruction": shared["instruction"],
            "conversation_history": shared.get("conversation_history", []),
            "current_page_context": shared.get("current_page_context", ""),
            "current_url": shared.get("current_url", ""),
            "agent_decision": shared.get("agent_decision", ""),
        }

    def exec(self, inputs):
        """Call the LLM to generate a final answer."""
        user_question = inputs["user_question"]
        current_knowledge_base = inputs["current_knowledge_base"]
        instruction = inputs["instruction"]
        conversation_history = inputs["conversation_history"]
        current_page_context = str(
            {inputs["current_url"]: inputs["current_page_context"]}
        )
        current_url = inputs["current_url"]
        agent_decision = inputs["agent_decision"]
        logger.info("✍️ Crafting final answer...")

        # Create a prompt for the LLM to answer the question
        prompt = f"""
### CONTEXT
Based on the following information, answer the question.
Question: {user_question}
Research: {current_knowledge_base}
Conversation History: {conversation_history}
Current Newsletter Page Context: {current_page_context}
Previous agent decision: {agent_decision}

### INSTRUCTION
{instruction}

## YOUR ANSWER:
Provide a comprehensive answer using the research results. IMPORTANT:
- Use the research results and current newsletter page context to answer the question.
- If the research results are not relevant to the question, say so.
- If the research results are not enough to answer the question, say so.
- Must include the source of the information in the answer in the format:
"""
        # TODO: add answer instructions
        # + open("prompts/answer_instructions.md", "r").read()
        # Call the LLM to generate an answer
        answer = call_llm(prompt)
        return answer

    def exec_fallback(self, prep_res, exc):
        """Fallback when answer generation fails."""
        logger.error(f"Error generating answer: {exc}")
        return "Error generating answer: " + exc

    def post(self, shared, prep_res, exec_res):
        """Save the final answer and complete the flow."""
        # Save the answer in the shared store
        conversation_history = shared.get("conversation_history", [])
        conversation_history.append({"bot": exec_res})
        shared["conversation_history"] = conversation_history
        shared["final_answer"] = exec_res

        logger.info("✅ Answer generated successfully")
        # logger.info(f"💬 Conversation history: {pprint.pformat(conversation_history)}")

        # We're done - no need to continue the flow
        return "done"


# ------------------------------
# AnswerDatabaseSearch
# ------------------------------
class AnswerDatabaseSearch(Node):
    def prep(self, shared):
        """Get the database search query from the shared store."""
        # update progress queue
        if "progress_queue" in shared:
            shared["progress_queue"].put_nowait(
                "Crafting final answer from database research..."
            )
        return {
            "user_question": shared.get("user_question", ""),
            "current_knowledge_base": shared.get("current_knowledge_base", ""),
            "database_agent_decision": shared.get("database_agent_decision", ""),
        }

    def exec(self, inputs):
        """Call the LLM to generate a search query for the database."""
        user_question = inputs["user_question"]
        current_knowledge_base = inputs["current_knowledge_base"]
        database_agent_decision = inputs["database_agent_decision"]
        answer_instructions = open("prompts/answer_instructions.md", "r").read()
        prompt = f"""
        ### CONTEXT
        User Question: {user_question}
        Previous Research: {current_knowledge_base}
        Database Agent Decision: {database_agent_decision}

        ## NEXT ACTION
        {answer_instructions}
        """
        # save prompt to file
        with open("prompts/answer_prompt.md", "w") as f:
            f.write(prompt)
        response = call_llm(prompt)
        return response

    def exec_fallback(self, prep_res, exc):
        """Fallback when generating AnswerDatabaseSearch decision fails."""
        logger.error(f"Error generating AnswerDatabaseSearch decision: {exc}")
        return "Error generating AnswerDatabaseSearch decision: " + exc

    def post(self, shared, prep_res, exec_res):
        """Save the decision and determine the next step in the flow."""
        conversation_history = shared.get("conversation_history", [])
        conversation_history.append({"bot": exec_res})
        shared["conversation_history"] = conversation_history
        shared["final_answer"] = exec_res
        logger.info(f"🔍 Answer generated from database agent: {exec_res}")
        return "done"
