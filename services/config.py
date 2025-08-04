import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LangSmith configuration
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "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")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "zalo_bot")

# Set environment variables for LangSmith
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

# Initialize LangSmith client if API key is available
langsmith_client = None
is_langsmith_configured = False  # Initialize the flag

if os.getenv("LANGCHAIN_API_KEY"):
    try:
        from langsmith import Client

        langsmith_client = Client()
        is_langsmith_configured = True  # Set to True if initialization succeeds
        print("✅ LangSmith client initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing LangSmith client: {e}")
