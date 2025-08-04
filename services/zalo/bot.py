import logging
from datetime import datetime
from typing import Optional

from zlapi import ZaloAPI
from .message_handler import MessageData, ZaloMessageHandler

logger = logging.getLogger(__name__)

class ZaloBot(ZaloAPI):
    """Custom Zalo bot implementation with message handling"""

    def __init__(self, phone: str, password: str, imei: str, cookies: dict):
        super().__init__(phone, password, imei=imei, cookies=cookies)
        self.message_handler = ZaloMessageHandler(self)
        self.last_activity = datetime.now()

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        """Handles incoming messages and processes them through MessageHandler"""

        #print(f"Received message: {message} from {author_id} in thread {thread_id} of type {thread_type}")

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
        logger.info(f"Received event type: {event_type}")
        # Add event handling logic here if needed
