from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel
import hmac
import hashlib
import json
from typing import Optional
import fastapi.responses

app = FastAPI()

# Configuration - These should be loaded from environment variables in production
OA_SECRET_KEY = "your_oa_secret_key"  # Get this from Zalo Developer Portal
ZALO_VERIFICATION_CODE = "MUxX39taK3XPvj4vaz5RCrFZr2-_bGDmDZGn"

class ZaloMessage(BaseModel):
    app_id: str
    sender_id: str
    user_id: str
    event_name: str
    message: Optional[dict]
    timestamp: str

@app.get("/")
async def root():
    return {"greeting": "Hello, World!", "message": "Welcome to FastAPI!"}

@app.get("/webhook")
async def verify_webhook(mac: str = Header(None)):
    """
    Handle Zalo webhook URL verification
    This endpoint is used by Zalo to verify the webhook URL
    """
    return {"message": "Webhook URL verified"}

@app.post("/webhook")
async def zalo_webhook(request: Request, mac: str = Header(None)):
    """
    Handle incoming webhook events from Zalo
    """
    # Get raw request body
    body = await request.body()
    body_str = body.decode()
    
    # Verify webhook signature
    if not verify_signature(body_str, mac):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Parse request body
    try:
        data = json.loads(body_str)
        message = ZaloMessage(**data)
        
        # Handle different event types
        if message.event_name == "user_send_text":
            return handle_text_message(message)
        elif message.event_name == "user_send_image":
            return handle_image_message(message)
        elif message.event_name == "user_send_sticker":
            return handle_sticker_message(message)
        elif message.event_name == "follow":
            return handle_follow_event(message)
        elif message.event_name == "unfollow":
            return handle_unfollow_event(message)
            
        return {"status": "success"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/zalo-platform-site-verification.html", response_class=fastapi.responses.PlainTextResponse)
async def zalo_domain_verification():
    """
    Handle Zalo domain ownership verification via HTML file
    This endpoint returns the verification code provided by Zalo
    """
    return f"zalo-platform-site-verification={ZALO_VERIFICATION_CODE}"

@app.get("/.well-known/zalo-platform-site-verification.txt", response_class=fastapi.responses.PlainTextResponse)
async def zalo_txt_verification():
    """
    Handle Zalo domain ownership verification via TXT file
    This is an alternative verification method
    """
    return f"zalo-platform-site-verification={ZALO_VERIFICATION_CODE}"

def verify_signature(body: str, mac: str) -> bool:
    """
    Verify the webhook signature using HMAC
    """
    if not mac:
        return False
        
    computed_hash = hmac.new(
        OA_SECRET_KEY.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_hash, mac)

def handle_text_message(message: ZaloMessage):
    """Handle text messages from users"""
    # Implement your text message handling logic here
    return {"status": "success"}

def handle_image_message(message: ZaloMessage):
    """Handle image messages from users"""
    # Implement your image message handling logic here
    return {"status": "success"}

def handle_sticker_message(message: ZaloMessage):
    """Handle sticker messages from users"""
    # Implement your sticker message handling logic here
    return {"status": "success"}

def handle_follow_event(message: ZaloMessage):
    """Handle when a user follows the Official Account"""
    # Implement your follow event handling logic here
    return {"status": "success"}

def handle_unfollow_event(message: ZaloMessage):
    """Handle when a user unfollows the Official Account"""
    # Implement your unfollow event handling logic here
    return {"status": "success"}