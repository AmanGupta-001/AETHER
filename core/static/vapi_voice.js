/**
 * AETHER — Vapi AI Real-Time Conversational Voice Module
 * Sub-500ms voice-to-voice with Deepgram STT, natural barge-in, and human speech.
 * Integrated with AETHER laptop tools: Google Calendar, YouTube Music, Hardware Monitor, System Controls.
 */

let vapiInstance = null;
let isVapiCallActive = false;
let vapiConfig = {
    publicKey: "be2354ea-73f2-4d78-b896-d6a2b3d43078",
    assistantId: "7ac7e51a-9080-424b-9004-78fa7bd31092"
};

// Dynamically load the Vapi Web SDK via ESM
let VapiModule = null;
async function loadVapiSDK() {
    if (!VapiModule) {
        try {
            const mod = await import("https://esm.sh/@vapi-ai/web");
            VapiModule = mod.default || mod;
        } catch (e) {
            console.error("Failed to load Vapi Web SDK from CDN:", e);
        }
    }
    return VapiModule;
}

// Fetch configured keys from backend
async function fetchVapiConfig() {
    try {
        const res = await fetch('/api/vapi/config');
        if (res.ok) {
            const data = await res.json();
            if (data.publicKey) vapiConfig.publicKey = data.publicKey;
            if (data.assistantId) vapiConfig.assistantId = data.assistantId;
        }
    } catch (e) {
        console.warn("Using fallback Vapi config:", e);
    }
}

// Build assistant overrides with system instructions and laptop function tools
function getAssistantOverrides() {
    return {
        model: {
            messages: [
                {
                    role: "system",
                    content: `You are AETHER (JARVIS Voice Mode), an elite autonomous multi-agent AI assistant created for Aman.
You have direct, immediate control over Aman's laptop and tools:
1. "check_calendar": Read upcoming Google Calendar events. When asked about meetings, schedule, or calendar events, ALWAYS call this tool immediately!
2. "play_music": Plays requested songs, artists, or genres on YouTube inside Brave browser.
3. "system_monitor": Checks real-time laptop hardware telemetry (CPU, RAM, NVIDIA RTX 3050 Laptop GPU, drive storage, battery, temperature).
4. "system_controller": Controls Windows applications (notepad, calc, spotify, vscode, paint, taskmgr), folders (downloads, documents, desktop), media keys (volume_up, volume_down, mute, play_pause), or locks the workstation.
5. "web_search": Searches the live web for up-to-date queries.

NEVER say you don't have access to the user's calendar, apps, or device. You DO have access through your client tools. Always trigger the appropriate tool function call immediately whenever requested.`
                }
            ],
            tools: [
                {
                    type: "function",
                    async: true,
                    function: {
                        name: "check_calendar",
                        description: "Fetches upcoming events and schedule from the user's Google Calendar.",
                        parameters: {
                            type: "object",
                            properties: {}
                        }
                    }
                },
                {
                    type: "function",
                    async: true,
                    function: {
                        name: "play_music",
                        description: "Plays a song, artist, album, or playlist on YouTube in Brave browser.",
                        parameters: {
                            type: "object",
                            properties: {
                                query: {
                                    type: "string",
                                    description: "Song title, artist, or music query, e.g. 'Starboy', 'Lofi hip hop beats', 'Coldplay'"
                                }
                            },
                            required: ["query"]
                        }
                    }
                },
                {
                    type: "function",
                    async: true,
                    function: {
                        name: "system_monitor",
                        description: "Retrieves live hardware telemetry: CPU load, RAM usage, NVIDIA RTX 3050 Laptop GPU, storage space, battery %, and temperatures.",
                        parameters: {
                            type: "object",
                            properties: {}
                        }
                    }
                },
                {
                    type: "function",
                    async: true,
                    function: {
                        name: "system_controller",
                        description: "Controls Windows apps (Notepad, Calculator, Spotify, VS Code, Paint, Task Manager), opens folders (Downloads, Documents, Desktop), controls media volume (volume_up, volume_down, mute), or locks the laptop.",
                        parameters: {
                            type: "object",
                            properties: {
                                action: {
                                    type: "string",
                                    description: "Action to take: 'launch_app', 'open_folder', 'media_control', 'lock_screen'"
                                },
                                target: {
                                    type: "string",
                                    description: "Target application name, folder name, or media key (e.g. 'notepad', 'calc', 'downloads', 'volume_up', 'mute')"
                                }
                            },
                            required: ["action"]
                        }
                    }
                },
                {
                    type: "function",
                    async: true,
                    function: {
                        name: "web_search",
                        description: "Performs live web search for real-time information, weather, or news.",
                        parameters: {
                            type: "object",
                            properties: {
                                query: {
                                    type: "string",
                                    description: "The search query"
                                }
                            },
                            required: ["query"]
                        }
                    }
                }
            ]
        }
    };
}

// Initialize Vapi client instance
async function getVapiClient() {
    if (!vapiInstance) {
        const Vapi = await loadVapiSDK();
        if (!Vapi) {
            throw new Error("Vapi SDK could not be loaded.");
        }
        await fetchVapiConfig();
        vapiInstance = new Vapi(vapiConfig.publicKey);
        setupVapiEventListeners(vapiInstance);
    }
    return vapiInstance;
}

function setupVapiEventListeners(vapi) {
    vapi.on("call-start", () => {
        isVapiCallActive = true;
        updateVoiceUIState(true);
        console.log("🎙️ Vapi JARVIS call started.");
    });

    vapi.on("speech-start", () => {
        const orb = document.getElementById("vapiVoiceButton");
        if (orb) orb.classList.add("orb-talking");
    });

    vapi.on("speech-end", () => {
        const orb = document.getElementById("vapiVoiceButton");
        if (orb) orb.classList.remove("orb-talking");
    });

    vapi.on("message", async (msg) => {
        if (!msg) return;

        // 1. Handle Tool Calls from Vapi (Calendar, Music, System, Hardware)
        if (msg.type === "tool-calls") {
            const toolCalls = msg.toolCallList || [];
            for (const tc of toolCalls) {
                const fn = tc.function || tc;
                const toolName = fn.name;
                let args = fn.arguments;
                if (typeof args === "string") {
                    try { args = JSON.parse(args); } catch(e) { args = {}; }
                }
                console.log(`⚡ Vapi triggered tool: ${toolName}`, args);

                try {
                    const res = await fetch("/api/tools/execute", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ tool_name: toolName, parameters: args || {} })
                    });
                    const data = await res.json();
                    const output = data.result || data.error || "Completed";

                    // Display tool execution in chat UI
                    const uuid = "vapi-tool-" + Date.now();
                    if (typeof addMessage === "function") {
                        addMessage(marked.parse(`⚙️ **Executed Tool: ${toolName}**\n\n${output}`), uuid);
                    }

                    // Feed tool result back to Vapi so the assistant speaks it to Aman
                    if (vapiInstance) {
                        vapiInstance.send({
                            type: "add-message",
                            message: {
                                role: "system",
                                content: `Tool '${toolName}' executed on Aman's laptop. Result:\n${output}\n\nNow concisely and naturally speak this result to Aman.`
                            }
                        });
                    }
                } catch (err) {
                    console.error("Tool execution failed:", err);
                }
            }
            return;
        }

        // 2. Render transcripts live into AETHER's chat stream
        if (msg.type === "transcript" && msg.transcriptType === "final") {
            const text = msg.transcript;
            if (!text) return;

            if (msg.role === "user") {
                if (typeof addUserMessage === "function") addUserMessage(marked.parse(text));
            } else if (msg.role === "assistant") {
                const uuid = typeof generateUUID === "function" ? generateUUID() : "vapi-" + Date.now();
                if (typeof addMessage === "function") addMessage(marked.parse(text), uuid);
            }

            const chatHistory = document.getElementById("chat_history");
            if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;
        }
    });

    vapi.on("call-end", () => {
        isVapiCallActive = false;
        updateVoiceUIState(false);
        console.log("🎙️ Vapi JARVIS call ended.");
    });

    vapi.on("error", (err) => {
        console.error("Vapi Voice Error:", err);
        isVapiCallActive = false;
        updateVoiceUIState(false);
    });
}

// Toggle start/stop Vapi call
async function toggleVapiCall() {
    try {
        const vapi = await getVapiClient();
        if (isVapiCallActive) {
            vapi.stop();
        } else {
            console.log("Starting Vapi call with Assistant:", vapiConfig.assistantId);
            const overrides = getAssistantOverrides();
            await vapi.start(vapiConfig.assistantId, overrides);
        }
    } catch (e) {
        console.error("Error toggling Vapi call:", e);
        alert("Could not start Vapi Voice Call. Please ensure microphone access is granted in your browser.");
        updateVoiceUIState(false);
    }
}

// Update UI elements to reflect active voice call
function updateVoiceUIState(isActive) {
    const orb = document.getElementById("vapiVoiceButton");
    const badgePill = document.querySelector(".badge-pill");
    const vapiBtn = document.getElementById("vapiCallBtn");

    if (isActive) {
        if (orb) {
            orb.classList.add("orb-calling");
            orb.title = "JARVIS Voice Active — Click to end call";
        }
        if (badgePill) {
            badgePill.classList.add("badge-active-voice");
            badgePill.innerHTML = `<span class="status-pulse-dot red-pulse"></span> JARVIS VOICE ACTIVE`;
        }
        if (vapiBtn) {
            vapiBtn.classList.add("btn-voice-active");
            vapiBtn.innerHTML = `<span>End Voice Call</span> 🔴`;
        }
    } else {
        if (orb) {
            orb.classList.remove("orb-calling", "orb-talking");
            orb.title = "Click to talk with AETHER (Vapi JARVIS Mode)";
        }
        if (badgePill) {
            badgePill.classList.remove("badge-active-voice");
            badgePill.innerHTML = `<span class="status-pulse-dot"></span> AUTONOMOUS MULTI-AGENT AI`;
        }
        if (vapiBtn) {
            vapiBtn.classList.remove("btn-voice-active");
            vapiBtn.innerHTML = `<span>Talk to JARVIS</span> 🎙️`;
        }
    }
}

// Attach globally
window.toggleVapiCall = toggleVapiCall;
window.isVapiCallActive = isVapiCallActive;
