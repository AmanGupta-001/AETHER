from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, RedirectResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Dict, List
import asyncio
import os
import pymongo
import requests
import logging
from collections import defaultdict
import json
from datetime import datetime
from pathlib import Path
from graph.graphAgent import Graph
import ai_agents.neo_agent_llama
from ai_agents.neo_think_agent import NeoThinkAgent
from summarize_chat import summarize_chat
from rag import embed_and_store
from modules.user_data_setup import check_folders
from modules.chat import read_chat
from ai_agents.neo_agent_llama import NeoAgentLlama

# Example of how to get variables from .env via docker-compose and .env
#from config import PORT



log = logging.getLogger("uvicorn")
log.setLevel(logging.DEBUG)
logger = logging.getLogger("Initaton")
logger.setLevel(logging.INFO)
logger.info("Starting application loading...") # Use the logger


'''
    FOR API DOCUMENTATION, VISIT: http://localhost:3000/docs
    
    Websocket endpoints are not automatically documented.

    Running using uvicorn outside of docker: 
    1. Enter a venv
    2. python -m uvicorn main:app --host 0.0.0.0 --port 3000 --reload
'''

#
# Setup
#
logger.info("Booting....")
check_folders()  # Check directories are made for user data

#
from starlette.middleware.base import BaseHTTPMiddleware

# Server config
#
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Make CORS more restrictive
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No-cache middleware for static files so the browser always fetches fresh JS/CSS
class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheStaticMiddleware)

# Mount static folder for UI
app.mount("/static", StaticFiles(directory="static"), name="static")

# ANSI escape codes for colors
RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"

# Agent instantiation
logger.info("Initiating Aether...")
try:
    jarvis = Graph()
    logger.info(str(jarvis))
    logger.info("Aether Created")
except Exception as e:
    logger.info(f"Error initializing Aether: {e}")
    # Fallback to simpler agent
    logger.info(YELLOW + "Falling back to alternate agent")
    jarvis = NeoThinkAgent()
    logger.info(YELLOW + str(jarvis))

welcome_text = r'''
      _____  ____________________ ______________ ___ 
     /  _  \ \_   _____/\__    ___/   |   \_   _____/|   |
    /  /_\  \ |    __)_   |    | /    ~    \    __)_ |   |
   /    |    \|        \  |    | \    Y    /        \|   |__
   \____|__  /_______  /  |____|  \___|_  /_______  /|____/
           \/        \/                 \/        \/       
'''
print(welcome_text)

# Initialize active_chats with standard llm format
active_chats: Dict[str, Dict[str, List[Dict[str, str]]]] = defaultdict(lambda: {"chat_history": []})

# MongoDB Connection
client = None
collection = None  # Default to None if MongoDB isn't available

try:
    client = pymongo.MongoClient("mongodb://mongodb:27017/", serverSelectionTimeoutMS=5000)
    client.server_info()  # Try to connect
    print("✅ Connected to MongoDB!")
    
    db = client["chat_database"]
    collection = db["chats"]
except pymongo.errors.ServerSelectionTimeoutError:
    print("❌ MongoDB is not available. Running without database features.")
    client = None  # Ensure client is None to prevent errors
    collection = None  # Prevent further crashes


# WebSocket manager
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"Session {session_id} connected.")

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        print(f"Session {session_id} disconnected.")

    async def send_message(self, session_id: str, message: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)

ws_manager = WebSocketManager()

#
# HTTP Endpoints
#
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/")
async def hello_world():
    return FileResponse("static/index.html")

@app.get("/ping_server")
async def ping_server():
    return "Hello from API!"

# Pydantic models for request/response bodies
class ChatSummaryRequest(BaseModel):
    chat_history: List[Dict[str, str]]
    user_id: str

@app.post("/vectorize_chat")
async def summarize_store(data: ChatSummaryRequest):
    if not data.chat_history or not data.user_id:
        raise HTTPException(status_code=400, detail="chat_history and user_id are required")

    summary = summarize_chat(data.chat_history)
    embed_and_store(summary, data.user_id)

    return {"status": "success", "summary": summary}

class RecordingRequest(BaseModel):
    conversation_id: str

@app.post("/start_recording")
async def start_recording_route(data: RecordingRequest):
    print("Starting recording...")
    response = requests.post(f"http://speech-to-text:3001/start_recording/{data.conversation_id}")

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to start recording")

    return {"status": "recording_started"}

@app.post("/recording_completed")
async def recording_completed(data: dict):
    session_id = data.get("session_id", "")
    text = data.get("text", "")
    conversation_id = data.get("conversation_id", "")
    print(f"Recording completed for conversation ID {conversation_id} with text: {text}")

    asyncio.create_task(jarvis.run(text, session_id))  # Run Jarvis response asynchronously. passing session_id

    return {"status": "success"}

@app.get("/ws/health/{session_id}")
async def websocket_health(session_id: str):
    """Check if a WebSocket connection is active for a given session ID"""
    if session_id in active_websockets:
        return {"status": "connected", "session_id": session_id}
    return {"status": "disconnected", "session_id": session_id}

# ── Chat Session REST API ───────────────────────────────────────────────────────

@app.get("/api/sessions")
async def get_sessions():
    """Return all sessions with title + preview for the sidebar."""
    result = []
    for sid, data in active_chats.items():
        history = data.get("chat_history", [])
        if not history:
            continue
        first = history[0]
        title   = (first.get("human_message") or "New conversation")[:40]
        preview = (first.get("ai_message")    or "")[:80]
        updated = data.get("updated_at", "")
        result.append({"session_id": sid, "title": title, "preview": preview, "updated_at": updated})
    # Newest first
    result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return result

@app.get("/api/vapi/config")
async def get_vapi_config():
    """Return Vapi AI public key and assistant ID for real-time voice streaming."""
    return {
        "publicKey": os.getenv("VAPI_PUBLIC_KEY", "be2354ea-73f2-4d78-b896-d6a2b3d43078"),
        "assistantId": os.getenv("VAPI_ASSISTANT_ID", "7ac7e51a-9080-424b-9004-78fa7bd31092")
    }

class ExecuteToolRequest(BaseModel):
    tool_name: str
    parameters: dict = {}

@app.post("/api/tools/execute")
async def execute_tool(data: ExecuteToolRequest):
    """Execute any registered AETHER tool directly (for Vapi voice and direct agent calls)."""
    import tools.tools as tools_module
    all_tools = {t.name: t for t in tools_module.get_tools()}
    
    # Map common aliases from Vapi to exact tool names
    alias_map = {
        "check_calendar": "read_calendar_events",
        "get_calendar": "read_calendar_events",
        "read_calendar": "read_calendar_events",
        "calendar": "read_calendar_events",
        "get_system_telemetry": "system_monitor",
        "monitor": "system_monitor",
        "telemetry": "system_monitor"
    }
    tool_name = alias_map.get(data.tool_name, data.tool_name)
    
    if tool_name not in all_tools:
        raise HTTPException(status_code=404, detail=f"Tool '{data.tool_name}' not found.")
    
    target_tool = all_tools[tool_name]
    try:
        params = data.parameters or {}
        res = target_tool.invoke(params)
        return {"success": True, "tool_name": tool_name, "result": str(res)}
    except Exception as e:
        log.error(f"Error executing tool {tool_name}: {e}")
        return {"success": False, "tool_name": tool_name, "error": str(e)}

class SaveSessionRequest(BaseModel):
    session_id: str
    human_message: str
    ai_message: str

@app.post("/api/sessions/save")
async def save_session(data: SaveSessionRequest):
    """Persist a human↔AI exchange into active_chats."""
    sid = data.session_id
    entry = {
        "human_message": data.human_message,
        "ai_message":    data.ai_message,
        "timestamp":     datetime.utcnow().isoformat()
    }
    active_chats[sid]["chat_history"].append(entry)
    active_chats[sid]["updated_at"] = datetime.utcnow().isoformat()
    return {"status": "saved"}

# ── Gmail OAuth2 ────────────────────────────────────────────────────────────────

GMAIL_TOKEN_PATH   = Path(__file__).resolve().parent / "gmail_token.json"
GMAIL_SECRETS_PATH = Path(__file__).resolve().parent / "gmail_oauth_client.json"
GMAIL_SCOPES       = ["https://www.googleapis.com/auth/gmail.readonly"]
GMAIL_REDIRECT_URI = "http://localhost:3000/gmail/callback"

@app.get("/gmail/status")
async def gmail_status():
    """Returns whether Gmail is currently connected."""
    connected = GMAIL_TOKEN_PATH.exists()
    email = None
    if connected:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build as gbuild
            creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_PATH), GMAIL_SCOPES)
            svc   = gbuild("oauth2", "v2", credentials=creds)
            info  = svc.userinfo().get().execute()
            email = info.get("email")
        except Exception:
            connected = False
    return {"connected": connected, "email": email}

@app.get("/gmail/auth")
async def gmail_auth():
    """Kick off the OAuth2 flow — redirect the user to Google consent screen."""
    if not GMAIL_SECRETS_PATH.exists():
        return HTMLResponse("""
        <html><body style="font-family:sans-serif;background:#111;color:#eee;padding:40px">
        <h2>⚠️ Gmail OAuth client secrets not found</h2>
        <p>To link Gmail, you need a <strong>gmail_oauth_client.json</strong> file inside <code>core/</code>.<br>
        Follow these steps:</p>
        <ol>
          <li>Go to <a href="https://console.cloud.google.com/apis/credentials" target="_blank" style="color:#00d2ff">Google Cloud Console → Credentials</a></li>
          <li>Create an <strong>OAuth 2.0 Client ID</strong> → Application type: <em>Web application</em></li>
          <li>Add <code>http://localhost:3000/gmail/callback</code> as an Authorized redirect URI</li>
          <li>Download the JSON and save it as <code>core/gmail_oauth_client.json</code></li>
          <li>Enable the <strong>Gmail API</strong> and <strong>People API</strong> in your project</li>
          <li>Return here: <a href="/gmail/auth" style="color:#00d2ff">http://localhost:3000/gmail/auth</a></li>
        </ol>
        </body></html>
        """, status_code=200)

    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_secrets_file(
        str(GMAIL_SECRETS_PATH),
        scopes=GMAIL_SCOPES + ["https://www.googleapis.com/auth/userinfo.email", "openid"],
        redirect_uri=GMAIL_REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return RedirectResponse(auth_url)

@app.get("/gmail/callback")
async def gmail_callback(request: Request):
    """Handle the OAuth2 callback, save token, and show success."""
    if not GMAIL_SECRETS_PATH.exists():
        raise HTTPException(status_code=500, detail="OAuth secrets not configured")

    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_secrets_file(
        str(GMAIL_SECRETS_PATH),
        scopes=GMAIL_SCOPES + ["https://www.googleapis.com/auth/userinfo.email", "openid"],
        redirect_uri=GMAIL_REDIRECT_URI
    )
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials
    GMAIL_TOKEN_PATH.write_text(creds.to_json())

    return HTMLResponse("""
    <html><body style="font-family:sans-serif;background:#111;color:#eee;padding:40px;text-align:center">
    <h2 style="color:#00d2ff">✅ Gmail Connected!</h2>
    <p>Your Gmail account is now linked to AETHER.</p>
    <p>You can now ask AETHER things like:<br>
    <em>"Show me my latest emails"</em> &nbsp;•&nbsp;
    <em>"Do I have any unread messages from my boss?"</em> &nbsp;•&nbsp;
    <em>"Summarise my inbox"</em></p>
    <script>setTimeout(() => window.close(), 3000);</script>
    <p style="color:#666;font-size:13px">This window will close automatically in 3 seconds.</p>
    </body></html>
    """)

@app.post("/gmail/disconnect")
async def gmail_disconnect():
    """Remove stored Gmail token."""
    if GMAIL_TOKEN_PATH.exists():
        GMAIL_TOKEN_PATH.unlink()
    return {"status": "disconnected"}

#
# WebSocket Endpoints
#

# User prompting request models
class UserPromptData(BaseModel):
    prompt: str
    conversation_id: str

class UserPromptRequest(BaseModel):
    event: str
    data: UserPromptData

# Generic event request
class BaseEventRequest(BaseModel):
    event: str

def print_status(active_websocket):
    print("WebSocketAgent loaded...")
    print(active_websocket)

active_websockets = {}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(websocket, session_id)
    global active_websockets
    active_websockets[session_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("event")
            print(f"Received event: {event_type}")
            ### User prompt
            if event_type == "user_prompt":
                req = UserPromptRequest(**data) # Unpacks message into UserPromptRequest
                ai_response = await jarvis.run(req.data.prompt, session_id=session_id, websocket=websocket) # Run Jarvis response

            ### Get chat history
            elif event_type == "get_chat_history":
                history = active_chats.get(session_id, {"chat_history": []})
                await ws_manager.send_message(session_id, json.dumps({"event": "chat_history", "data": history}))

    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)

#
# Server Startup
#
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)

    if collection is None:  # Prevent MongoDB crash
        print("MongoDB is not available. Skipping DB insert.")
    # else:
    #     chat_entry = {
    #         "session_id": session_id,
    #         "conversation_id": message.get("conversation_id", ""),
    #         "human_message": message.get("prompt", ""),
    #         "ai_message": "",
    #     }
    #     inserted_id = collection.insert_one(chat_entry).inserted_id
    #     print(f"Chat entry inserted with ID: {inserted_id}")

    #await ws_manager.send_message(session_id, response) # Send response to frontend
    #print(f"Jarvis response sent to session {session_id}")
    # local chat history storage/cache
    # TODO: Make this purely mongoDB
    # if session_id in active_chats:
    #     active_chats[session_id]["chat_history"].append(chat_entry)

    # try:
    #     collection.update_one(
    #         {"_id": inserted_id},
    #         {"$set": {"ai_message": response}}
    #     )
    #     print(f"Updated MongoDB entry {inserted_id} with AI response")
    # except Exception as e:
    #     print(f"Jarvis encountered an error updating MongoDB entry: {e}")