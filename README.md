# AETHER - Autonomous Multi-Agent AI Assistant

<div align="center">
  <img src="favicon.ico" width="120" alt="AETHER Logo" style="display: block; margin-left: auto; margin-right: auto; filter: drop-shadow(0 0 15px #6366f1);">
  <br>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-6366f1.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/framework-FastAPI%20%7C%20LangGraph-009688.svg" alt="Framework">
  <img src="https://img.shields.io/badge/LLM-Google%20Gemini%20%7C%20OpenAI-ff6f00.svg" alt="LLM">
</div>

---

## ⚡ Overview

**AETHER** (Autonomous Efficient Task & Heuristic Execution Routine) is an advanced, multi-agent AI assistant designed for autonomous task execution, real-time web intelligence, schedule management, and conversational interaction.

Built upon **LangGraph** and **FastAPI**, AETHER orchestrates specialized autonomous agents capable of making intelligent routing decisions, executing tools asynchronously, and streaming real-time tokens to a modern cyberpunk-inspired web interface.

---

## ✨ Features & Capabilities

- 🧠 **Multi-Agent Graph Orchestration**: Stateful agentic workflows built on LangGraph with automatic state persistence, loop prevention, and conditional routing.
- 🌐 **Live Web Intelligence**: Seamless real-time information retrieval powered by the Tavily Web Search API.
- 📅 **Google Calendar Integration**: Natural language calendar management—query upcoming schedules, view event details, and book new appointments.
- ⚡ **Low-Latency Streaming**: Real-time token streaming via FastAPIs WebSockets with automatic reconnection.
- 🔍 **Local RAG & Memory**: Contextual long-term retrieval and memory powered by FAISS vector search.
- 🎨 **Modern Cybernetic UI**: Clean, responsive interface with glowing avatar accents, Markdown rendering, auto-scrolling, and blank-input prevention.
- 💻 **Flexible LLM Provider**: Fully configured for Google Gemini (`gemini-flash-lite-latest`, `gemini-2.5-flash`) via Google's OpenAI-compatible API endpoint, as well as native OpenAI models.
- 🚀 **Zero-Docker Local Setup**: Runs natively on consumer hardware in lightweight Python 3.11+ without heavy GPU container overhead.

---

## 🏗️ Architecture

```
User Web Client (WebSocket)
          │
          ▼
   [FastAPI Server]
          │
          ▼
   [LangGraph Engine]
    ├── Jarvis Router Agent (Evaluates intent: Direct Response vs Tool Node)
    ├── Agent Decider (Dispatches to specialized agent)
    │     ├── Calendar Subgraph (Google Calendar API Read / Create)
    │     ├── Web Search Agent (Tavily API)
    │     └── Other Tools (RAG Search, File Reader, Image Generator)
    └── Response Generator (Streams formatted response back to UI)
```

---

## 🛠️ Quickstart Guide

### 1. Prerequisites
- **Python 3.11+** installed
- Google Gemini API Key (or OpenAI API Key)
- *(Optional)* Tavily API Key for live web search
- *(Optional)* Google Cloud Service Account (`credentials.json`) for Google Calendar

### 2. Clone and Setup Environment

```bash
git clone <your-repo-url>
cd aether
```

Create a virtual environment and install dependencies:

```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r core/requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file inside `core/` (or copy from `.env.example`):

```bash
cp .env.example core/.env
```

Edit `core/.env`:

```env
# Primary LLM API (Google Gemini or OpenAI)
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_gemini_api_key_here
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-flash-lite-latest

# Live Web Search
TAVILY_API_KEY=your_tavily_api_key_here

# Google Calendar (Service Account)
GOOGLE_AUTH_KEY=credentials.json
GOOGLE_CALENDAR_ID=your_email@gmail.com

PORT=3000
```

### 4. Run AETHER

```bash
cd core
python -m uvicorn main:app --host 0.0.0.0 --port 3000
```

Open your browser and navigate to:
**`http://localhost:3000`**

---

## 📂 Project Structure

```
├── core/
│   ├── ai_agents/              # LLM wrappers and WebSocket streaming handlers
│   ├── graph/                  # LangGraph state graphs and routing nodes
│   │   ├── subgraph/           # Specialized calendar subgraphs
│   │   ├── node.py             # Agent prompts, deciders, and tool routers
│   │   └── graphAgent.py       # Main state graph workflow
│   ├── static/                 # Modern web frontend (HTML/CSS/JS)
│   ├── tools/                  # Calendar, web search, file readers, and painters
│   ├── main.py                 # FastAPI application and WebSocket endpoints
│   ├── config.py               # Central environment and API configuration
│   └── requirements.txt        # Core Python dependencies
├── docs/                       # Architecture and developer guides
├── LICENSE                     # MIT License
└── README.md                   # Project documentation
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
