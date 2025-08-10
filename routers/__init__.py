# This file makes the routers directory a Python package

from .agent_router import router as agent_router
from .zalo_oa_router import router as zalo_oa_router
from .zalo_personal_router import router as zalo_personal_router
from .config_router import router as config_router
from .testing_router import router as testing_router

__all__ = [
    "agent_router",
    "zalo_oa_router", 
    "zalo_personal_router",
    "config_router",
    "testing_router"
] 