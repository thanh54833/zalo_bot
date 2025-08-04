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


class BaseCommand:
    """Base class for command handlers"""

    def __init__(self, bot_instance: ZaloAPI):
        self.bot = bot_instance

    def execute(self, message_data: MessageData, args: List[str]) -> str:
        """Execute the command"""
        raise NotImplementedError


class HelpCommand(BaseCommand):
    """Handler for !help command"""

    def execute(self, message_data: MessageData, args: List[str]) -> str:
        commands = {
            "help": "Show this help message",
            "echo": "Echo back your message",
            "info": "Show information about the current chat"
        }
        help_text = "Available commands:\n"
        for cmd, desc in commands.items():
            help_text += f"!{cmd}: {desc}\n"
        return help_text


class EchoCommand(BaseCommand):
    """Handler for !echo command"""

    def execute(self, message_data: MessageData, args: List[str]) -> str:
        return " ".join(args) if args else "Echo what?"


class InfoCommand(BaseCommand):
    """Handler for !info command"""

    def execute(self, message_data: MessageData, args: List[str]) -> str:
        return json.dumps({
            "thread_id": message_data.thread_id,
            "thread_type": message_data.thread_type,
            "author_id": message_data.author_id,
            "timestamp": message_data.timestamp.isoformat()
        }, indent=2)


class ZaloMessageHandler:
    """Handles processing and responding to incoming Zalo messages"""

    def __init__(self, bot_instance: ZaloAPI):
        self.bot = bot_instance
        # Initialize command handlers
        self.commands: Dict[str, BaseCommand] = {
            "help": HelpCommand(bot_instance),
            "echo": EchoCommand(bot_instance),
            "info": InfoCommand(bot_instance),
        }

    def process_message(self, message_data: MessageData) -> Optional[str]:
        """Process incoming message and return response if needed"""
        try:
            logger.info(f"Processing message: {message_data.message} from {message_data.author_id}")

            if message_data.message.startswith("!"):
                return self.handle_command(message_data)

            return self.handle_normal_message(message_data)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return FALLBACK_RESPONSE

    def handle_command(self, message_data: MessageData) -> Optional[str]:
        """Handle command messages (starting with !)"""
        try:
            parts = message_data.message[1:].split()
            if not parts:
                return "Please specify a command after '!'."

            command = parts[0].lower()
            args = parts[1:]

            if command in self.commands:
                return self.commands[command].execute(message_data, args)

            return f"Unknown command: {command}. Type !help for available commands."

        except Exception as e:
            logger.error(f"Error handling command: {e}")
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
            agent_response = ""
            if response and 'messages' in response and response['messages']:
                last_message = response['messages'][-1]
                if hasattr(last_message, 'content'):
                    agent_response = last_message.content

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
