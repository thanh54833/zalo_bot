import hashlib
import hmac
import json
import os
from typing import Optional

import fastapi.responses
from fastapi import FastAPI, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --- Set Groq API Key ---
# WARNING: Storing API keys directly in code is insecure.
# It's recommended to use environment variables or a secret management system for production.
os.environ['GROQ_API_KEY'] = "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"

# Import our zalo router
from routers import zalo_router

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Configuration - These should be loaded from environment variables in production
OA_SECRET_KEY = "NrGu0gUeiEnRrajtwPmF"  # Get this from Zalo Developer Portal

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)


class ZaloMessage(BaseModel):
    app_id: str
    sender_id: str
    user_id: str
    event_name: str
    message: Optional[dict]
    timestamp: str


# Include our zalo router
app.include_router(zalo_router.router)


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

    print("body -> ", body)
    print("Received webhook event -> ", verify_signature(body, mac))

    # During initial setup, Zalo might send verification requests without proper signatures
    # Skip signature verification for now

    try:
        # Try to parse the request body
        data = json.loads(body_str)

        # Always return success for webhook verification
        return {"status": "success"}

    except Exception as e:
        # If there's an error, still return success for webhook verification
        return {"status": "success"}


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


# Add specific route for Zalo verification file
@app.get("/zalo_verifierMUxX39taK3XPvj4vaz5RCrFZr2-_bGDmDZGn.html")
async def zalo_verification_file():
    return fastapi.responses.FileResponse("static/zalo_verifierMUxX39taK3XPvj4vaz5RCrFZr2-_bGDmDZGn.html")


# Mount static files AFTER defining all routes
app.mount("/static", StaticFiles(directory="static"), name="static")
