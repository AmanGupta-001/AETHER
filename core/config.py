import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("jarvis")

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not OPENAI_API_KEY and GEMINI_API_KEY:
    OPENAI_API_KEY = GEMINI_API_KEY
    os.environ["OPENAI_API_KEY"] = GEMINI_API_KEY
    if "OPENAI_BASE_URL" not in os.environ:
        os.environ["OPENAI_BASE_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai/"

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# LLM streaming configuration
STREAM_ENABLED = True
STREAM_OPTIONS = {"include_usage": True}

# configure phoenix otel (only when explicitly enabled, e.g. in full Docker environment)
if os.getenv("ENABLE_PHOENIX", "false").lower() == "true":
    try:
        os.environ['PHOENIX_PROJECT_NAME'] = "Jarvis"
        tracer_provider = register(
            endpoint=os.getenv("PHOENIX_ENDPOINT", "http://phoenix:4317"),
            auto_instrument=True,
        ) 
        LangChainInstrumentor().instrument()
    except Exception as e:
        logger.warning(f"Could not connect to Phoenix: {e}")

if __name__ == "__main__":
    print(f"[INFO] OPENAI_API_KEY: {OPENAI_API_KEY}")

# Google Calendar configuration
_local_creds = Path(__file__).resolve().parent / "credentials.json"
_raw_auth_key = os.getenv("GOOGLE_AUTH_KEY", "credentials.json")
if _local_creds.exists():
    GOOGLE_AUTH_KEY = str(_local_creds)
elif _raw_auth_key and not os.path.isabs(_raw_auth_key):
    GOOGLE_AUTH_KEY = str(Path(__file__).resolve().parent / _raw_auth_key)
else:
    GOOGLE_AUTH_KEY = _raw_auth_key
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

# Google Calendar Service function
def get_calendar_service():
    logger.info(f"Initializing Google Calendar service with auth key path: {GOOGLE_AUTH_KEY}")
    
    # Check if the credentials file exists
    creds_file = Path(GOOGLE_AUTH_KEY)
    if not creds_file.exists():
        error_msg = f"Google Calendar credentials file not found at: {GOOGLE_AUTH_KEY}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    logger.info("Google Calendar credentials file found")
    
    try:
        creds = Credentials.from_service_account_file(
            GOOGLE_AUTH_KEY, scopes=GOOGLE_CALENDAR_SCOPES
        )
        logger.info("Google Calendar credentials loaded successfully")
        
        service = build("calendar", "v3", credentials=creds)
        logger.info("Google Calendar service created successfully")
        
        return service
    except Exception as e:
        logger.error(f"Failed to initialize Google Calendar service: {str(e)}")
        raise


