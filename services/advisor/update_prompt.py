"""Utility script to update the system prompt in the global configuration.

This script provides functions to update and manage the system prompt.
"""

import asyncio
import logging
from services.config import config_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PROMPT = """Bạn là trợ lý AI giao tiếp bằng Tiếng Việt, tập trung vào giải quyết vấn đề.
Quy tắc phản hồi:
- LUÔN giới hạn câu trả lời trong 20 từ
- Đi thẳng vào vấn đề chính
- Không dùng từ ngữ thừa hoặc mở đầu dài dòng
- Ưu tiên hướng dẫn và giải pháp cụ thể
- Sử dụng ngôn ngữ đơn giản, dễ hiểu

Ví dụ cách trả lời tốt:
- "Bấm nút Cài đặt > Bảo mật > Đổi mật khẩu để thay đổi mật khẩu ạ."
- "Anh/chị vui lòng gửi email đến support@example.com để được hỗ trợ ạ."
- "Em không rõ về vấn đề này. Anh/chị liên hệ số 0358380646 ạ."
"""

async def update_system_prompt(new_prompt=None):
    """Update the system prompt in the global configuration.
    
    Args:
        new_prompt (str, optional): The new system prompt. If None, uses the default.
        
    Returns:
        str: The updated system prompt
    """
    # Start the config system
    await config_manager.start()
    
    # Use default if no prompt provided
    prompt_to_use = new_prompt or DEFAULT_PROMPT
    
    # Update the global config
    await config_manager.patch_global({
        "default_system_prompt": prompt_to_use
    })
    
    logger.info("Updated system prompt in global configuration")
    
    # Stop the config system
    await config_manager.stop()
    
    return prompt_to_use

async def reset_to_default():
    """Reset the system prompt to the default value."""
    return await update_system_prompt(DEFAULT_PROMPT)

async def get_current_prompt():
    """Get the current system prompt from the global configuration."""
    # Start the config system
    await config_manager.start()
    
    # Get the current prompt
    current_prompt = config_manager.get_global().default_system_prompt
    
    # Stop the config system
    await config_manager.stop()
    
    return current_prompt

if __name__ == "__main__":
    # Example usage: Reset to default prompt
    asyncio.run(reset_to_default()) 