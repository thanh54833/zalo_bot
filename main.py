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
from services.advisor.agent import AgentAdvisor
from routers import config_router, zalo_oa_router, zalo_personal_router, agent_router, testing_router
import services.advisor

app = FastAPI()


# ----------------------------------------------------
# Application lifecycle hooks for config management
# ----------------------------------------------------
@app.on_event("startup")
async def startup_event():
    try:
        print("🔄 Starting application initialization...")
        
        # Load configuration
        await config_manager.load()
        print("✅ Configuration loaded successfully")
        
        # Create a default instance of AgentAdvisor and assign it to the module-level variable
        print("🔄 Creating AgentAdvisor instance...")
        services.advisor.agent_advisor = AgentAdvisor()
        
        # Also update the reference in agent_router
        agent_router.agent_advisor = services.advisor.agent_advisor
        print("✅ AgentAdvisor created and assigned successfully")
        
        # Test if the agent is working
        if services.advisor.agent_advisor.is_initialized:
            print("✅ Agent initialized successfully during startup")
        else:
            print("⚠️ Agent not initialized during startup - this may be normal if disabled")
            
        print("🚀 Application startup completed successfully")
        
    except Exception as e:
        print(f"❌ Application startup failed: {e}")
        import traceback
        traceback.print_exc()
        # Don't raise the exception - let the app continue to start
        # but log the error for debugging


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
app.include_router(config_router)
app.include_router(zalo_oa_router)
app.include_router(zalo_personal_router)
app.include_router(agent_router)
app.include_router(testing_router)


@app.get("/")
async def root():
    return {"greeting": "Hello, World!", "message": "Welcome to FastAPI!"}


# Add specific route for Zalo verification file
@app.get("/zalo_verifierMUxX39taK3XPvj4vaz5RCrFZr2-_bGDmDZGn.html")
async def zalo_verification_file():
    return fastapi.responses.FileResponse("static/zalo_verifierMUxX39taK3XPvj4vaz5RCrFZr2-_bGDmDZGn.html")


# Mount static files AFTER defining all routes
app.mount("/static", StaticFiles(directory="static"), name="static")
