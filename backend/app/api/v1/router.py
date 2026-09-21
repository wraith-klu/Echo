from fastapi import APIRouter
from app.api.v1.endpoints import router as endpoints_router
from app.api.v1.websocket import router as ws_router

api_router = APIRouter()

# Include REST endpoints
api_router.include_router(endpoints_router, tags=["REST Endpoints"])

# Include WebSocket streams
api_router.include_router(ws_router, prefix="/ws", tags=["WebSocket Stream"])
