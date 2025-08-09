import hashlib
import hmac
import json
import os
from typing import Optional

import fastapi.responses
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --- Config and Routers ---
from services.app_settings import config_manager
from routers import config_router, zalo_oa_router

app = FastAPI()

# ----------------------------------------------------
# Application lifecycle hooks for config management
# ----------------------------------------------------
@app.on_event("startup")
async def startup_event():
    await config_manager.load()
    # Set GROQ API Key for langchain if not set as env var
    # This allows libraries that use os.environ to work correctly
    if 'GROQ_API_KEY' not in os.environ:
        os.environ['GROQ_API_KEY'] = config_manager.settings.agent_config.model.api_key


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)


class ZaloMessage(BaseModel):
    app_id: str
    sender_id: str
    user_id: str
    event_name: str
    message: Optional[dict]
    timestamp: str


# Include routers
app.include_router(config_router.router)
app.include_router(zalo_oa_router.router)


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
    # Check if Zalo OA integration is enabled
    if not config_manager.settings.zalo_config.oa.enabled:
        raise HTTPException(status_code=503, detail="Zalo OA integration is disabled")
        
    # Get raw request body
    body = await request.body()

    # Verify signature using the key from our config
    if not verify_signature(body, mac):
        # In a real app, you might want to raise an HTTPException here
        print("Webhook signature verification failed!")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        # Parse the body as JSON
        data = json.loads(body)
        
        # Forward the request to the Zalo OA router for processing
        # We'll use the same structure as expected by the OA router
        return await zalo_oa_router.zalo_oa_webhook(request)
        
    except json.JSONDecodeError:
        print("Invalid JSON in webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        print(f"Error processing webhook: {e}")
        # Return success to acknowledge receipt as per Zalo's requirement
        return {"status": "success"}


def verify_signature(body: bytes, mac: str) -> bool:
    """
    Verify the webhook signature using HMAC
    """
    if not mac:
        return False
    
    # Access the secret key from the new nested structure
    secret = config_manager.settings.zalo_config.oa.secret_key

    computed_hash = hmac.new(
        secret.encode(),
        body,  # hmac works with bytes
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_hash, mac)


# Add specific route for Zalo verification file
@app.get("/zalo_verifierMUxX39taK3XPvj4vaz5RCrFZr2-_bGDmDZGn.html")
async def zalo_verification_file():
    return fastapi.responses.FileResponse("static/zalo_verifierMUxX39taK3XPvj4vaz5RCrFZr2-_bGDmDZGn.html")


# Mount static files AFTER defining all routes
app.mount("/static", StaticFiles(directory="static"), name="static")
