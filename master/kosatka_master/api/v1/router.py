from fastapi import APIRouter

from .auth import router as auth_router
from .clients import router as clients_router
from .config import router as config_router
from .host import router as host_router
from .nodes import router as nodes_router
from .routing import router as routing_router
from .stats import router as stats_router
from .subscriptions import router as subs_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(config_router)
api_router.include_router(nodes_router)
api_router.include_router(host_router)
api_router.include_router(clients_router)
api_router.include_router(subs_router)
api_router.include_router(stats_router)
api_router.include_router(routing_router)
