from typing import Dict, List, Optional, Union
from langchain_core.messages import AnyMessage

class Prompt:
    """Class to manage prompts for the advisor agent"""
    
    @staticmethod
    def get_default_prompt() -> str:
        """Returns the default system prompt for the agent"""
        return """You are a helpful AI assistant. You provide clear, accurate, and concise responses.
        
When answering questions:
- Be truthful and admit when you don't know something
- Provide specific, actionable advice when appropriate
- Maintain a friendly and professional tone
- Format your responses for readability
- Avoid making up information or providing misleading answers
"""
    
    @staticmethod
    def get_expert_prompt() -> str:
        """Returns an expert-level system prompt for the agent"""
        return """You are an expert AI assistant with deep knowledge across multiple domains. You provide detailed, nuanced, and accurate responses.
        
When answering questions:
- Draw on your extensive knowledge to provide comprehensive answers
- Consider multiple perspectives and approaches
- Cite relevant concepts and principles when applicable
- Explain complex topics in an accessible way
- Be transparent about limitations in your knowledge
- Maintain a professional and authoritative tone
"""
    
    @staticmethod
    def get_custom_prompt(user_id: str, context: Optional[Dict] = None) -> str:
        """Returns a custom prompt based on user ID and optional context"""
        # This could be expanded to fetch user preferences from a database
        base_prompt = Prompt.get_default_prompt()
        
        # Add user-specific customizations
        if context and "name" in context:
            user_greeting = f"\nWhen responding to {context['name']}, "
            user_greeting += "use their name occasionally and remember their preferences."
            base_prompt += user_greeting
            
        return base_prompt
    
    @staticmethod
    def format_prompt(prompt_text: str, messages: List[AnyMessage]) -> List[AnyMessage]:
        """Formats a prompt text with system message and user messages"""
        system_message = {"role": "system", "content": prompt_text}
        return [system_message] + messages 