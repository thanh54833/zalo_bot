import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import threading

from zlapi import ZaloAPI
from services.app_settings import config_manager
from .message_handler import MessageData, ZaloMessageHandler

logger = logging.getLogger(__name__)

class ZaloBot(ZaloAPI):
    """Custom Zalo bot implementation with message handling"""

    def __init__(self, phone: str, password: str, imei: str, cookies: dict):
        """Initialize the ZaloBot but don't connect yet"""
        # Store credentials without connecting
        self.phone = phone
        self.password = password
        self.imei = imei
        self.cookies = cookies
        
        # Initialize other attributes
        self.message_handler = None
        self.last_activity = datetime.now()
        self.is_enabled = config_manager.settings.zalo_config.personal.enabled
        self.is_connected = False
        self.listen_thread = None
        
        logger.info(f"ZaloBot instance created (not connected). Enabled: {self.is_enabled}")
        
        # Only connect if enabled
        if self.is_enabled:
            self.connect()
    
    def connect(self) -> bool:
        """Connect to Zalo and initialize message handler"""
        if self.is_connected:
            logger.info("ZaloBot is already connected")
            return True
            
        try:
            # Initialize the parent class (ZaloAPI) with credentials
            super().__init__(self.phone, self.password, imei=self.imei, cookies=self.cookies)
            
            # Initialize message handler
            self.message_handler = ZaloMessageHandler(self)
            self.is_connected = True
            logger.info(f"ZaloBot connected successfully with phone: {self.phone}")
            return True
        except Exception as e:
            logger.error(f"Error connecting ZaloBot: {e}")
            self.is_connected = False
            return False

    def start_listening(self) -> bool:
        """Start listening for messages in a background thread"""
        if not self.is_enabled:
            logger.warning("Cannot start listening: ZaloBot is disabled")
            return False
            
        if not self.is_connected:
            logger.warning("Cannot start listening: ZaloBot is not connected")
            if not self.connect():
                return False
        
        if self.listen_thread and self.listen_thread.is_alive():
            logger.info("ZaloBot is already listening")
            return True
            
        try:
            # Create and start the listening thread
            self.listen_thread = threading.Thread(target=self.listen, daemon=True)
            self.listen_thread.start()
            logger.info("ZaloBot started listening in background thread")
            return True
        except Exception as e:
            logger.error(f"Error starting ZaloBot listening thread: {e}")
            return False

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        """Handles incoming messages and processes them through MessageHandler"""
        
        # Skip processing if bot is disabled
        if not self.is_enabled or not self.is_connected:
            logger.info("ZaloBot is disabled or not connected. Ignoring incoming message.")
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
                if self.message_handler:
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
        if not self.is_enabled or not self.is_connected:
            logger.info("ZaloBot is disabled or not connected. Ignoring incoming event.")
            return
            
        logger.info(f"Received event type: {event_type}")
        # Add event handling logic here if needed
    
    def disconnect(self) -> bool:
        """Disconnect from Zalo and clean up resources"""
        try:
            if self.is_connected:
                # Logout from Zalo
                self.logout()
                self.is_connected = False
                logger.info("ZaloBot disconnected and logged out successfully")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting ZaloBot: {e}")
            return False
        
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
            logger.info("ZaloBot was enabled. Connecting and starting...")
            try:
                # Connect to Zalo
                if self.connect():
                    # Start listening
                    self.start_listening()
            except Exception as e:
                logger.error(f"Error enabling ZaloBot: {e}")
        else:
            # Bot was disabled
            logger.info("ZaloBot was disabled. Disconnecting...")
            try:
                # Disconnect and clean up
                self.disconnect()
            except Exception as e:
                logger.error(f"Error disabling ZaloBot: {e}")
                
    def reconnect(self):
        """Reconnect to Zalo if needed"""
        try:
            # Get the latest credentials from config
            cfg = config_manager.settings.zalo_config.personal
            
            # Update our credentials
            self.phone = cfg.phone
            self.password = cfg.password
            self.imei = cfg.imei
            if cfg.cookies:
                self.cookies = cfg.cookies
            
            # Disconnect if already connected
            if self.is_connected:
                self.disconnect()
                
            # Connect with new credentials
            success = self.connect()
            
            if success:
                # Start listening again
                self.start_listening()
                
            return success
        except Exception as e:
            logger.error(f"Error reconnecting ZaloBot: {e}")
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the bot"""
        return {
            "enabled": self.is_enabled,
            "connected": self.is_connected,
            "listening": self.listen_thread is not None and self.listen_thread.is_alive(),
            "last_activity": self.last_activity.isoformat() if hasattr(self, 'last_activity') else None
        }
