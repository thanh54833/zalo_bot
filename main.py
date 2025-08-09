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
from routers import config_router, zalo_oa_router, zalo_personal_router, agent_router

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


# Include routers
app.include_router(config_router.router)
app.include_router(zalo_oa_router.router)
app.include_router(zalo_personal_router.router)
app.include_router(agent_router.router)


@app.get("/")
async def root():
    return {"greeting": "Hello, World!", "message": "Welcome to FastAPI!"}


# Add specific route for Zalo verification file
@app.get("/zalo_verifierMUxX39taK3XPvj4vaz5RCrFZr2-_bGDmDZGn.html")
async def zalo_verification_file():
    return fastapi.responses.FileResponse("static/zalo_verifierMUxX39taK3XPvj4vaz5RCrFZr2-_bGDmDZGn.html")


# Mount static files AFTER defining all routes
app.mount("/static", StaticFiles(directory="static"), name="static")
