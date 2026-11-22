/**
 * AETHER Voice Input — Web Speech Recognition API
 * Real-time Speech-to-Text directly inside the browser (Chrome / Edge / Safari).
 * Zero external servers, zero latency, no OpenAI Whisper port 3001 required.
 */

let recognition = null;
let isRecognizing = false;

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Speech Recognition API is not supported in this browser. Please use Chrome or Edge.");
        return null;
    }

    const reco = new SpeechRecognition();
    reco.continuous = false;         // Stop when user finishes speaking
    reco.interimResults = true;      // Real-time live transcript preview
    reco.lang = 'en-US';

    return reco;
}

function startRecording() {
    const voiceBtn = document.getElementById('voice_button');
    const inputField = document.getElementById('chat_input_text');

    if (!recognition) {
        recognition = initSpeechRecognition();
        if (!recognition) {
            alert("Voice input requires Google Chrome, Microsoft Edge, or a Web Speech-compatible browser.");
            return;
        }

        recognition.onstart = () => {
            isRecognizing = true;
            if (voiceBtn) {
                voiceBtn.classList.add('recording-active');
                voiceBtn.innerHTML = '🔴';
                voiceBtn.title = 'Listening... click to stop';
            }
            if (inputField) {
                inputField.placeholder = "Listening... Speak now...";
            }
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            if (inputField) {
                inputField.value = finalTranscript || interimTranscript;
            }
        };

        recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            stopRecordingUI();
            if (event.error === 'not-allowed') {
                alert("Microphone access was denied. Please allow microphone access in your browser settings to use voice input.");
            }
        };

        recognition.onend = () => {
            stopRecordingUI();
        };
    }

    if (isRecognizing) {
        try {
            recognition.stop();
        } catch (e) {}
        stopRecordingUI();
    } else {
        try {
            recognition.start();
        } catch (e) {
            console.warn("Recognition already started or error:", e);
        }
    }
}

function stopRecordingUI() {
    isRecognizing = false;
    const voiceBtn = document.getElementById('voice_button');
    const inputField = document.getElementById('chat_input_text');

    if (voiceBtn) {
        voiceBtn.classList.remove('recording-active');
        voiceBtn.innerHTML = '🎤';
        voiceBtn.title = 'Voice Input';
    }
    if (inputField) {
        inputField.placeholder = "Send a command or query to Aether...";
        inputField.focus();
    }
}
