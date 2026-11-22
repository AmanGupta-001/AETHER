"""
Gmail Read Tool — reads recent emails from the user's Gmail inbox.
Uses OAuth2 token stored at core/gmail_token.json.
"""

import os
import json
import base64
import re
from pathlib import Path
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional

TOKEN_PATH = Path(__file__).resolve().parent.parent / "gmail_token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _get_gmail_service():
    """Return an authenticated Gmail API service, or raise if not connected."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not TOKEN_PATH.exists():
        raise RuntimeError(
            "Gmail is not connected yet. Please open http://localhost:3000/gmail/auth "
            "in your browser to link your Gmail account."
        )
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
        else:
            raise RuntimeError(
                "Gmail token expired. Please re-authorise at http://localhost:3000/gmail/auth"
            )
    return build("gmail", "v1", credentials=creds)


def _decode_body(payload) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = _decode_body(part)
        if result:
            return result
    return ""


class ReadGmailParams(BaseModel):
    max_emails: int = Field(default=5, description="Maximum number of recent emails to fetch (1-20).")
    query: Optional[str] = Field(
        default=None,
        description="Gmail search query (e.g. 'from:boss@company.com', 'is:unread', 'subject:invoice'). Leave empty for latest inbox emails."
    )


@tool("read_gmail_emails", args_schema=ReadGmailParams)
def read_gmail_emails(max_emails: int = 5, query: Optional[str] = None) -> str:
    """
    Read recent emails from the user's Gmail inbox.
    Use this when the user asks about their emails, inbox, unread messages, or anything from Gmail.
    """
    try:
        service = _get_gmail_service()
    except RuntimeError as e:
        return str(e)

    q = query or "in:inbox"
    max_emails = max(1, min(max_emails, 20))

    results = service.users().messages().list(
        userId="me", q=q, maxResults=max_emails
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return "No emails found matching the criteria."

    output = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("Subject", "(no subject)")
        sender  = headers.get("From", "unknown")
        date    = headers.get("Date", "unknown")
        snippet = msg.get("snippet", "")

        body = _decode_body(msg.get("payload", {}))
        # Trim body to avoid token overflow
        body_preview = body[:300].strip() if body else snippet[:300]
        # Clean up whitespace
        body_preview = re.sub(r'\s+', ' ', body_preview)

        output.append(
            f"📧 From: {sender}\n"
            f"   Date: {date}\n"
            f"   Subject: {subject}\n"
            f"   Preview: {body_preview}"
        )

    return "\n\n".join(output)


def get_tool() -> StructuredTool:
    return read_gmail_emails

