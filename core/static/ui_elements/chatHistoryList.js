console.log("Chat history module loaded...")

// ── Chat History Sidebar ──────────────────────────────────────────────────────

// Renders the static shell (header + new-chat button). Items are injected by loadChatHistory().
let chatHistoryList = () => {
    return /*html*/ `
        <div id="chatHistoryList">
            <div class="chatHistoryHeader">
                <h3 class="russo-one-regular sidebar-title">Chat history</h3>
                <button id="newChatBtn" onclick="startNewChat()" title="New conversation">＋ New Chat</button>
            </div>
            <div id="chatSessionList"></div>
        </div>
    `;
};

// Fetch sessions from server and render them in the sidebar.
async function loadChatHistory() {
    try {
        const res = await fetch('/api/sessions');
        const sessions = await res.json();   // [{session_id, title, preview, updated_at}]
        renderChatHistory(sessions);
    } catch (e) {
        console.warn("Could not load chat history:", e);
        renderChatHistory([]);
    }
}

function renderChatHistory(sessions) {
    const container = document.getElementById("chatSessionList");
    if (!container) return;

    if (!sessions || sessions.length === 0) {
        container.innerHTML = `<p class="no-sessions-hint">No previous chats yet.<br>Start typing below!</p>`;
        return;
    }

    container.innerHTML = sessions.map(s => {
        const isActive = s.session_id === session_id;
        return /*html*/`
            <div class="historicalChatThumbnail ${isActive ? 'activeChatSession' : ''}"
                 onclick="switchToSession('${s.session_id}')"
                 data-session="${s.session_id}">
                <h3 class="chatThumbnailHeading">${escapeHtml(s.title)}</h3>
                <p>${escapeHtml(s.preview)}</p>
            </div>
        `;
    }).join('');
}

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text || '';
    return d.innerHTML;
}

// Start a brand-new chat session
function startNewChat() {
    // Clear the visible chat
    document.getElementById("chat_history").innerHTML = "";
    // Generate a new session id and reconnect WebSocket
    localStorage.removeItem('jarvis_session_id');
    session_id = getSessionId();
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();          // triggers onclose → reconnect with new session_id
    } else {
        connectWebSocket();
    }
    // Highlight nothing while loading
    document.querySelectorAll('.historicalChatThumbnail').forEach(el => el.classList.remove('activeChatSession'));
}

// Switch to an existing session
function switchToSession(targetSessionId) {
    if (targetSessionId === session_id) return;
    // Clear current chat view
    document.getElementById("chat_history").innerHTML = "";
    // Store target id and reconnect
    localStorage.setItem('jarvis_session_id', targetSessionId);
    session_id = targetSessionId;
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    } else {
        connectWebSocket();
    }
    // Highlight active
    document.querySelectorAll('.historicalChatThumbnail').forEach(el => {
        el.classList.toggle('activeChatSession', el.dataset.session === targetSessionId);
    });
}