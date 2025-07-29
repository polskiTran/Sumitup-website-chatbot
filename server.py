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
from utils.mongo_db import (
    create_chat_session,
    delete_chat_session,
    get_all_chat_sessions_ids,
    load_chat_session,
    save_chat_session,
)

app = FastAPI()

# Mount static files (HTML, CSS, JS)
# app.mount("/static", StaticFiles(directory="static"), name="static")


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


# @app.get("/", response_class=HTMLResponse)
# async def get_root(request: Request):
#     """Serve the main configuration page."""
#     with open("static/index.html", "r") as f:
#         return HTMLResponse(content=f.read())


# @app.get("/chatbot", response_class=HTMLResponse)
# async def get_chatbot(request: Request):
#     """Serve the chatbot page."""
#     with open("static/chatbot.html", "r") as f:
#         return HTMLResponse(content=f.read())


# @app.get("/embed/chatbot.js", response_class=HTMLResponse)
# async def get_chatbot_js(request: Request):
#     """Serve the chatbot JavaScript for embedding."""
#     with open("static/chatbot.js", "r") as f:
#         content = f.read()
#     return HTMLResponse(
#         content=content, headers={"Content-Type": "application/javascript"}
#     )


class ConnectionManager:
    """Manages WebSocket connections, session IDs, and conversational state."""

    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict] = {}
        self.flows: Dict[WebSocket, Flow] = {}
        self.session_ids: Dict[WebSocket, str] = {}  # Track session ID per connection

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = {}
        self.flows[websocket] = None  # Will be set after session selection
        self.session_ids[websocket] = None
        print("Client connected")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        if websocket in self.flows:
            del self.flows[websocket]
        if websocket in self.session_ids:
            del self.session_ids[websocket]
        print("Client disconnected")

    def get_shared_state(self, websocket: WebSocket) -> Dict:
        return self.active_connections.get(websocket)

    def set_shared_state(self, websocket: WebSocket, state: Dict):
        self.active_connections[websocket] = state

    def get_flow(self, websocket: WebSocket) -> Flow:
        return self.flows.get(websocket)

    def set_flow(self, websocket: WebSocket, flow: Flow):
        self.flows[websocket] = flow

    def get_session_id(self, websocket: WebSocket) -> str:
        return self.session_ids.get(websocket)

    def set_session_id(self, websocket: WebSocket, session_id: str):
        self.session_ids[websocket] = session_id


manager = ConnectionManager()


def create_fresh_shared_state():
    """Create a fresh shared state with properly isolated mutable objects."""
    shared_state = settings.shared_store.copy()
    shared_state["conversation_history"] = []  # Fresh conversation history
    shared_state["current_page_context"] = {}  # Fresh page context
    # Note: progress_queue will be created fresh for each request anyway
    return shared_state


@app.websocket("/api/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Step 1: Send all available chat session IDs to the frontend
        session_ids = get_all_chat_sessions_ids() or []
        await websocket.send_text(
            json.dumps({"type": "session_list", "payload": session_ids})
        )

        # Step 2: Wait for frontend to select or create a session
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
            payload = message.get("payload", {})

            # if msg_type == "select_session":
            #     session_id = payload.get("session_id")
            #     chat_session = load_chat_session(session_id)
            #     if not chat_session:
            #         await websocket.send_text(
            #             json.dumps({"type": "error", "payload": "Session not found."})
            #         )
            #         continue
            #     shared_state = chat_session["chat_session_shared_store"]
            #     manager.set_shared_state(websocket, shared_state)
            #     manager.set_session_id(websocket, session_id)
            #     manager.set_flow(websocket, create_support_bot_flow())
            #     await websocket.send_text(
            #         json.dumps({"type": "session_loaded", "payload": session_id})
            #     )
            #     break
            if msg_type == "select_session":  # select existing session
                session_id = payload.get("session_id")
                chat_session = load_chat_session(session_id)
                if not chat_session:
                    await websocket.send_text(
                        json.dumps({"type": "error", "payload": "Session not found."})
                    )
                    continue
                shared_state = chat_session["chat_session_shared_store"]
                conversation_history = shared_state.get("conversation_history", [])
                manager.set_shared_state(websocket, shared_state)
                manager.set_session_id(websocket, session_id)
                manager.set_flow(websocket, create_support_bot_flow())
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "session_loaded",
                            "payload": {
                                "session_id": session_id,
                                "conversation_history": conversation_history,
                            },
                        }
                    )
                )
                break
            elif msg_type == "create_session":  # create new session
                # Start with a fresh shared store with properly isolated mutable objects
                shared_state = create_fresh_shared_state()
                session_id = create_chat_session(shared_state)
                if not session_id:
                    await websocket.send_text(
                        json.dumps(
                            {"type": "error", "payload": "Failed to create session."}
                        )
                    )
                    continue
                manager.set_shared_state(websocket, shared_state)
                manager.set_session_id(websocket, session_id)
                manager.set_flow(websocket, create_support_bot_flow())
                await websocket.send_text(
                    json.dumps({"type": "session_created", "payload": session_id})
                )
                break
            elif msg_type == "delete_session":
                session_id = payload.get("session_id")
                if not session_id:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "payload": "Session ID is required for deletion.",
                            }
                        )
                    )
                    continue

                delete_chat_session(session_id)
                # Send updated session list
                updated_session_ids = get_all_chat_sessions_ids() or []
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "session_deleted",
                            "payload": {
                                "deleted_session_id": session_id,
                                "updated_session_list": updated_session_ids,
                            },
                        }
                    )
                )
                continue
            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "payload": "Please select, create, or delete a session.",
                        }
                    )
                )

        # Step 3: Main chat loop
        while True:
            print(
                "\n========================================================START OF TURN========================================================\n"
            )
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")
            payload = message.get("payload", {})

            # Handle session switching in main loop
            if msg_type == "select_session":
                session_id = payload.get("session_id")
                chat_session = load_chat_session(session_id)
                if not chat_session:
                    await websocket.send_text(
                        json.dumps({"type": "error", "payload": "Session not found."})
                    )
                    continue
                shared_state = chat_session["chat_session_shared_store"]
                conversation_history = shared_state.get("conversation_history", [])
                print(
                    f"📥 Loaded session {session_id} with {len(conversation_history)} conversation turns (initial)"
                )
                for i, turn in enumerate(conversation_history):
                    print(f"  Turn {i + 1}: {turn}")
                manager.set_shared_state(websocket, shared_state)
                manager.set_session_id(websocket, session_id)
                manager.set_flow(websocket, create_support_bot_flow())
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "session_loaded",
                            "payload": {
                                "session_id": session_id,
                                "conversation_history": conversation_history,
                            },
                        }
                    )
                )
                continue
            elif msg_type == "create_session":
                # Start with a fresh shared store with properly isolated mutable objects
                shared_state = create_fresh_shared_state()
                session_id = create_chat_session(shared_state)
                if not session_id:
                    await websocket.send_text(
                        json.dumps(
                            {"type": "error", "payload": "Failed to create session."}
                        )
                    )
                    continue
                manager.set_shared_state(websocket, shared_state)
                manager.set_session_id(websocket, session_id)
                manager.set_flow(websocket, create_support_bot_flow())
                await websocket.send_text(
                    json.dumps({"type": "session_created", "payload": session_id})
                )
                continue
            elif msg_type == "delete_session":
                session_id_to_delete = payload.get("session_id")
                if not session_id_to_delete:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "payload": "Session ID is required for deletion.",
                            }
                        )
                    )
                    continue

                delete_chat_session(session_id_to_delete)
                # Send updated session list
                updated_session_ids = get_all_chat_sessions_ids() or []
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "session_deleted",
                            "payload": {
                                "deleted_session_id": session_id_to_delete,
                                "updated_session_list": updated_session_ids,
                            },
                        }
                    )
                )

                # If the deleted session was the current session, reset the connection
                current_session_id = manager.get_session_id(websocket)
                if current_session_id == session_id_to_delete:
                    manager.set_shared_state(websocket, {})
                    manager.set_session_id(websocket, None)
                    manager.set_flow(websocket, None)
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "session_reset",
                                "payload": "Current session was deleted. Please select a new session.",
                            }
                        )
                    )
                continue

            # Handle regular chat messages
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
            session_id = manager.get_session_id(websocket)
            if not shared_state:
                # This should not happen in normal flow since session selection should have created it
                print("⚠️  Warning: No shared state found, creating fresh state")
                shared_state = create_fresh_shared_state()
                manager.set_shared_state(websocket, shared_state)
            # Note: Removed msg_type == "start" condition to prevent conversation history loss
            # get current url from payload
            current_url = payload.get("current_url", "")
            shared_state["current_url"] = current_url
            # check if current_url is in the shared store
            if current_url not in shared_state["current_page_context"]:
                shared_state["current_page_context"][current_url] = ""

            # append user messages
            shared_state["user_question"] = question
            # Ensure conversation_history exists and append new user question
            if "conversation_history" not in shared_state:
                shared_state["conversation_history"] = []
            shared_state["conversation_history"].append({"user": question})

            # Debug: Print current conversation history length
            # print(
            #     f"💬 Conversation history before flow: {len(shared_state.get('conversation_history', []))} items"
            # )

            q = asyncio.Queue()
            shared_state["progress_queue"] = q

            def run_sync_flow_in_thread():
                try:
                    support_bot_flow.run(shared_state)
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
                        answer_data = {
                            "answer": final_answer,
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
                    }
                elif progress_msg.startswith("ERROR:::"):
                    event_data = {
                        "type": "error",
                        "payload": progress_msg.replace("ERROR:::", "", 1),
                    }
                else:
                    event_data = {"type": "progress", "payload": progress_msg}
                await websocket.send_text(json.dumps(event_data))

            # Debug: Print conversation history after flow
            # print(
            #     f"💬 Conversation history after flow: {len(shared_state.get('conversation_history', []))} items"
            # )
            # for i, turn in enumerate(shared_state.get("conversation_history", [])):
            #     print(f"  Turn {i + 1}: {turn}")

            # Save chat session after each turn
            if session_id:
                save_chat_session(session_id, shared_state)
                # print(
                #     f"💾 Saved session {session_id} with {len(shared_state.get('conversation_history', []))} conversation turns"
                # )

            manager.set_shared_state(websocket, shared_state)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7777)
