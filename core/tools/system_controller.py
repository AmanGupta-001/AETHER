import os
import subprocess
import ctypes
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional

# Windows Virtual-Key Codes for Media & Audio
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

def _press_key(vk_code: int, repeat: int = 1):
    """Simulate a Windows key press and release."""
    for _ in range(repeat):
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)

# Common App Aliases mapped to executables or protocols
APP_MAP = {
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "spotify": "spotify",
    "vscode": "code",
    "code": "code",
    "cmd": "cmd.exe",
    "terminal": "powershell.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "settings": "ms-settings:",
}

# Common Folder Aliases
USER_PROFILE = os.environ.get("USERPROFILE", r"C:\Users\mrmad")
FOLDER_MAP = {
    "downloads": os.path.join(USER_PROFILE, "Downloads"),
    "download": os.path.join(USER_PROFILE, "Downloads"),
    "documents": os.path.join(USER_PROFILE, "Documents"),
    "desktop": os.path.join(USER_PROFILE, "Desktop"),
    "pictures": os.path.join(USER_PROFILE, "Pictures"),
    "videos": os.path.join(USER_PROFILE, "Videos"),
    "music": os.path.join(USER_PROFILE, "Music"),
}

class SystemControlInput(BaseModel):
    action: str = Field(
        description="The action type: 'open_app', 'open_folder', 'media_control', or 'lock_pc'."
    )
    target: Optional[str] = Field(
        default=None,
        description="For 'open_app': application name (e.g. 'calculator', 'notepad', 'spotify', 'vscode', 'settings'). For 'open_folder': folder name or path (e.g. 'downloads', 'desktop', 'documents'). For 'media_control': 'play_pause', 'mute', 'volume_up', 'volume_down', 'next_track', 'prev_track'."
    )

@tool("system_controller", args_schema=SystemControlInput)
def system_controller(action: str, target: Optional[str] = None) -> str:
    """
    Perform safe, controlled OS actions on the user's laptop:
    - Open desktop applications (Calculator, Notepad, Spotify, VS Code, Paint, Task Manager, Settings)
    - Open user folders in Windows Explorer (Downloads, Desktop, Documents, Pictures)
    - Control system volume and media playback (Play/Pause, Mute/Unmute, Volume Up, Volume Down, Next Track)
    - Lock the laptop screen
    """
    act = (action or "").lower().strip()
    tgt = (target or "").lower().strip()

    try:
        # 1. Open Application
        if act in ("open_app", "app", "launch_app"):
            app_target = APP_MAP.get(tgt, tgt)
            if app_target.startswith("ms-"):
                os.startfile(app_target)
            else:
                subprocess.Popen(app_target, shell=True)
            return f"✅ Launched **{target}** successfully!"

        # 2. Open Folder in Explorer
        if act in ("open_folder", "folder", "open_directory"):
            folder_path = FOLDER_MAP.get(tgt)
            if not folder_path and os.path.exists(target):
                folder_path = target
            
            if folder_path and os.path.exists(folder_path):
                os.startfile(folder_path)
                return f"📁 Opened **{target}** in Windows File Explorer: `{folder_path}`"
            else:
                return f"⚠️ Folder '{target}' was not found."

        # 3. Media & Volume Controls
        if act in ("media_control", "media", "volume", "audio"):
            if any(k in tgt for k in ("mute", "unmute", "silence")):
                _press_key(VK_VOLUME_MUTE)
                return "🔊 Toggled system mute/unmute."
            elif any(k in tgt for k in ("volume_up", "vol_up", "louder", "up", "increase")):
                _press_key(VK_VOLUME_UP, repeat=5)
                return "🔊 Volume increased (+10%)."
            elif any(k in tgt for k in ("volume_down", "vol_down", "quieter", "down", "decrease")):
                _press_key(VK_VOLUME_DOWN, repeat=5)
                return "🔉 Volume decreased (-10%)."
            elif any(k in tgt for k in ("play", "pause", "resume", "stop")):
                _press_key(VK_MEDIA_PLAY_PAUSE)
                return "⏯️ Toggled media Play/Pause."
            elif any(k in tgt for k in ("next", "skip")):
                _press_key(VK_MEDIA_NEXT_TRACK)
                return "⏭️ Skipped to next track."
            elif any(k in tgt for k in ("prev", "previous", "back")):
                _press_key(VK_MEDIA_PREV_TRACK)
                return "⏮️ Returned to previous track."
            else:
                return f"Unknown media control target: '{target}'. Options: play_pause, mute, volume_up, volume_down, next_track."

        # 4. Lock PC
        if act in ("lock_pc", "lock", "lock_screen"):
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "🔒 Laptop screen locked."

        return f"Action '{action}' is not supported. Supported actions: 'open_app', 'open_folder', 'media_control', 'lock_pc'."

    except Exception as e:
        return f"Error executing {action}: {str(e)}"

def get_tool() -> StructuredTool:
    return system_controller

