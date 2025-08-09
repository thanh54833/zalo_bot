import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request, Header, Depends
import httpx

from services.app_settings import config_manager
from services.advisor import agent_advisor

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/zalo-oa",
    tags=["zalo-oa"],
    responses={404: {"description": "Not found"}},
)

# Zalo OA event types
EVENT_USER_SEND_TEXT = "user_send_text"
EVENT_USER_SEND_IMAGE = "user_send_image"
EVENT_USER_SEND_STICKER = "user_send_sticker"
EVENT_USER_FOLLOW_OA = "user_follow_oa"
EVENT_USER_UNFOLLOW_OA = "user_unfollow_oa"

class ZaloOAHandler:
    """Handler for Zalo Official Account webhook events"""
    
    def __init__(self):
        self.base_url = "https://openapi.zalo.me/v2.0/oa"
        self.last_activity = datetime.now()
    
    async def is_enabled(self) -> bool:
        """Check if Zalo OA integration is enabled"""
        return config_manager.settings.zalo_config.oa.enabled
    
    async def get_access_token(self) -> str:
        """Get Zalo OA access token (implement your token management here)"""
        # This is a placeholder. In a real implementation, you would:
        # 1. Check if you have a valid cached token
        # 2. If not, use refresh token to get a new one
        # 3. Store the new token and return it
        
        # For now, we'll just return a dummy value
        return "YOUR_ZALO_OA_ACCESS_TOKEN"
    
    async def send_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """Send a text message to a user via Zalo OA API"""
        if not await self.is_enabled():
            logger.warning("Zalo OA integration is disabled. Not sending message.")
            return {"success": False, "message": "Zalo OA integration is disabled"}
            
        try:
            access_token = await self.get_access_token()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/message",
                    json={
                        "recipient": {
                            "user_id": user_id
                        },
                        "message": {
                            "text": message
                        }
                    },
                    headers={
                        "access_token": access_token,
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Error sending message: {response.text}")
                    return {"success": False, "error": response.text}
                    
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}
    
    async def handle_text_message(self, sender_id: str, message: str) -> Dict[str, Any]:
        """Handle a text message from a user"""
        if not await self.is_enabled():
            logger.warning("Zalo OA integration is disabled. Not processing message.")
            return {"success": False, "message": "Zalo OA integration is disabled"}
            
        try:
            # Process message with AI agent if it's enabled
            if agent_advisor.is_enabled:
                # Format message for agent
                agent_messages = [
                    {"role": "user", "content": message}
                ]
                
                # Get response from agent
                agent_response = agent_advisor.invoke(agent_messages)
                
                # Extract response text
                response_text = agent_response.get("output", "Sorry, I couldn't process your request.")
                
                # Send response back to user
                return await self.send_message(sender_id, response_text)
            else:
                logger.warning("AI agent is disabled. Using default response.")
                return await self.send_message(
                    sender_id, 
                    "I'm sorry, but our AI assistant is currently unavailable. Please try again later."
                )
                
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            return {"success": False, "error": str(e)}
    
    async def handle_follow_event(self, sender_id: str) -> Dict[str, Any]:
        """Handle a user following the OA"""
        if not await self.is_enabled():
            logger.warning("Zalo OA integration is disabled. Not processing follow event.")
            return {"success": False, "message": "Zalo OA integration is disabled"}
            
        try:
            welcome_message = "Cảm ơn bạn đã theo dõi. Tôi là trợ lý ảo, hãy đặt câu hỏi để được hỗ trợ!"
            return await self.send_message(sender_id, welcome_message)
        except Exception as e:
            logger.error(f"Error handling follow event: {e}")
            return {"success": False, "error": str(e)}

# Create singleton handler
zalo_oa_handler = ZaloOAHandler()

# Dependency to check if OA integration is enabled
async def verify_oa_enabled():
    if not await zalo_oa_handler.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Zalo OA integration is currently disabled"
        )
    return True

@router.post("/webhook")
async def zalo_oa_webhook(request: Request, enabled: bool = Depends(verify_oa_enabled)):
    """
    Handle incoming webhook events from Zalo OA
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Received Zalo OA webhook: {body}")
        
        # Extract event data
        event_name = body.get("event_name")
        sender_id = body.get("sender", {}).get("id")
        
        if not event_name or not sender_id:
            logger.warning("Missing event_name or sender_id in webhook payload")
            return {"status": "error", "message": "Invalid payload"}
        
        # Handle different event types
        if event_name == EVENT_USER_SEND_TEXT:
            message = body.get("message", {}).get("text", "")
            await zalo_oa_handler.handle_text_message(sender_id, message)
            
        elif event_name == EVENT_USER_FOLLOW_OA:
            await zalo_oa_handler.handle_follow_event(sender_id)
            
        # Always return success to acknowledge receipt
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing Zalo OA webhook: {e}")
        # Still return success to acknowledge receipt
        return {"status": "success"}

@router.get("/status")
async def get_status(enabled: bool = Depends(verify_oa_enabled)):
    """Get the current status of the Zalo OA integration"""
    return {
        "status": "active",
        "last_activity": zalo_oa_handler.last_activity.isoformat(),
        "agent_enabled": agent_advisor.is_enabled
    } 