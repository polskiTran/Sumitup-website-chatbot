import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pocketflow import Flow

from config import settings
from flow import create_support_bot_flow

app = FastAPI()

# Mount static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


def validate_and_sanitize_input(
    question: str, instruction: str = ""
) -> tuple[str, str]:
    """Validate and sanitize user inputs for safety."""
    if len(question) > 1000:
        raise ValueError("Question must be 1000 characters or less")

    if len(instruction) > 2000:
        raise ValueError("Instruction must be 2000 characters or less")

    if not question.strip():
        raise ValueError("Question cannot be empty")

    dangerous_patterns = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    combined_text = f"{question} {instruction}".lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, combined_text, re.IGNORECASE):
            raise ValueError("Input contains potentially unsafe content")

    question = question.replace("<", "&lt;").replace(">", "&gt;")
    instruction = instruction.replace("<", "&lt;").replace(">", "&gt;")

    return question.strip(), instruction.strip()


@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    """Serve the main configuration page."""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/chatbot", response_class=HTMLResponse)
async def get_chatbot(request: Request):
    """Serve the chatbot page."""
    with open("static/chatbot.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/embed/chatbot.js", response_class=HTMLResponse)
async def get_chatbot_js(request: Request):
    """Serve the chatbot JavaScript for embedding."""
    with open("static/chatbot.js", "r") as f:
        content = f.read()
    return HTMLResponse(
        content=content, headers={"Content-Type": "application/javascript"}
    )


class ConnectionManager:
    """Manages WebSocket connections and their associated conversational state."""

    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict] = {}
        self.flows: Dict[WebSocket, Flow] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = {}
        self.flows[websocket] = create_support_bot_flow()
        print("Client connected")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        if websocket in self.flows:
            del self.flows[websocket]
        print("Client disconnected")

    def get_shared_state(self, websocket: WebSocket) -> Dict:
        return self.active_connections.get(websocket)

    def set_shared_state(self, websocket: WebSocket, state: Dict):
        self.active_connections[websocket] = state

    def get_flow(self, websocket: WebSocket) -> Flow:
        return self.flows.get(websocket)


manager = ConnectionManager()


@app.websocket("/api/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            print(
                "\n========================================================START OF TURN========================================================\n"
            )
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")
            payload = message.get("payload", {})

            try:
                question = payload.get("question")
                if not question:
                    raise ValueError("Question is missing.")
                question, _ = validate_and_sanitize_input(question)
            except ValueError as e:
                await websocket.send_text(
                    json.dumps({"type": "error", "payload": str(e)})
                )
                continue

            shared_state = manager.get_shared_state(websocket)
            support_bot_flow = manager.get_flow(websocket)
            if msg_type == "start" or not shared_state:
                # current_url = payload.get("current_url", "")
                # shared_state["current_url"] = current_url
                # extra_urls = payload.get("extra_urls", [])
                # instruction = payload.get("instruction", "")
                # load instruction from instruction.md
                # instruction = (
                #     "Current date: "
                #     + datetime.now().strftime("%Y-%m-%d")
                #     + "\n"
                #     + open("instruction.md", "r", encoding="utf-8").read()
                # )
                # prefixes = payload.get("prefixes", [])

                # # Limit extra_urls to maximum 10
                # if len(extra_urls) > 10:
                #     extra_urls = extra_urls[:10]

                # # Limit prefixes to maximum 10
                # if len(prefixes) > 10:
                #     prefixes = prefixes[:10]

                # # If current_url is empty, use the current page URL (this would be handled by frontend)
                # # Combine current_url and extra_urls into start_urls, removing duplicates
                # start_urls = []
                # if current_url:
                #     start_urls.append(current_url)
                # start_urls.extend(extra_urls)

                # # Remove duplicates while preserving order
                # start_urls = list(dict.fromkeys(start_urls))

                # if not start_urls:
                #     await websocket.send_text(
                #         json.dumps(
                #             {
                #                 "type": "error",
                #                 "payload": "At least one URL (current or extra) is required.",
                #             }
                #         )
                #     )
                #     continue

                # shared_state = {
                #     "conversation_history": [],
                #     "instruction": instruction,
                #     "current_url": current_url,
                #     "allowed_domains": prefixes,
                #     "max_iterations": 5,
                #     "max_pages": 50,
                #     "content_max_chars": 10000,
                #     "max_urls_per_iteration": 5,
                #     "all_discovered_urls": start_urls.copy(),
                #     "visited_urls": set(),
                #     "url_content": {},
                #     "url_graph": {},
                #     "urls_to_process": list(range(len(start_urls))),
                # }
                shared_state.update(settings.shared_store)
            # get current url from payload
            current_url = payload.get("current_url", "")
            shared_state["current_url"] = current_url
            # check if current_url is in the shared store
            if current_url not in shared_state["current_page_context"]:
                shared_state["current_page_context"][current_url] = ""

            # append user messages
            shared_state["user_question"] = question
            shared_state["conversation_history"].append({"user": question})
            # shared_state["current_iteration"] = 0
            # shared_state["final_answer"] = None

            q = asyncio.Queue()
            shared_state["progress_queue"] = q

            def run_sync_flow_in_thread():
                try:
                    support_bot_flow.run(shared_state)
                    # final_answer = shared_state.get("final_answer")
                    # {"bot": "answer"}
                    final_answer = shared_state.get("conversation_history")[-1].get(
                        "bot"
                    )
                    print(
                        f"\n🤖 ~~~~~ Final answer ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~:\n {final_answer}\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n"
                    )
                    print(
                        "========================================================END OF TURN========================================================\n\n"
                    )
                    if final_answer:
                        # useful_indices = shared_state.get("useful_visited_indices", [])
                        # useful_pages = [
                        #     shared_state["all_discovered_urls"][idx]
                        #     for idx in useful_indices
                        #     if idx < len(shared_state["all_discovered_urls"])
                        # ]
                        answer_data = {
                            "answer": final_answer,
                            # "useful_pages": useful_pages,
                        }
                        q.put_nowait(f"FINAL_ANSWER:::{json.dumps(answer_data)}")
                    else:
                        q.put_nowait(
                            "ERROR:::Flow finished, but no answer was generated."
                        )
                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    q.put_nowait(f"ERROR:::An unexpected error occurred: {str(e)}")
                finally:
                    q.put_nowait(None)

            asyncio.create_task(asyncio.to_thread(run_sync_flow_in_thread))

            while True:
                progress_msg = await q.get()
                if progress_msg is None:
                    break

                event_data = {}
                if progress_msg.startswith("FINAL_ANSWER:::"):
                    answer_data = json.loads(
                        progress_msg.replace("FINAL_ANSWER:::", "", 1)
                    )
                    event_data = {
                        "type": "final_answer",
                        "payload": answer_data["answer"],
                        # "useful_pages": answer_data["useful_pages"],
                    }
                elif progress_msg.startswith("ERROR:::"):
                    event_data = {
                        "type": "error",
                        "payload": progress_msg.replace("ERROR:::", "", 1),
                    }
                else:
                    event_data = {"type": "progress", "payload": progress_msg}
                await websocket.send_text(json.dumps(event_data))

            if shared_state.get("final_answer"):
                shared_state["conversation_history"].append(
                    {
                        "user": shared_state["user_question"],
                        "bot": shared_state["final_answer"],
                    }
                )
            # shared_state["urls_to_process"] = []

            manager.set_shared_state(websocket, shared_state)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# @app.websocket("/api/ws/chat")
# async def websocket_endpoint(websocket: WebSocket):
#     # connect to the websocket
#     await manager.connect(websocket)

#     # Initialize conversation history for this connection
#     shared_store = {"websocket": websocket, "conversation_history": []}

#     try:
#         while True:
#             data = await websocket.receive_text()
#             message = json.loads(data)

#             # Update only the current message, keep conversation history
#             shared_store["user_message"] = message.get("content", "")

#             flow = create_support_bot_flow()
#             await flow.run_async(shared_store)

#     except WebSocketDisconnect:
#         # disconnect from the websocket
#         manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7777)
