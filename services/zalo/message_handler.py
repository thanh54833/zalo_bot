import json
import logging
from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel
from zlapi import ZaloAPI
from zlapi.models import Message, ThreadType

from services.advisor import agent_advisor

logger = logging.getLogger(__name__)

# Fallback response message
FALLBACK_RESPONSE = "Xin chào! Bạn có thể liên hệ đến sđt: 0358380646 để nhận được trợ giúp"


class MessageData(BaseModel):
    """Data model for Zalo messages"""
    mid: str
    author_id: str
    message: str
    thread_id: str
    thread_type: str
    timestamp: datetime


class ZaloMessageHandler:
    """Handles processing and responding to incoming Zalo messages"""

    def __init__(self, bot_instance: ZaloAPI):
        self.bot = bot_instance

    def process_message(self, message_data: MessageData) -> Optional[str]:
        """Process incoming message and return response if needed"""
        try:
            logger.info(f"Processing message: {message_data.message} from {message_data.author_id}")

            return self.handle_normal_message(message_data)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return FALLBACK_RESPONSE

    def handle_normal_message(self, message_data: MessageData) -> str:
        """Handle non-command messages by invoking the agent."""
        try:
            logger.info(f"Invoking agent_advisor for message: {message_data.message}")

            # Prepare the input for the agent
            agent_input = {
                "messages": [{"role": "user", "content": message_data.message}]
            }

            # Invoke the agent
            response = agent_advisor.invoke(agent_input)

            # Extract the agent's final response
            agent_response = response.get("output", "")

            if not agent_response:
                logger.warning("Agent returned an empty response.")
                return FALLBACK_RESPONSE

            return agent_response

        except Exception as e:
            logger.error(f"Error invoking agent_advisor: {e}")
            return FALLBACK_RESPONSE

    def send_response(self, response: str, thread_id: str, thread_type: str) -> None:
        """Send response message back to Zalo"""
        try:
            if response:
                message = Message(text=response)
                self.bot.send(message, thread_id, ThreadType.USER)
                logger.info(f"Sent response: {response}")

        except Exception as e:
            logger.error(f"Error sending response: {e}")
            try:
                message = Message(text=FALLBACK_RESPONSE)
                self.bot.send(message, thread_id, ThreadType.USER)
                logger.info("Sent fallback response")
            except Exception as e2:
                logger.error(f"Error sending fallback response: {e2}")
