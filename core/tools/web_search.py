import os
import dotenv
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool

dotenv.load_dotenv()

@tool
def web_search(user_query: str) -> str:
    """
    Use this tool to search the live web for real-time information such as news, weather, facts, and updates.
    
    Args:
        user_query: The query string to search the web for.
    """
    tavily_key = os.getenv("TAVILY_API_KEY")
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")

    # 1. Primary: Tavily AI Search Engine
    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            search_result = client.search(user_query, max_results=5, search_depth="basic")
            results = search_result.get("results", [])
            if not results:
                return f"No web search results found for: {user_query}"
            
            formatted = []
            for r in results:
                title = r.get("title", "")
                snippet = r.get("content", "")
                url = r.get("url", "")
                formatted.append(f"• **{title}**\n  {snippet}\n  [Source]({url})")
            return "\n\n".join(formatted)
        except Exception as e:
            print(f"Tavily search error: {e}")

    # 2. Secondary: Perplexity API
    if perplexity_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=perplexity_key, base_url="https://api.perplexity.ai")
            response = client.chat.completions.create(
                model="llama-3.1-sonar-large-128k-online",
                messages=[{"role": "user", "content": user_query}],
                temperature=0.0,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Perplexity search error: {e}")

    return f"Unable to perform web search: Please ensure TAVILY_API_KEY is configured in your .env file."

def get_tool() -> StructuredTool:
    return web_search
