from typing_extensions import TypedDict
from fastapi.websockets import WebSocket
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode, tools_condition
import requests

"""
Baseclass for all agents using websocket and requires the simple .run function
"""
class WebSocketAgent:
    async def run(self, user_prompt: str, session_id: str, websocket: WebSocket = None):
        """
        Run the agent with a user prompt and send the response via FastAPI WebSockets.
        """
        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 50}
        
        # Check if websocket exists for session
        if websocket is None:
            import main
            if session_id not in main.active_websockets:
                print(f"No active websocket for session {session_id}")
                return "Connection lost. Please refresh the page to reconnect."
            websocket = main.active_websockets[session_id]
        print(f"Getting websocket for session {session_id}...")
        
        try:
            input_data = {"messages": [HumanMessage(content=user_prompt)]}
            # Send start message with try/except to handle disconnections
            try:
                await websocket.send_json({"event": "start_message", "data": " "})
            except Exception as e:
                print(f"Error sending start message: {e}")
                # Remove invalid websocket
                if session_id in main.active_websockets:
                    del main.active_websockets[session_id]
                return "Connection lost. Please refresh the page to reconnect."
                
            # Streaming processing code
            async for event in self.graph.astream_events(input_data, config, version='v2'):
                event_type = event.get('event')
                node_name = event.get('metadata', {}).get('langgraph_node')
                
                ### Stream tokens ONLY from the user-facing 'generate' node
                if event_type == 'on_chat_model_stream' and node_name == 'generate':
                    chunk = event['data'].get('chunk')
                    if hasattr(chunk, 'content') and chunk.content:
                        try:
                            await websocket.send_json({"event": "ai_chunk", "data": chunk.content})
                        except Exception:
                            pass

                ### Tool response
                elif event_type == 'on_chain_stream' and event.get('name') == 'tools':
                    messages = event.get('data', {}).get('chunk', {}).get('messages', [])
                    if messages:
                        tool_response = messages[-1]
                        if isinstance(tool_response, ToolMessage):
                            print(f"Tool Message: {tool_response.content}")
                            try:
                                await websocket.send_json({"event": "tool_message", "data": str(tool_response.content)})
                            except Exception as e:
                                print(f"Error sending tool message: {e}")
                            continue

                ### AI message end from LangGraph
                elif event_type == 'on_chain_end' and event.get('name') == 'LangGraph':
                    messages = event.get('data', {}).get('output', {}).get('messages', [])
                    if messages:
                        last_message = messages[-1]
                        if isinstance(last_message, AIMessage) and last_message.content:
                            ai_message = last_message
                            print(f"AI Message complete: {ai_message.content[:60]}...")
                            try:
                                await websocket.send_json({"event": "ai_message", "data": ai_message.content})
                            except Exception as e:
                                print(f"Error sending AI message: {e}")

            # Non-blocking optional TTS notification (only if local text-to-speech container is active)
            if False:
                try:
                    requests.post("http://text-to-speech:5000/generate", json={"text": ai_message.content}, timeout=0.5)
                except Exception:
                    pass

            return ai_message.content if 'ai_message' in locals() else ""
        except Exception as e:
            print(f"Error in AI processing: {e}")
            err_msg = str(e)
            if "429" in err_msg:
                user_err = "⚠️ **Rate limit reached (HTTP 429)**: The Gemini API free quota for this minute was reached. Please wait ~30 seconds and try again!"
            elif "503" in err_msg:
                user_err = "⚠️ **Service Temporarily Busy (HTTP 503)**: Google's AI servers were briefly overloaded. Please retry your prompt in a few seconds!"
            else:
                user_err = f"⚠️ **Error**: {err_msg}"
            try:
                await websocket.send_json({"event": "ai_message", "data": user_err})
            except Exception:
                pass
            return str(e)
        except Exception as e:
            print(f"Error in AI processing: {e}")
            return str(e)