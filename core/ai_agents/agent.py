from langchain_openai import ChatOpenAI
from ai_agents.model import Model, LLMType
import os
import logging
from config import STREAM_ENABLED, STREAM_OPTIONS  # Add import for streaming config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Agent:
    temperature = 0
    max_tokens = 2048
    model: Model
    llm_type: LLMType
    
    # Model-specific configurations
    MODEL_CONFIGS = {
        "gpt-4o-mini": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "gpt-4o": {
            "max_tokens": 8192,
            "temperature": 0.7,
        },
        "gpt-3.5-turbo": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "o3-mini": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "o4-mini": {
            "temperature": 1,
        },
        "gpt-4-1-mini": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "gpt-4o-mini_": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        # Add more models as needed
    }

    def __init__(self, model: Model, override_temp: float = None):
        self.model = model
        self.override_temp = override_temp

    def get_llm(self):
        try:
            if self.model[1] == LLMType.chat_open_ai:
                model_name = self.model[0]
                
                # Check for API key
                api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
                if not api_key:
                    logger.error("No API key found (OPENAI_API_KEY, GEMINI_API_KEY, or GOOGLE_API_KEY)")
                    raise ValueError("Missing API key environment variable")

                base_url = os.environ.get("OPENAI_BASE_URL")
                is_gemini = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or (api_key and api_key.startswith("AIza")))
                if is_gemini and not base_url:
                    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

                if is_gemini:
                    # Map to Gemini model for compatibility
                    model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
                    logger.info(f"Using Gemini via OpenAI-compatible endpoint with model: {model_name}")
                else:
                    logger.info(f"Initializing ChatOpenAI with model: {model_name}")
                
                # Start with minimal required parameters
                params = {
                    "model": model_name,
                    "api_key": api_key,
                    "request_timeout": 30,
                    "max_retries": 5,
                    "streaming": STREAM_ENABLED,
                }

                if base_url:
                    params["base_url"] = base_url

                if not is_gemini:
                    params["stream_options"] = STREAM_OPTIONS
                
                # Apply model-specific parameters if available
                if not is_gemini and model_name in self.MODEL_CONFIGS:
                    model_params = self.MODEL_CONFIGS[model_name].copy()
                    params.update(model_params)
                    logger.info(f"Applied specific configuration for model: {model_name}")
                else:
                    params["temperature"] = self.temperature
                    logger.info(f"Using default temperature for {model_name}")
                
                # Apply temperature override if provided
                if self.override_temp is not None:
                    params["temperature"] = self.override_temp
                    logger.info(f"Overriding temperature with value: {self.override_temp}")
                
                logger.info(f"Initializing ChatOpenAI with parameters: {params}")
                self.llm = ChatOpenAI(**params)
                logger.info(f"ChatOpenAI initialized successfully")
            else:
                logger.error(f"Unsupported LLM type: {self.model[1]}")
                raise ValueError(f"Unsupported LLM type: {self.model[1]}")
                
            return self.llm
        except Exception as e:
            logger.error(f"Error initializing LLM: {str(e)}")
            raise



