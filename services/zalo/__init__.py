from .bot import ZaloBot
from .message_handler import ZaloMessageHandler, MessageData, BaseCommand

# Global bot instance
_bot_instance = None

def get_bot_instance() -> ZaloBot:
    """
    Get the global ZaloBot instance
    
    Returns:
        The ZaloBot instance or None if not initialized
    """
    return _bot_instance

def set_bot_instance(bot: ZaloBot):
    """
    Set the global ZaloBot instance
    
    Args:
        bot: The ZaloBot instance to set
    """
    global _bot_instance
    _bot_instance = bot

__all__ = ['ZaloBot', 'ZaloMessageHandler', 'MessageData', 'BaseCommand', 'get_bot_instance', 'set_bot_instance'] 