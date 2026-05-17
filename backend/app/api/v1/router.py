from fastapi import APIRouter

from app.api.v1 import webhooks
from app.api.v1.endpoints import dashboard, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(webhooks.router)
api_router.include_router(dashboard.router)
