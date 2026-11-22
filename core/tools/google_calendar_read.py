import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from langchain_core.tools.structured import StructuredTool
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config import get_calendar_service, GOOGLE_CALENDAR_ID

from typing import Optional

load_dotenv()

class read_calendar_events_parameters(BaseModel):   
    time_min: Optional[str] = Field(
        default=None,
        description="Start time to fetch events from in ISO format (YYYY-MM-DDTHH:MM:SS). Defaults to current time if omitted.",
        example="2026-11-23T00:00:00"
    )
    time_max: Optional[str] = Field(
        default=None,
        description="End time to fetch events until in ISO format (YYYY-MM-DDTHH:MM:SS). Defaults to 30 days from now if omitted.",
        example="2026-12-23T23:59:59"
    )
    maxResults: int = Field(
        default=10,
        description="Maximum number of events to fetch",
        example=10
    )

@tool("read_calendar_events", args_schema=read_calendar_events_parameters)
def read_calendar_events(time_min: Optional[str] = None, time_max: Optional[str] = None, maxResults: int = 10) -> str:
    """
    Use this tool to read upcoming events from Google Calendar. No parameters required to check upcoming events in the next month.
    """
    service = get_calendar_service()

    now = datetime.now(timezone.utc)
    if not time_min:
        dt_min = now
    else:
        try:
            clean_min = time_min.strip().replace("Z", "+00:00")
            dt_min = datetime.fromisoformat(clean_min)
        except Exception:
            try:
                dt_min = datetime.strptime(time_min[:19], '%Y-%m-%dT%H:%M:%S')
            except Exception:
                dt_min = now

    if not time_max:
        dt_max = dt_min + timedelta(days=30)
    else:
        try:
            clean_max = time_max.strip().replace("Z", "+00:00")
            dt_max = datetime.fromisoformat(clean_max)
        except Exception:
            try:
                dt_max = datetime.strptime(time_max[:19], '%Y-%m-%dT%H:%M:%S')
            except Exception:
                dt_max = dt_min + timedelta(days=30)

    if dt_min.tzinfo is None:
        dt_min = dt_min.replace(tzinfo=timezone.utc)
    if dt_max.tzinfo is None:
        dt_max = dt_max.replace(tzinfo=timezone.utc)

    formatted_time_min = dt_min.isoformat()
    formatted_time_max = dt_max.isoformat()

    events_result = service.events().list(
        calendarId=GOOGLE_CALENDAR_ID,
        timeMin=formatted_time_min,
        timeMax=formatted_time_max,
        maxResults=maxResults,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])

    if not events:
        return "No events found in the specified time range."
    
    formatted_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        event_details = (
            f"Event: {event['summary']}\n"
            f"Start: {start}\n"
            f"End: {end}\n"
            f"Location: {event.get('location', 'No location specified')}\n"
            f"Description: {event.get('description', 'No description provided')}\n"
            f"Link: {event.get('htmlLink', 'No link available')}\n"
        )
        formatted_events.append(event_details)
    
    return "\n".join(formatted_events)

def get_tool() -> StructuredTool:
    return read_calendar_events

if __name__ == "__main__":
    # Example usage
    now = datetime.now(timezone.utc)
    
    time_min = now.isoformat() 
    time_max = (now + timedelta(days=7)).isoformat()
    print(time_min, time_max)
    result = read_calendar_events(time_min, time_max)
    print(result)