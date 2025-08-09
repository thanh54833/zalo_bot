import logging
import asyncio
from fastapi import APIRouter, HTTPException, Depends

from services.app_settings import config_manager
from services.zalo import ZaloBot, set_bot_instance, get_bot_instance

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/zalo-personal",
    tags=["zalo-personal"],
    responses={404: {"description": "Not found"}},
)

# Dependency to check if personal integration is enabled
async def verify_personal_enabled():
    if not config_manager.settings.zalo_config.personal.enabled:
        raise HTTPException(
            status_code=503,
            detail="Zalo personal integration is currently disabled"
        )
    return True

@router.on_event("startup")
async def startup_event():
    """Initialize ZaloBot when the FastAPI application starts."""
    try:
        # Only initialize if enabled in config
        if config_manager.settings.zalo_config.personal.enabled:
            logger.info("Initializing ZaloBot for personal account integration...")
            await initialize_bot()
        else:
            logger.info("Zalo personal account integration is disabled. Not initializing ZaloBot.")
    except Exception as e:
        logger.error(f"Error initializing ZaloBot: {e}")

async def initialize_bot():
    """Initialize the ZaloBot instance with configuration values."""
    try:
        # Get config
        cfg = config_manager.settings.zalo_config.personal
        
        # Create ZaloBot instance
        bot = ZaloBot(
            phone=cfg.phone,
            password=cfg.password,
            imei=cfg.imei,
            cookies=cfg.cookies
        )
        
        # Store the instance globally
        set_bot_instance(bot)
        logger.info(f"ZaloBot initialized with phone: {cfg.phone}")
        
        # Start listening if enabled
        if cfg.enabled and bot.is_connected:
            bot.start_listening()
        
        return bot
    except Exception as e:
        logger.error(f"Error initializing ZaloBot: {e}")
        return None

@router.get("/status")
async def get_status():
    """Get the current status of the Zalo personal integration"""
    bot = get_bot_instance()
    if not bot:
        return {
            "status": "not_initialized",
            "message": "ZaloBot has not been initialized"
        }
    
    # Use the bot's get_status method
    status = bot.get_status()
    status["config_enabled"] = config_manager.settings.zalo_config.personal.enabled
    
    return status

@router.post("/restart")
async def restart_bot(enabled: bool = Depends(verify_personal_enabled)):
    """Restart the ZaloBot"""
    try:
        # Get current instance
        bot = get_bot_instance()
        
        # Disconnect if exists
        if bot:
            try:
                bot.disconnect()
                logger.info("Disconnected existing ZaloBot instance")
            except:
                pass
        
        # Initialize new instance
        new_bot = await initialize_bot()
        if not new_bot:
            raise HTTPException(status_code=500, detail="Failed to initialize ZaloBot")
            
        return {"status": "restarted", "message": "ZaloBot has been restarted"}
    except Exception as e:
        logger.error(f"Error restarting ZaloBot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect")
async def connect_bot(enabled: bool = Depends(verify_personal_enabled)):
    """Connect the ZaloBot if it's not already connected"""
    bot = get_bot_instance()
    if not bot:
        # Initialize if not exists
        bot = await initialize_bot()
        if not bot:
            raise HTTPException(status_code=500, detail="Failed to initialize ZaloBot")
    
    # Connect if not connected
    if not bot.is_connected:
        if not bot.connect():
            raise HTTPException(status_code=500, detail="Failed to connect ZaloBot")
    
    # Start listening
    if not bot.start_listening():
        raise HTTPException(status_code=500, detail="Failed to start ZaloBot listening")
    
    return {"status": "connected", "message": "ZaloBot is now connected and listening"}

@router.post("/disconnect")
async def disconnect_bot():
    """Disconnect the ZaloBot"""
    bot = get_bot_instance()
    if not bot:
        return {"status": "not_initialized", "message": "ZaloBot has not been initialized"}
    
    if bot.is_connected:
        if bot.disconnect():
            return {"status": "disconnected", "message": "ZaloBot has been disconnected"}
        else:
            raise HTTPException(status_code=500, detail="Failed to disconnect ZaloBot")
    else:
        return {"status": "already_disconnected", "message": "ZaloBot was already disconnected"} 