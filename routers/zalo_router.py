import logging
import threading
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from services.zalo import ZaloBot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Zalo configuration
PHONE = "0559362614"
PASSWORD = "Lumia520"
IMEI = "2bd94c6b-f25c-418b-8e26-adb12c47086b-84fb6a68ab92a6d30981c69a1117885c"
COOKIES = {
    'zpw_sek': 'PHX8.442114449.a0.ztLU0MccDF3uXsxgIAOqy1A4KPjBd1Q40v4VY3sJ3PCpYMAK0j10g2FiK8aUcmdI5DqX-HRptY-RfsC4vyuqy0'
}

# Create router
router = APIRouter(
    prefix="/api/zalo",
    tags=["zalo"],
    responses={404: {"description": "Not found"}},
)

class BotStatus(BaseModel):
    status: str
    is_listening: bool
    last_activity: Optional[datetime] = None

# Global bot instance and state
bot_instance: Optional[ZaloBot] = None
bot_thread: Optional[threading.Thread] = None
bot_status = BotStatus(status="stopped", is_listening=False)

def run_bot():
    """Initializes and runs the Zalo bot in a blocking manner."""
    global bot_instance, bot_status
    try:
        # Prioritize cookie-based login
        if all(COOKIES.values()):
            bot_instance = ZaloBot(PHONE, "", imei=IMEI, cookies=COOKIES)
        else:
            bot_instance = ZaloBot(PHONE, PASSWORD, imei=IMEI)

        bot_status.status = "running"
        bot_status.is_listening = True
        logger.info("Starting Zalo bot...")
        bot_instance.listen()
    except Exception as e:
        logger.error(f"Bot error: {e}")
        bot_status.status = "error"
        bot_status.is_listening = False

def start_bot_thread():
    """Starts the bot in a new daemon thread."""
    global bot_thread
    if bot_thread is None or not bot_thread.is_alive():
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        return True
    return False

@router.on_event("startup")
async def startup_event():
    """Starts the bot when the FastAPI application starts."""
    logger.info("Starting FastAPI and Zalo bot...")
    start_bot_thread()

@router.on_event("shutdown")
async def shutdown_event():
    """Cleans up when the server shuts down."""
    global bot_instance
    if bot_instance:
        bot_instance.logout()
    logger.info("Zalo bot has been logged out.")

@router.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Zalo Bot API is running", "status": bot_status.dict()}

@router.get("/status")
async def get_status():
    """Gets the current status of the bot."""
    return bot_status.dict()

@router.post("/send-message")
async def send_message(message: str, thread_id: str, thread_type: str = "USER"):
    """Sends a message through the bot."""
    global bot_instance
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    try:
        from zlapi.models import Message, ThreadType
        tt = ThreadType.USER if thread_type.upper() == "USER" else ThreadType.GROUP
        msg = Message(text=message)
        result = bot_instance.send(msg, thread_id, tt)
        return {"success": True, "message": "Message sent successfully", "result": str(result)}
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restart-bot")
async def restart_bot():
    """Restarts the bot."""
    global bot_instance, bot_status
    try:
        if bot_instance:
            bot_instance.logout()

        bot_status.status = "restarting"
        bot_status.is_listening = False

        if start_bot_thread():
            return {"success": True, "message": "Bot restarting..."}
        else:
            return {"success": False, "message": "Bot is already running or restarting."}
    except Exception as e:
        logger.error(f"Error restarting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account-info")
async def get_account_info():
    """Gets the account information."""
    global bot_instance
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    try:
        info = bot_instance.fetchAccountInfo()
        return {"success": True, "account_info": info}
    except Exception as e:
        logger.error(f"Error fetching account info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
