from fastapi import APIRouter

from .clients import router as clients_router
from .nodes import router as nodes_router
from .routing import router as routing_router
from .stats import router as stats_router
from .subscriptions import router as subs_router

api_router = APIRouter()
api_router.include_router(nodes_router)
api_router.include_router(clients_router)
api_router.include_router(subs_router)
api_router.include_router(stats_router)
api_router.include_router(routing_router)
