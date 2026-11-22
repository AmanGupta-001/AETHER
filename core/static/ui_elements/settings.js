/*
    The settings page that pops up when you press the settings icon.
*/

let settingsPage = async () => {
    let settingsElement = document.getElementById("settingsPage");
    if (settingsElement.style.display == "block") {
        settingsElement.style.display = "none";
    } else {
        settingsElement.style.display = "block";
        await loadSettingsContent();
    }
}

async function loadSettingsContent() {
    const el = document.getElementById("settingsPage");

    // Check Gmail status
    let gmailHtml = `<div class="settings-loading">Checking Gmail status...</div>`;
    el.innerHTML = `<h2 class="russo-one-regular settings-heading">⚙️ Settings</h2>${gmailHtml}`;

    try {
        const res = await fetch('/gmail/status');
        const data = await res.json();

        const gmailSection = data.connected
            ? `<div class="settings-integration connected">
                <span class="int-icon">✉️</span>
                <div class="int-info">
                    <strong>Gmail</strong>
                    <span class="int-status connected-label">● Connected as ${data.email || 'your account'}</span>
                </div>
                <button class="int-btn disconnect-btn" onclick="disconnectGmail()">Disconnect</button>
               </div>`
            : `<div class="settings-integration">
                <span class="int-icon">✉️</span>
                <div class="int-info">
                    <strong>Gmail</strong>
                    <span class="int-status">Not connected</span>
                </div>
                <button class="int-btn connect-btn" onclick="window.open('/gmail/auth','_blank','width=600,height=700'); setTimeout(loadSettingsContent, 4000)">Connect Gmail</button>
               </div>`;

        el.innerHTML = `
            <button class="settings-close" onclick="settingsPage()">✕</button>
            <h2 class="russo-one-regular settings-heading">⚙️ Settings</h2>
            <div class="settings-section">
                <h4 class="settings-section-title">🔗 Integrations</h4>
                ${gmailSection}
                <div class="settings-integration connected">
                    <span class="int-icon">📅</span>
                    <div class="int-info">
                        <strong>Google Calendar</strong>
                        <span class="int-status connected-label">● Connected (service account)</span>
                    </div>
                </div>
            </div>
            <div class="settings-section">
                <h4 class="settings-section-title">ℹ️ About</h4>
                <p class="settings-about">AETHER — AI Personal Assistant<br>
                Powered by Gemini &amp; LangGraph</p>
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<button class="settings-close" onclick="settingsPage()">✕</button>
            <h2 class="russo-one-regular settings-heading">⚙️ Settings</h2>
            <p style="color:#888;padding:16px">Could not load settings. Is the server running?</p>`;
    }
}

async function disconnectGmail() {
    await fetch('/gmail/disconnect', { method: 'POST' });
    await loadSettingsContent();
}