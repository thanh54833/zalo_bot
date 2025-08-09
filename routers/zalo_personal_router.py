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

async def manage_zalo_personal_bot(should_be_enabled: bool):
    """
    Centralized function to manage the Zalo personal bot's state.
    Initializes or shuts down the bot based on the desired state.
    """
    bot = get_bot_instance()
    
    if should_be_enabled:
        if bot is None:
            logger.info("Zalo personal bot is not initialized. Initializing...")
            try:
                cfg = config_manager.settings.zalo_config.personal
                if not cfg.phone or not cfg.password:
                    logger.warning("Zalo personal bot credentials are not set. Cannot initialize.")
                    return
                
                new_bot = ZaloBot(
                    phone=cfg.phone,
                    password=cfg.password,
                    imei=cfg.imei,
                    cookies=cfg.cookies
                )
                set_bot_instance(new_bot)
                bot = new_bot
                logger.info(f"ZaloBot initialized with phone: {cfg.phone}")
            except Exception as e:
                logger.error(f"Error initializing ZaloBot: {e}")
                return

        if bot.is_connected:
            if not bot.listen_thread or bot.listen_thread.done():
                bot.start_listening()
        else:
            if bot.connect():
                bot.start_listening()

    else: # should_be_disabled
        if bot and bot.is_connected:
            logger.info("Disabling and disconnecting Zalo personal bot.")
            bot.disconnect()
            set_bot_instance(None)

@router.on_event("startup")
async def startup_event():
    """Initialize ZaloBot when the FastAPI application starts."""
    try:
        if config_manager.settings.zalo_config.personal.enabled:
            logger.info("Initializing ZaloBot for personal account integration...")
            await manage_zalo_personal_bot(should_be_enabled=True)
        else:
            logger.info("Zalo personal account integration is disabled. Not initializing ZaloBot.")
    except Exception as e:
        logger.error(f"Error initializing ZaloBot: {e}")

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
        logger.info("Restarting Zalo personal bot...")
        await manage_zalo_personal_bot(should_be_enabled=False) # Stop the old one
        await asyncio.sleep(1) # Give it a moment to release resources
        await manage_zalo_personal_bot(should_be_enabled=True)  # Start a new one
        return {"status": "restarted", "message": "ZaloBot has been restarted"}
    except Exception as e:
        logger.error(f"Error restarting ZaloBot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect")
async def connect_bot(enabled: bool = Depends(verify_personal_enabled)):
    """Connect the ZaloBot if it's not already connected"""
    bot = get_bot_instance()
    if not bot:
        logger.info("Bot not initialized, attempting to start it.")
        await manage_zalo_personal_bot(should_be_enabled=True)
        bot = get_bot_instance()
        if not bot:
            raise HTTPException(status_code=500, detail="Failed to initialize and connect ZaloBot")

    if not bot.is_connected:
        if not bot.connect():
            raise HTTPException(status_code=500, detail="Failed to connect ZaloBot")
    
    if not bot.listen_thread or bot.listen_thread.done():
        if not bot.start_listening():
            raise HTTPException(status_code=500, detail="Failed to start ZaloBot listening")
    
    return {"status": "connected", "message": "ZaloBot is now connected and listening"}

@router.post("/disconnect")
async def disconnect_bot():
    """Disconnect the ZaloBot"""
    bot = get_bot_instance()
    if not bot:
        return {"status": "not_initialized", "message": "ZaloBot has not been initialized"}
    
    await manage_zalo_personal_bot(should_be_enabled=False)
    
    if bot.is_connected:
        if bot.disconnect():
            return {"status": "disconnected", "message": "ZaloBot has been disconnected"}
        else:
            raise HTTPException(status_code=500, detail="Failed to disconnect ZaloBot")
    else:
        return {"status": "already_disconnected", "message": "ZaloBot was already disconnected"} 