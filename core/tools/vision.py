from openai import OpenAI
import os
import base64

import config
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool

@tool
def vision(user_text: str, file_path: str):
    """
    Use this tool to generate a response based on an image url and user text.
    Return a message that uses BOTH the user text and the image url.
    """

    #Only for URL / online images
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url","image_url": {"url": file_path}}
            ]
        }
    ]


    #TODO: Add support for local images
    

    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash") if base_url else "gpt-4o"
    client = OpenAI(api_key=config.OPENAI_API_KEY or "dummy", base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        # temperature=0.0,
    )
    message = response.choices[0].message.content

    return message

def get_tool() -> StructuredTool:
    return vision