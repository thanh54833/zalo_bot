import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LangSmith configuration
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "lsv2_pt_8390b2e1eea14d7e9a84d80a5e0467a5_149781903")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "zalo_bot")

# Set environment variables for LangSmith
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

# Check if LangSmith is properly configured
def is_langsmith_configured():
    if not LANGCHAIN_API_KEY:
        logger.warning("LANGCHAIN_API_KEY is not set. LangSmith tracing will be disabled.")
        return False
    return True

# Log configuration status
if is_langsmith_configured():
    logger.info(f"LangSmith configured with project: {LANGCHAIN_PROJECT}")
else:
    logger.warning("LangSmith not properly configured. Check your environment variables.") 