import os
import subprocess
import urllib.request
import urllib.parse
import re
import webbrowser
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional

class PlayMusicInput(BaseModel):
    query: Optional[str] = Field(
        default="chill lofi beats",
        description="The song name, artist, genre, or video to play on YouTube. Defaults to 'chill lofi beats' if unspecified."
    )

def _find_brave_path() -> Optional[str]:
    """Locate Brave browser on Windows."""
    candidates = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def _get_top_youtube_url(query: str) -> str:
    """Find the first matching YouTube video URL for a search query."""
    search_query = query.strip() if query and query.strip() else "chill lofi beats"
    search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_query)}"
    
    try:
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        html = urllib.request.urlopen(req, timeout=4).read().decode("utf-8", errors="ignore")
        # Extract the first video ID from watch?v=XXXXXXXXXXX
        video_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', html)
        if video_ids:
            return f"https://www.youtube.com/watch?v={video_ids[0]}"
    except Exception as e:
        print(f"Direct video fetch error: {e}")
        
    # Fallback to the search results page
    return search_url

@tool("play_music", args_schema=PlayMusicInput)
def play_music(query: Optional[str] = "chill lofi beats") -> str:
    """
    Play songs, music, lofi, or videos by opening YouTube in Brave Browser.
    Use this tool whenever the user asks to play music, play a song, play a video on YouTube, or listen to something.
    """
    song_query = (query or "chill lofi beats").strip()
    target_url = _get_top_youtube_url(song_query)
    brave_path = _find_brave_path()

    try:
        if brave_path:
            # Launch Brave detached
            subprocess.Popen([brave_path, target_url])
            browser_name = "Brave Browser"
        else:
            # Fallback to system default browser
            webbrowser.open(target_url)
            browser_name = "your default browser"

        return f"🎶 Playing **{song_query}** on YouTube in {browser_name}!\n\nLink: [Open in YouTube]({target_url})"
    except Exception as e:
        return f"Failed to launch browser: {str(e)}. Direct link: {target_url}"

def get_tool() -> StructuredTool:
    return play_music
