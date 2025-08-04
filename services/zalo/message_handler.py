import json
import logging
from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel
from zlapi import ZaloAPI
from zlapi.models import Message, ThreadType

logger = logging.getLogger(__name__)

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

    async def execute(self, message_data: MessageData, args: List[str]) -> str:
        """Execute the command"""
        raise NotImplementedError

class HelpCommand(BaseCommand):
    """Handler for !help command"""
    async def execute(self, message_data: MessageData, args: List[str]) -> str:
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
    async def execute(self, message_data: MessageData, args: List[str]) -> str:
        return " ".join(args) if args else "Echo what?"

class InfoCommand(BaseCommand):
    """Handler for !info command"""
    async def execute(self, message_data: MessageData, args: List[str]) -> str:
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
        
    async def process_message(self, message_data: MessageData) -> Optional[str]:
        """Process incoming message and return response if needed"""
        try:
            logger.info(f"Processing message: {message_data.message} from {message_data.author_id}")
            
            if message_data.message.startswith("!"):
                return await self.handle_command(message_data)
                
            return await self.handle_normal_message(message_data)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None
            
    async def handle_command(self, message_data: MessageData) -> Optional[str]:
        """Handle command messages (starting with !)"""
        try:
            parts = message_data.message[1:].split()
            if not parts:
                return None
                
            command = parts[0].lower()
            args = parts[1:]
            
            if command in self.commands:
                return await self.commands[command].execute(message_data, args)
            
            return f"Unknown command: {command}. Type !help for available commands."
            
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            return None
            
    async def handle_normal_message(self, message_data: MessageData) -> Optional[str]:
        """Handle non-command messages"""
        try:
            # Add your custom message processing logic here
            # For example:
            # - Natural language processing
            # - Keyword detection
            # - AI response generation
            # - Message forwarding
            # - Database storage
            
            logger.info(f"Received normal message: {message_data.message}")
            return None
            
        except Exception as e:
            logger.error(f"Error handling normal message: {e}")
            return None

    async def send_response(self, response: str, thread_id: str, thread_type: str) -> None:
        """Send response message back to Zalo"""
        try:
            if response:
                tt = ThreadType.USER if thread_type.upper() == "USER" else ThreadType.GROUP
                message = Message(text=response)
                await self.bot.sendMessage(message, thread_id, tt)
                
        except Exception as e:
            logger.error(f"Error sending response: {e}") 