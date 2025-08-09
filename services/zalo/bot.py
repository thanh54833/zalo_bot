import logging
import asyncio
from datetime import datetime
from typing import Optional

from zlapi import ZaloAPI
from services.app_settings import config_manager
from .message_handler import MessageData, ZaloMessageHandler

logger = logging.getLogger(__name__)

class ZaloBot(ZaloAPI):
    """Custom Zalo bot implementation with message handling"""

    def __init__(self, phone: str, password: str, imei: str, cookies: dict):
        super().__init__(phone, password, imei=imei, cookies=cookies)
        self.message_handler = ZaloMessageHandler(self)
        self.last_activity = datetime.now()
        # Check if personal account integration is enabled
        self.is_enabled = config_manager.settings.zalo_config.personal.enabled
        logger.info(f"ZaloBot personal account integration is {'enabled' if self.is_enabled else 'disabled'}")

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        """Handles incoming messages and processes them through MessageHandler"""
        
        # Skip processing if bot is disabled
        if not self.is_enabled:
            logger.info("ZaloBot is disabled. Ignoring incoming message.")
            return

        print("Message object:", message_object)
        # message_object.uidFrom !='0' là tin nhắn user gửi tới.
        if message_object.uidFrom !='0' :
            try:
                self.last_activity = datetime.now()

                # Create message data object
                message_data = MessageData(
                    mid=str(mid),
                    author_id=str(author_id),
                    message=str(message) if message else "",
                    thread_id=str(thread_id),
                    thread_type=str(thread_type),
                    timestamp=datetime.now()
                )
                
                # Process message synchronously since we're in a callback
                response = self.message_handler.process_message(message_data)
                if response:
                    self.message_handler.send_response(
                        response,
                        message_data.thread_id,
                        message_data.thread_type
                    )
                
            except Exception as e:
                logger.error(f"Error in onMessage: {e}")

    def onEvent(self, event_data, event_type):
        """Handle other Zalo events"""
        # Skip processing if bot is disabled
        if not self.is_enabled:
            logger.info("ZaloBot is disabled. Ignoring incoming event.")
            return
            
        logger.info(f"Received event type: {event_type}")
        # Add event handling logic here if needed
        
    async def handle_enabled_state_change(self, new_state: bool):
        """
        Handle changes to the enabled state
        
        Args:
            new_state: The new enabled state
        """
        if new_state == self.is_enabled:
            # No change
            return
            
        old_state = self.is_enabled
        self.is_enabled = new_state
        logger.info(f"ZaloBot enabled state changed: {old_state} -> {new_state}")
        
        if new_state:
            # Bot was enabled
            logger.info("ZaloBot was enabled. Reconnecting...")
            try:
                # Reconnect to Zalo
                self.reconnect()
                logger.info("ZaloBot reconnected successfully")
            except Exception as e:
                logger.error(f"Error reconnecting ZaloBot: {e}")
        else:
            # Bot was disabled
            logger.info("ZaloBot was disabled. Logging out...")
            try:
                # Logout to clean up resources
                self.logout()
                logger.info("ZaloBot logged out successfully")
            except Exception as e:
                logger.error(f"Error logging out ZaloBot: {e}")
                
    def reconnect(self):
        """Reconnect to Zalo if needed"""
        try:
            # Get the latest credentials from config
            cfg = config_manager.settings.zalo_config.personal
            
            # Update our credentials
            self.phone = cfg.phone
            self.password = cfg.password
            self.imei = cfg.imei
            
            # Attempt to reconnect
            if cfg.cookies and all(cfg.cookies.values()):
                # Use cookies if available
                self.cookies = cfg.cookies
                self.login_with_cookie()
            else:
                # Otherwise use password
                self.login()
                
            logger.info(f"ZaloBot reconnected with phone: {self.phone}")
            return True
        except Exception as e:
            logger.error(f"Error reconnecting ZaloBot: {e}")
            return False
