/**
 * AETHER — Vapi AI Real-Time Conversational Voice Module
 * Sub-500ms voice-to-voice with Deepgram STT, natural barge-in, and human speech.
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

    vapi.on("message", (msg) => {
        if (!msg) return;

        // Render transcripts live into AETHER's chat stream
        if (msg.type === "transcript" && msg.transcriptType === "final") {
            const text = msg.transcript;
            if (!text) return;

            if (msg.role === "user") {
                addUserMessage(marked.parse(text));
            } else if (msg.role === "assistant") {
                const uuid = typeof generateUUID === "function" ? generateUUID() : "vapi-" + Date.now();
                addMessage(marked.parse(text), uuid);
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
            await vapi.start(vapiConfig.assistantId);
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
