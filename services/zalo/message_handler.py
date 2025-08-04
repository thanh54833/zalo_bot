import json
import logging
from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel
from zlapi import ZaloAPI
from zlapi.models import Message, ThreadType

logger = logging.getLogger(__name__)

# Default response message
DEFAULT_RESPONSE = "Xin chào! bạn có thể liên hệ đến sdt: 0358380646 để nhận được trợ giúp"

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
        help_text += f"\n{DEFAULT_RESPONSE}"
        return help_text

class EchoCommand(BaseCommand):
    """Handler for !echo command"""
    def execute(self, message_data: MessageData, args: List[str]) -> str:
        echo_response = " ".join(args) if args else "Echo what?"
        return f"{echo_response}\n\n{DEFAULT_RESPONSE}"

class InfoCommand(BaseCommand):
    """Handler for !info command"""
    def execute(self, message_data: MessageData, args: List[str]) -> str:
        info = json.dumps({
            "thread_id": message_data.thread_id,
            "thread_type": message_data.thread_type,
            "author_id": message_data.author_id,
            "timestamp": message_data.timestamp.isoformat()
        }, indent=2)
        return f"{info}\n\n{DEFAULT_RESPONSE}"

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
            return DEFAULT_RESPONSE  # Return default response even on error
            
    def handle_command(self, message_data: MessageData) -> Optional[str]:
        """Handle command messages (starting with !)"""
        try:
            parts = message_data.message[1:].split()
            if not parts:
                return DEFAULT_RESPONSE
                
            command = parts[0].lower()
            args = parts[1:]
            
            if command in self.commands:
                return self.commands[command].execute(message_data, args)
            
            return f"Unknown command: {command}. Type !help for available commands.\n\n{DEFAULT_RESPONSE}"
            
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            return DEFAULT_RESPONSE
            
    def handle_normal_message(self, message_data: MessageData) -> str:
        """Handle non-command messages"""
        try:
            logger.info(f"Received normal message: {message_data.message}")
            # Always return the default response
            return DEFAULT_RESPONSE
            
        except Exception as e:
            logger.error(f"Error handling normal message: {e}")
            return DEFAULT_RESPONSE

    def send_response(self, response: str, thread_id: str, thread_type: str) -> None:
        """Send response message back to Zalo"""
        try:
            if response:
                tt = ThreadType.USER if thread_type.upper() == "USER" else ThreadType.GROUP
                message = Message(text=response)
                self.bot.send(message, thread_id, tt)
                logger.info(f"Sent response: {response}")
                
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            # Try to send default response if regular response fails
            try:
                tt = ThreadType.USER if thread_type.upper() == "USER" else ThreadType.GROUP
                message = Message(text=DEFAULT_RESPONSE)
                self.bot.send(message, thread_id, tt)
                logger.info("Sent default response as fallback")
            except Exception as e2:
                logger.error(f"Error sending default response: {e2}") 