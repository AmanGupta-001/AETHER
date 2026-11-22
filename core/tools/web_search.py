from openai import OpenAI
import dotenv
import config
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool

dotenv.load_dotenv()

@tool
def web_search(user_query):
    """
    Use this tool to search the web for information. user_query must be a string.
    Never specify the date, year or any other specific time information unless the user specifies it.

    Args:
        user_query: The query(string) to search for.
    """
    
    messages = [
        {
            "role": "user",
            "content": user_query,
        },
    ]

    client = OpenAI(api_key=config.PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="llama-3.1-sonar-large-128k-online",
        messages=messages,
        temperature=0.0,
    )
    
    message = response.choices[0].message.content

    return message

def get_tool() -> StructuredTool:
    return web_search